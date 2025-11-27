import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate

import threading
from datetime import datetime

import plotly.graph_objs as go
from plotly.subplots import make_subplots


class ControllerDashboard:
    """
    Dashboard Dash per il tuning di un insieme di controllori
    + visualizzazione delle variabili di processo.

    controllers: dict {nome_controller: istanza_controller}
                 ogni istanza deve implementare:
                   - getListOfParameters()
                   - getParameters()
                   - setParameters(dict)

    I grafici mostrano:
      - T1 e SP1
      - U1
      - T2 e SP2
      - U2

    I dati per il grafico vengono aggiornati tramite:
      get_values(T1, T2, SP1, SP2, U1, U2)
    """

    def __init__(
        self,
        controllers,
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
            controllers         : dict {nome_controller: istanza_controller}
            host                : host Flask/Dash
            port                : porta di ascolto
            debug               : flag debug Dash
            title               : titolo mostrato nella pagina
            serve_dev_bundles   : se True prova a servire i bundle .js non minificati
            start_in_background : se True avvia il server in un thread daemon
            plot_period         : periodo di refresh del grafico [s]
            time_window         : numero di punti da visualizzare
        """
        self.controllers = controllers
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

        # Crea app Dash
        self.app = dash.Dash(__name__)

        # Imposta layout e callback
        self.app.layout = self._create_layout()
        self._register_callbacks()

        self.app_thread = None

        if start_in_background:
            self.start_background()

    # ---------- Layout ----------

    def _create_layout(self):
        """
        Crea il layout: card parametri + sezione grafici.
        """
        cards = []

        for ctrl_name, ctrl in self.controllers.items():
            # Parametri del controller
            param_names = ctrl.getListOfParameters()
            params = ctrl.getParameters()

            param_inputs = []
            for p_name in param_names:
                value = params[p_name]

                if isinstance(value, (int, float)):
                    input_type = "number"
                else:
                    input_type = "text"

                param_inputs.append(
                    html.Div(
                        [
                            html.Label(p_name, style={"display": "block"}),
                            dcc.Input(
                                id={
                                    "type": "param-input",
                                    "controller": ctrl_name,
                                    "param": p_name,
                                },
                                type=input_type,
                                value=value,
                                debounce=True,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"marginBottom": "8px"},
                    )
                )

            card = html.Div(
                [
                    html.H3(f"Controller: {ctrl_name}"),
                    html.Div(param_inputs),
                    html.Button(
                        "Update",
                        id={"type": "update-btn", "controller": ctrl_name},
                        n_clicks=0,
                    ),
                    html.Div(
                        id={"type": "status", "controller": ctrl_name},
                        style={"marginTop": "8px", "color": "green"},
                    ),
                ],
                style={
                    "border": "1px solid #ccc",
                    "borderRadius": "8px",
                    "padding": "16px",
                    "marginBottom": "16px",
                    "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                },
            )

            cards.append(card)

        # Sezione grafico sotto le card dei parametri
        plot_section = html.Div(
            [
                html.H2(
                    "Andamento variabili di processo",
                    style={"marginTop": "40px", "marginBottom": "10px"},
                ),
                html.Div(
                    [
                        html.Label("Finestra temporale (n° dati da visualizzare)"),
                        dcc.Input(
                            id="time-window",
                            type="number",
                            value=self.time_window,
                            min=1,
                            step=1,
                            style={"width": "120px", "marginLeft": "8px"},
                        ),
                    ],
                    style={"marginBottom": "10px"},
                ),
                dcc.Graph(id="real-time-graph"),
                dcc.Interval(
                    id="interval-component",
                    interval=int(self.plot_period * 1000),
                    n_intervals=0,
                ),
            ],
            style={"marginTop": "30px"},
        )

        layout = html.Div(
            [
                html.H1(self.title),
                html.Div(
                    "Modifica i parametri e premi 'Update' per applicare i nuovi valori.",
                    style={"marginBottom": "20px"},
                ),
                html.Div(cards),
                plot_section,
            ],
            style={"maxWidth": "900px", "margin": "0 auto", "fontFamily": "sans-serif"},
        )

        return layout

    # ---------- Callbacks ----------

    def _register_callbacks(self):
        """
        Registra i callback:
          - update parametri controller
          - aggiornamento grafico in tempo reale
        """

        @self.app.callback(
            Output({"type": "status", "controller": MATCH}, "children"),
            Input({"type": "update-btn", "controller": MATCH}, "n_clicks"),
            State({"type": "param-input", "controller": MATCH, "param": ALL}, "value"),
            State({"type": "param-input", "controller": MATCH, "param": ALL}, "id"),
        )
        def update_controller_parameters(n_clicks, values, ids):
            if not n_clicks:
                raise PreventUpdate

            if not ids:
                return "Nessun parametro trovato."

            ctrl_name = ids[0]["controller"]
            ctrl = self.controllers[ctrl_name]

            param_update = {}
            for value, id_dict in zip(values, ids):
                p_name = id_dict["param"]
                if value is not None:
                    param_update[p_name] = value

            try:
                ctrl.setParameters(param_update)
            except Exception as e:
                return f"Errore aggiornando parametri: {e}"

            return "Parametri aggiornati con successo."

        @self.app.callback(
            Output("real-time-graph", "figure"),
            Input("interval-component", "n_intervals"),
            Input("time-window", "value"),
        )
        def update_graph(n, time_window):
            """
            Callback per aggiornare il grafico in base ai dati
            ricevuti via get_values().
            """
            if time_window is None or time_window < 1:
                time_window = self.time_window

            with self.lock:
                if not self.time_data:
                    time_data = []
                    t1 = []
                    t2 = []
                    sp1 = []
                    sp2 = []
                    u1 = []
                    u2 = []
                else:
                    max_tw = min(len(self.time_data), int(time_window))
                    time_data = self.time_data[-max_tw:]
                    t1 = self.t1_data[-max_tw:]
                    t2 = self.t2_data[-max_tw:]
                    sp1 = self.sp1_data[-max_tw:]
                    sp2 = self.sp2_data[-max_tw:]
                    u1 = self.u1_data[-max_tw:]
                    u2 = self.u2_data[-max_tw:]

            fig = make_subplots(
                rows=4,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=(
                    "Temperature (T1 / SP1)",
                    "Control Command (U1)",
                    "Temperature (T2 / SP2)",
                    "Control Command (U2)",
                ),
            )

            # T1
            fig.add_trace(
                go.Scatter(x=time_data, y=t1, mode="lines", name="T1"),
                row=1,
                col=1,
            )

            # SP1: solo se c'è almeno un valore non-None
            if any(v is not None for v in sp1):
                fig.add_trace(
                    go.Scatter(x=time_data, y=sp1, mode="lines", name="SP1"),
                    row=1,
                    col=1,
                )

            # U1
            fig.add_trace(
                go.Scatter(x=time_data, y=u1, mode="lines", name="U1"),
                row=2,
                col=1,
            )

            # T2
            fig.add_trace(
                go.Scatter(x=time_data, y=t2, mode="lines", name="T2"),
                row=3,
                col=1,
            )

            # SP2: solo se c'è almeno un valore non-None
            if any(v is not None for v in sp2):
                fig.add_trace(
                    go.Scatter(x=time_data, y=sp2, mode="lines", name="SP2"),
                    row=3,
                    col=1,
                )

            # U2
            fig.add_trace(
                go.Scatter(x=time_data, y=u2, mode="lines", name="U2"),
                row=4,
                col=1,
            )

            # Tick X ogni ~15 punti
            if len(time_data) > 0:
                tick_step = max(1, len(time_data) // 15)
                for r in [1, 2, 3, 4]:
                    fig.update_xaxes(
                        tickvals=[time_data[i] for i in range(0, len(time_data), tick_step)],
                        ticktext=[str(time_data[i]) for i in range(0, len(time_data), tick_step)],
                        row=r,
                        col=1,
                    )

            fig.update_layout(
                height=900,
                showlegend=True,
                margin=dict(l=40, r=10, t=40, b=40),
            )

            return fig

    # ---------- Run helpers ----------

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

    # ---------- Metodo per aggiornare i dati del grafico ----------

    def get_values(self, T1, T2, U1, U2, SP1=None, SP2=None):
        """
        Aggiorna i buffer dei dati usati dal grafico.

        Da chiamare dal loop di controllo, ad esempio dopo aver letto T1,T2
        e calcolato U1,U2 e (eventualmente) SP1,SP2.

        Se SP1 o SP2 sono None, NON vengono plottati (vedi callback del grafico).
        """
        from datetime import datetime  # se non l'hai già in cima al file

        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S")

            self.time_data.append(timestamp)
            self.t1_data.append(float(T1))
            self.t2_data.append(float(T2))
            self.u1_data.append(float(U1))
            self.u2_data.append(float(U2))

            # Se non sono forniti, salviamo None
            # (poi il callback decide se plottare o no)
            self.sp1_data.append(float(SP1) if SP1 is not None else None)
            self.sp2_data.append(float(SP2) if SP2 is not None else None)

            # Mantieni al massimo max_points campioni
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
