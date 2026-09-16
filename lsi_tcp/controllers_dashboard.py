import csv
import io
import threading
from datetime import datetime
from typing import Dict, Optional

import dash
import dash_bootstrap_components as dbc
import dash_daq as daq
from dash import dcc, html
from dash.dependencies import ALL, MATCH, Input, Output, State
from dash.exceptions import PreventUpdate

import plotly.graph_objs as go
import plotly.io as pio
from plotly.subplots import make_subplots

from .channel_runtime import ChannelRuntime
from .dashboard_state import DashboardState

# Nomi dei segnali di processo associati a ciascun canale. Il progetto
# lavora sempre con esattamente due canali (T1/U1 e T2/U2): non serve
# generalizzare a N canali, quindi la mappa è statica.
_CHANNEL_INFO = {
    "channel1": {"T": "T1", "U": "U1", "title": "Canale 1 (T1 / U1)"},
    "channel2": {"T": "T2", "U": "U2", "title": "Canale 2 (T2 / U2)"},
}

# Parametri "strutturali" comuni a tutti i controllori/FakeTCLabSystem:
# vengono separati dai parametri "tarabili" nel pannello Offcanvas.
_STRUCTURAL_PARAMS = ("sampling_period", "u_min", "u_max")


class ControllerDashboard:
    """
    Dashboard Dash/Bootstrap per il tuning interattivo di due canali di
    controllo (channel1 -> T1/U1, channel2 -> T2/U2) + monitoraggio delle
    variabili di processo.

    Per ogni canale la dashboard NON parla direttamente con le classi
    controllore: legge/scrive lo stato condiviso in un `DashboardState` e
    mostra i parametri del controllore attivo esposto da un
    `ChannelRuntime` (che è anche l'oggetto che, nel loop di controllo,
    decide quale dei due controllori del canale calcola u).

    Uso tipico (vedi anche `utils.run_closed_loop`):

        state = DashboardState(["channel1", "channel2"])
        runtimes = {
            "channel1": ChannelRuntime("channel1", manual1, auto1, state),
            "channel2": ChannelRuntime("channel2", manual2, auto2, state),
        }
        dashboard = ControllerDashboard(runtimes, state, system=process)

        # nel loop di controllo:
        u1, ref1 = runtimes["channel1"].step(measure=t1)
        u2, ref2 = runtimes["channel2"].step(measure=t2)
        dashboard.get_values(T1=t1, T2=t2, U1=u1, U2=u2, SP1=ref1, SP2=ref2)
    """

    def __init__(
        self,
        runtimes: Dict[str, ChannelRuntime],
        state: DashboardState,
        system=None,
        is_simulator: bool = True,
        setpoint_from_profile: bool = False,
        host: str = "127.0.0.1",
        port: int = 8051,
        debug: bool = True,
        title: str = "Controller Tuning Dashboard",
        serve_dev_bundles: bool = False,
        start_in_background: bool = True,
        plot_period: float = 1.0,
        time_window: int = 300,
    ):
        """
        Parametri:
            runtimes             : dict {"channel1": ChannelRuntime, "channel2": ChannelRuntime}
            state                : DashboardState condiviso con il loop di controllo
            system               : processo (FakeTCLabSystem o TCLabSystem), opzionale.
                                    Se è un FakeTCLabSystem viene mostrato anche il pannello
                                    "Modifica parametri simulatore" (K/tau/L).
            is_simulator         : True se `system` è un simulatore (per il badge di stato)
            setpoint_from_profile: True durante la fase di validazione finale, quando il
                                    setpoint in automatico arriva da un SetpointProfile e
                                    NON deve essere modificato a mano dallo studente
                                    (il campo numerico viene disabilitato)
            host, port, debug, title, serve_dev_bundles, start_in_background,
            plot_period, time_window: come nella versione precedente.
        """
        self.runtimes = runtimes
        self.state = state
        self.system = system
        self.is_simulator = is_simulator
        self.setpoint_from_profile = setpoint_from_profile

        self.host = host
        self.port = port
        self.debug = debug
        self.title = title
        self.serve_dev_bundles = serve_dev_bundles

        self.plot_period = float(plot_period)
        self.time_window = int(time_window)

        # Buffer dati grafico
        self.lock = threading.Lock()
        self.time_data = []
        self.t1_data = []
        self.t2_data = []
        self.sp1_data = []
        self.sp2_data = []
        self.u1_data = []
        self.u2_data = []
        self.max_points = 10000  # limite per evitare crescita infinita

        # Crea app Dash con tema Bootstrap. suppress_callback_exceptions è
        # necessario perché il contenuto degli Offcanvas (parametri) viene
        # generato dinamicamente DOPO il primo render (non è nel layout iniziale).
        self.app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.BOOTSTRAP],
            suppress_callback_exceptions=True,
        )

        self.app.layout = self._create_layout()
        self._register_callbacks()

        self.app_thread = None

        if start_in_background:
            self.start_background()

    # ================================================================
    # Layout
    # ================================================================

    def _create_layout(self):
        header = dbc.Row(
            [
                dbc.Col(html.H1(self.title), width="auto"),
                dbc.Col(
                    dbc.Badge(
                        "Simulatore" if self.is_simulator else "Hardware reale",
                        color="info" if self.is_simulator else "warning",
                        className="ms-2",
                        style={"fontSize": "1rem"},
                    ),
                    width="auto",
                    className="d-flex align-items-center",
                ),
            ],
            align="center",
            className="mb-3",
        )

        channel_cards = dbc.Row(
            [dbc.Col(self._build_channel_card(ch), md=6) for ch in self.runtimes],
            className="mb-3",
        )

        system_row = []
        if self.system is not None and hasattr(self.system, "getListOfParameters"):
            system_row.append(dbc.Row(dbc.Col(self._build_system_card()), className="mb-3"))

        controls = dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Finestra temporale (n° campioni)"),
                        dcc.Input(
                            id="time-window",
                            type="number",
                            value=self.time_window,
                            min=1,
                            step=1,
                            style={"width": "140px"},
                        ),
                    ],
                    width="auto",
                ),
                dbc.Col(
                    dbc.Button("⏸ Pausa grafico", id="pause-btn", color="secondary", outline=True),
                    width="auto",
                ),
                dbc.Col(
                    dbc.Button("Esporta CSV", id="export-csv-btn", color="secondary", outline=True),
                    width="auto",
                ),
                dbc.Col(
                    dbc.Button("Esporta PNG", id="export-png-btn", color="secondary", outline=True),
                    width="auto",
                ),
            ],
            align="center",
            className="mb-2 g-2",
        )

        plot_section = html.Div(
            [
                html.H2("Andamento variabili di processo", className="mt-4 mb-2"),
                controls,
                dcc.Graph(id="real-time-graph"),
                dcc.Interval(
                    id="interval-component",
                    interval=int(self.plot_period * 1000),
                    n_intervals=0,
                ),
                dcc.Store(id="pause-flag", data=False),
                dcc.Download(id="download-csv"),
                dcc.Download(id="download-png"),
            ],
            className="mt-3",
        )

        return dbc.Container(
            [header, channel_cards, *system_row, plot_section],
            fluid=True,
            className="py-3",
        )

    def _build_channel_card(self, ch: str):
        info = _CHANNEL_INFO[ch]
        runtime = self.runtimes[ch]
        mode = runtime.mode

        return dbc.Card(
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(html.H4(info["title"]), width="auto"),
                            dbc.Col(
                                dbc.Badge(
                                    "Automatico" if mode == "auto" else "Manuale",
                                    id=f"mode-badge-{ch}",
                                    color="success" if mode == "auto" else "secondary",
                                ),
                                width="auto",
                                className="d-flex align-items-center",
                            ),
                        ],
                        align="center",
                        className="mb-2",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(daq.BooleanSwitch(id=f"mode-switch-{ch}", on=(mode == "auto")), width="auto"),
                            dbc.Col(html.Span("Manuale ⟷ Automatico"), width="auto"),
                        ],
                        align="center",
                        className="mb-3 g-2",
                    ),
                    dbc.Label(id=f"adaptive-label-{ch}", children=self._adaptive_label(ch)),
                    dcc.Input(
                        id=f"adaptive-input-{ch}",
                        type="number",
                        value=self._adaptive_value(ch),
                        debounce=True,
                        disabled=self._adaptive_disabled(ch),
                        style={"width": "100%"},
                        className="mb-3",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(html.Div([html.Small("Errore corrente"), html.H5(id=f"kpi-error-{ch}", children="-")])),
                            dbc.Col(html.Div([html.Small("Parametri attivi"), html.Div(id=f"kpi-params-{ch}", children="-")])),
                        ],
                        className="mb-3",
                    ),
                    dbc.Button("Modifica parametri", id=f"param-open-{ch}", size="sm", color="primary", outline=True),
                    dbc.Offcanvas(
                        id=f"param-offcanvas-{ch}",
                        title=f"Parametri – {info['title']}",
                        is_open=False,
                        children=html.Div(id=f"param-body-{ch}"),
                    ),
                    # Target "a perdere" per il callback che intercetta la
                    # digitazione nel campo adattivo e la scrive in
                    # DashboardState: non deve pilotare nulla in pagina.
                    html.Div(id=f"_dummy-output-{ch}", style={"display": "none"}),
                ]
            ),
            className="h-100",
        )

    def _build_system_card(self):
        return dbc.Card(
            dbc.CardBody(
                [
                    html.H4("Simulatore (FakeTCLabSystem)"),
                    html.P("Parametri del modello FOPDT usati in fase di test in simulato."),
                    dbc.Button("Modifica parametri simulatore", id="param-open-system", size="sm", color="primary", outline=True),
                    dbc.Offcanvas(
                        id="param-offcanvas-system",
                        title="Parametri del simulatore",
                        is_open=False,
                        children=html.Div(id="param-body-system"),
                    ),
                ]
            )
        )

    # ---------- helper per il campo numerico "adattivo" ----------

    # Nota: questi helper leggono SEMPRE la modalità da self.state (l'intento
    # dell'utente, aggiornato immediatamente dallo switch), non da
    # runtimes[ch].mode (la modalità del ChannelRuntime, che si allinea con
    # un ritardo massimo di un sampling_period, al prossimo giro del loop
    # di controllo). Usare runtimes[ch].mode qui creerebbe una finestra in
    # cui il campo adattivo scrive nello stato sbagliato (manual_u invece
    # di setpoint, o viceversa) subito dopo un cambio di modalità.
    def _adaptive_label(self, ch: str) -> str:
        mode = self.state.get_mode(ch)
        return "Setpoint [°C]" if mode == "auto" else "Potenza U [%]"

    def _adaptive_value(self, ch: str) -> float:
        mode, manual_u, setpoint = self.state.snapshot(ch)
        return setpoint if mode == "auto" else manual_u

    def _adaptive_disabled(self, ch: str) -> bool:
        mode = self.state.get_mode(ch)
        return mode == "auto" and self.setpoint_from_profile

    # ================================================================
    # Pannello parametri (Offcanvas) - riutilizzabile per controllori e
    # per FakeTCLabSystem
    # ================================================================

    def _resolve_target(self, scope: str):
        """Ritorna l'oggetto con getListOfParameters/getParameters/setParameters per lo scope."""
        if scope == "system":
            return self.system
        return self.runtimes[scope].active_controller

    def _build_param_body(self, scope: str):
        target = self._resolve_target(scope)
        if target is None:
            return html.Div("Nessun parametro disponibile.")

        names = target.getListOfParameters()
        params = target.getParameters()

        tunable = [n for n in names if n not in _STRUCTURAL_PARAMS]
        structural = [n for n in names if n in _STRUCTURAL_PARAMS]

        def _param_row(p_name, with_slider):
            value = params[p_name]
            is_numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
            children = [
                html.Label(p_name, className="fw-bold"),
                dcc.Input(
                    id={"type": "param-input", "scope": scope, "param": p_name},
                    type="number" if is_numeric else "text",
                    value=value,
                    debounce=True,
                    style={"width": "100%"},
                ),
            ]
            if with_slider and is_numeric:
                # Lo slider è solo un'aggiunta di comodo: muove SOLO il campo
                # numerico (slider -> input), che resta l'unica sorgente
                # inviata a setParameters(). Un legame bidirezionale vero e
                # proprio creerebbe un ciclo di callback Dash.
                lo = min(0.0, float(value))
                hi = max(float(value) * 3.0, float(value) + 10.0, 10.0)
                children.append(
                    dcc.Slider(
                        id={"type": "param-slider", "scope": scope, "param": p_name},
                        min=lo,
                        max=hi,
                        value=float(value),
                        updatemode="mouseup",
                        tooltip={"placement": "bottom"},
                    )
                )
            return html.Div(children, className="mb-3")

        body = [_param_row(p, with_slider=True) for p in tunable]

        if structural:
            body.append(html.Hr())
            body.append(html.Div("Parametri di sistema", className="fw-bold text-muted mb-2"))
            body.extend(_param_row(p, with_slider=False) for p in structural)

        body.append(
            dbc.Button("Applica", id=f"param-submit-{scope}", color="primary", className="mt-2")
        )
        body.append(html.Div(id=f"param-status-{scope}", className="mt-2"))

        return html.Div(body)

    def _register_param_panel(self, scope: str):
        open_id = f"param-open-{scope}"
        offcanvas_id = f"param-offcanvas-{scope}"
        body_id = f"param-body-{scope}"
        submit_id = f"param-submit-{scope}"
        status_id = f"param-status-{scope}"

        @self.app.callback(
            Output(offcanvas_id, "is_open"),
            Output(body_id, "children"),
            Input(open_id, "n_clicks"),
            prevent_initial_call=True,
        )
        def _open_panel(n_clicks, scope=scope):
            if not n_clicks:
                raise PreventUpdate
            return True, self._build_param_body(scope)

        @self.app.callback(
            Output(status_id, "children"),
            Input(submit_id, "n_clicks"),
            State({"type": "param-input", "scope": scope, "param": ALL}, "value"),
            State({"type": "param-input", "scope": scope, "param": ALL}, "id"),
            prevent_initial_call=True,
        )
        def _submit_panel(n_clicks, values, ids, scope=scope):
            if not n_clicks:
                raise PreventUpdate
            target = self._resolve_target(scope)
            param_update = {
                id_dict["param"]: value
                for value, id_dict in zip(values, ids)
                if value is not None
            }
            try:
                target.setParameters(param_update)
            except Exception as e:
                return f"Errore aggiornando parametri: {e}"
            return "Parametri aggiornati con successo."

    # ================================================================
    # Callback principali
    # ================================================================

    def _register_callbacks(self):
        # Slider -> input numerico: aggiorna SOLO il campo numerico associato
        # (stesso scope/param), che resta l'unica sorgente inviata a
        # setParameters(). Il binding è mono-direzionale per evitare un
        # ciclo di callback Dash.
        @self.app.callback(
            Output({"type": "param-input", "scope": MATCH, "param": MATCH}, "value"),
            Input({"type": "param-slider", "scope": MATCH, "param": MATCH}, "value"),
            prevent_initial_call=True,
        )
        def _slider_to_input(value):
            if value is None:
                raise PreventUpdate
            return value

        # Pannelli parametri: uno per canale + eventualmente uno per il sistema
        for ch in self.runtimes:
            self._register_param_panel(ch)
        if self.system is not None and hasattr(self.system, "getListOfParameters"):
            self._register_param_panel("system")

        # Switch manuale/automatico e campo adattivo: un callback per canale
        # (non serve pattern-matching: il trigger, lo switch, è già
        # per-istanza e i due canali hanno comportamento identico).
        for ch in self.runtimes:
            self._register_mode_switch_callback(ch)
            self._register_ticker_callback(ch)

        self._register_pause_callback()
        self._register_graph_callback()
        self._register_export_callbacks()

    def _register_mode_switch_callback(self, ch: str):
        @self.app.callback(
            Output(f"adaptive-label-{ch}", "children", allow_duplicate=True),
            Output(f"adaptive-input-{ch}", "value", allow_duplicate=True),
            Output(f"adaptive-input-{ch}", "disabled", allow_duplicate=True),
            Output(f"mode-badge-{ch}", "children", allow_duplicate=True),
            Output(f"mode-badge-{ch}", "color", allow_duplicate=True),
            Input(f"mode-switch-{ch}", "on"),
            prevent_initial_call=True,
        )
        def _on_switch(is_auto, ch=ch):
            new_mode = "auto" if is_auto else "manual"
            self.state.set_mode(ch, new_mode)
            # Il vero bumpless transfer (chiamata a starting()) avviene nel
            # loop di controllo alla prossima iterazione (ChannelRuntime.step),
            # che è anche l'unico punto che tocca le classi controllore.
            return (
                self._adaptive_label(ch),
                self._adaptive_value(ch),
                self._adaptive_disabled(ch),
                "Automatico" if is_auto else "Manuale",
                "success" if is_auto else "secondary",
            )

        @self.app.callback(
            Output("_dummy-output-" + ch, "children"),
            Input(f"adaptive-input-{ch}", "value"),
            prevent_initial_call=True,
        )
        def _on_adaptive_input(value, ch=ch):
            if value is None:
                raise PreventUpdate
            mode = self.state.get_mode(ch)
            if mode == "auto":
                self.state.set_setpoint(ch, value)
            else:
                self.state.set_manual_u(ch, value)
            return ""

    def _register_ticker_callback(self, ch: str):
        """
        Aggiorna, ad ogni tick dell'Interval, le informazioni di sola
        lettura del canale (badge, KPI). Il campo numerico adattivo viene
        aggiornato qui SOLO quando è disabilitato (setpoint pilotato da
        SetpointProfile in fase di validazione): in quel caso non c'è
        rischio di sovrascrivere ciò che lo studente sta digitando.
        """

        @self.app.callback(
            Output(f"mode-badge-{ch}", "children"),
            Output(f"mode-badge-{ch}", "color"),
            Output(f"kpi-error-{ch}", "children"),
            Output(f"kpi-params-{ch}", "children"),
            Output(f"adaptive-input-{ch}", "value"),
            Input("interval-component", "n_intervals"),
        )
        def _tick(n, ch=ch):
            runtime = self.runtimes[ch]
            mode = runtime.mode
            badge_text = "Automatico" if mode == "auto" else "Manuale"
            badge_color = "success" if mode == "auto" else "secondary"

            error_text = self._compute_kpis(ch)
            params_text = ", ".join(
                f"{k}={v:.3g}" if isinstance(v, (int, float)) else f"{k}={v}"
                for k, v in runtime.active_controller.getParameters().items()
                if k not in _STRUCTURAL_PARAMS
            ) or "-"

            adaptive_value = dash.no_update
            if mode == "auto" and self.setpoint_from_profile:
                adaptive_value = self.state.get_setpoint(ch)

            return badge_text, badge_color, error_text, params_text, adaptive_value

    def _compute_kpis(self, ch: str):
        info = _CHANNEL_INFO[ch]
        with self.lock:
            measures = self.t1_data if info["T"] == "T1" else self.t2_data
            setpoints = self.sp1_data if info["T"] == "T1" else self.sp2_data
            last_measure = measures[-1] if measures else None
            last_setpoint = setpoints[-1] if setpoints else None

        if last_measure is None:
            return "-"

        if last_setpoint is None:
            return "manuale"

        return f"{last_setpoint - last_measure:+.2f} °C"

    def _register_pause_callback(self):
        @self.app.callback(
            Output("pause-flag", "data"),
            Output("pause-btn", "children"),
            Input("pause-btn", "n_clicks"),
            State("pause-flag", "data"),
            prevent_initial_call=True,
        )
        def _toggle_pause(n_clicks, paused):
            new_paused = not bool(paused)
            self.state.set_paused(new_paused)
            label = "▶ Riprendi grafico" if new_paused else "⏸ Pausa grafico"
            return new_paused, label

    def _register_graph_callback(self):
        @self.app.callback(
            Output("real-time-graph", "figure"),
            Input("interval-component", "n_intervals"),
            Input("time-window", "value"),
            State("pause-flag", "data"),
        )
        def _update_graph(n, time_window, paused):
            if paused:
                raise PreventUpdate
            if time_window is None or time_window < 1:
                time_window = self.time_window
            return self._build_figure(int(time_window))

    def _windowed_data(self, time_window: int):
        with self.lock:
            if not self.time_data:
                return {k: [] for k in ("time", "t1", "t2", "sp1", "sp2", "u1", "u2")}
            max_tw = min(len(self.time_data), int(time_window))
            return {
                "time": self.time_data[-max_tw:],
                "t1": self.t1_data[-max_tw:],
                "t2": self.t2_data[-max_tw:],
                "sp1": self.sp1_data[-max_tw:],
                "sp2": self.sp2_data[-max_tw:],
                "u1": self.u1_data[-max_tw:],
                "u2": self.u2_data[-max_tw:],
            }

    def _build_figure(self, time_window: int):
        """
        Griglia 2x2:
          - riga 1: per ciascun canale, T e SP (asse sx, tratteggiato per SP)
                    insieme a U (asse dx) nello STESSO subplot (doppio asse Y);
          - riga 2: errore (SP - T) per canale, utile per leggere a colpo
                    d'occhio sovraelongazione/tempo di assestamento.
        """
        d = self._windowed_data(time_window)

        fig = make_subplots(
            rows=2,
            cols=2,
            shared_xaxes=True,
            vertical_spacing=0.08,
            horizontal_spacing=0.08,
            specs=[
                [{"secondary_y": True}, {"secondary_y": True}],
                [{}, {}],
            ],
            subplot_titles=(
                "Canale 1: T1/SP1 (sx) e U1 (dx)",
                "Canale 2: T2/SP2 (sx) e U2 (dx)",
                "Errore canale 1 (SP1 - T1)",
                "Errore canale 2 (SP2 - T2)",
            ),
        )

        def _add_channel(col, t_data, sp_data, u_data, t_name, u_name):
            fig.add_trace(
                go.Scatter(x=d["time"], y=t_data, mode="lines", name=t_name, line=dict(width=2)),
                row=1, col=col, secondary_y=False,
            )
            if any(v is not None for v in sp_data):
                fig.add_trace(
                    go.Scatter(x=d["time"], y=sp_data, mode="lines", name=f"SP{t_name[-1]}",
                                line=dict(dash="dash")),
                    row=1, col=col, secondary_y=False,
                )
            fig.add_trace(
                go.Scatter(x=d["time"], y=u_data, mode="lines", name=u_name, line=dict(width=1.5)),
                row=1, col=col, secondary_y=True,
            )
            error = [
                (sp - t) if (sp is not None) else None
                for sp, t in zip(sp_data, t_data)
            ]
            fig.add_trace(
                go.Scatter(x=d["time"], y=error, mode="lines", name=f"e{t_name[-1]}", showlegend=False),
                row=2, col=col,
            )

        _add_channel(1, d["t1"], d["sp1"], d["u1"], "T1", "U1")
        _add_channel(2, d["t2"], d["sp2"], d["u2"], "T2", "U2")

        fig.update_yaxes(title_text="Temperatura [°C]", row=1, col=1, secondary_y=False)
        fig.update_yaxes(title_text="U [%]", row=1, col=1, secondary_y=True)
        fig.update_yaxes(title_text="Temperatura [°C]", row=1, col=2, secondary_y=False)
        fig.update_yaxes(title_text="U [%]", row=1, col=2, secondary_y=True)
        fig.update_yaxes(title_text="Errore [°C]", row=2, col=1)
        fig.update_yaxes(title_text="Errore [°C]", row=2, col=2)

        if d["time"]:
            tick_step = max(1, len(d["time"]) // 10)
            tickvals = d["time"][::tick_step]
            for r in (1, 2):
                for c in (1, 2):
                    fig.update_xaxes(tickvals=tickvals, ticktext=tickvals, row=r, col=c)

        fig.update_layout(
            height=750,
            showlegend=True,
            template="plotly_white",
            margin=dict(l=50, r=50, t=60, b=40),
        )

        return fig

    # ---------- Export ----------

    def _register_export_callbacks(self):
        @self.app.callback(
            Output("download-csv", "data"),
            Input("export-csv-btn", "n_clicks"),
            State("time-window", "value"),
            prevent_initial_call=True,
        )
        def _export_csv(n_clicks, time_window):
            if not n_clicks:
                raise PreventUpdate
            d = self._windowed_data(time_window or self.time_window)
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["Time", "T1", "T2", "SP1", "SP2", "U1", "U2"])
            for row in zip(d["time"], d["t1"], d["t2"], d["sp1"], d["sp2"], d["u1"], d["u2"]):
                writer.writerow(row)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return dcc.send_string(buf.getvalue(), filename=f"tclab_dashboard_{timestamp}.csv")

        @self.app.callback(
            Output("download-png", "data"),
            Input("export-png-btn", "n_clicks"),
            State("time-window", "value"),
            prevent_initial_call=True,
        )
        def _export_png(n_clicks, time_window):
            if not n_clicks:
                raise PreventUpdate
            fig = self._build_figure(int(time_window or self.time_window))
            png_bytes = pio.to_image(fig, format="png")
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return dcc.send_bytes(png_bytes, filename=f"tclab_dashboard_{timestamp}.png")

    # ================================================================
    # Run helpers
    # ================================================================

    def _run_app(self):
        self.app.run(
            host=self.host,
            port=self.port,
            debug=self.debug,
            dev_tools_serve_dev_bundles=self.serve_dev_bundles,
            use_reloader=False,
        )

    def start_background(self):
        if self.app_thread is None or not self.app_thread.is_alive():
            self.app_thread = threading.Thread(target=self._run_app, daemon=True)
            self.app_thread.start()

    def run(self):
        self._run_app()

    # ================================================================
    # Aggiornamento dati del grafico
    # ================================================================

    def get_values(self, T1, T2, U1, U2, SP1=None, SP2=None):
        """
        Aggiorna i buffer dei dati usati dal grafico e dai KPI.

        Da chiamare dal loop di controllo dopo aver letto T1,T2 e calcolato
        U1,U2 e (eventualmente) SP1,SP2. Se SP1/SP2 sono None (canale in
        manuale) la relativa curva di setpoint non viene plottata.
        """
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S")

            self.time_data.append(timestamp)
            self.t1_data.append(float(T1))
            self.t2_data.append(float(T2))
            self.u1_data.append(float(U1))
            self.u2_data.append(float(U2))

            self.sp1_data.append(float(SP1) if SP1 is not None else None)
            self.sp2_data.append(float(SP2) if SP2 is not None else None)

            if len(self.time_data) > self.max_points:
                excess = len(self.time_data) - self.max_points
                for lst in [
                    self.time_data,
                    self.t1_data,
                    self.t2_data,
                    self.sp1_data,
                    self.sp2_data,
                    self.u1_data,
                    self.u2_data,
                ]:
                    del lst[:excess]
