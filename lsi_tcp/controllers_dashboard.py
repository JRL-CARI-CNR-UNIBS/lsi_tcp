import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate

import threading


class ControllerDashboard:
    """
    Dashboard Dash per il tuning di un insieme di controllori.

    controllers: dict {nome_controller: istanza_controller}
                 ogni istanza deve implementare:
                   - getListOfParameters()
                   - getParameters()
                   - setParameters(dict)
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
        """
        self.controllers = controllers
        self.host = host
        self.port = port
        self.debug = debug
        self.title = title
        self.serve_dev_bundles = serve_dev_bundles

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
        Crea il layout (lista di "card") per tutti i controllori.
        """
        cards = []

        for ctrl_name, ctrl in self.controllers.items():
            # Ottieni la lista ordinata dei parametri e i valori correnti
            param_names = ctrl.getListOfParameters()
            params = ctrl.getParameters()

            param_inputs = []
            for p_name in param_names:
                value = params[p_name]

                # Scegli un tipo di input sensato
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

        layout = html.Div(
            [
                html.H1(self.title),
                html.Div(
                    "Modifica i parametri e premi 'Update' per applicare i nuovi valori.",
                    style={"marginBottom": "20px"},
                ),
                html.Div(cards),
            ],
            style={"maxWidth": "600px", "margin": "0 auto", "fontFamily": "sans-serif"},
        )

        return layout

    # ---------- Callbacks ----------

    def _register_callbacks(self):
        """
        Registra i callback Dash per la gestione degli update dei parametri.
        Usiamo MATCH/ALL per avere un callback per card (per controller).
        """

        @self.app.callback(
            Output({"type": "status", "controller": MATCH}, "children"),
            Input({"type": "update-btn", "controller": MATCH}, "n_clicks"),
            State({"type": "param-input", "controller": MATCH, "param": ALL}, "value"),
            State({"type": "param-input", "controller": MATCH, "param": ALL}, "id"),
        )
        def update_controller_parameters(n_clicks, values, ids):
            """
            Callback chiamata quando si preme il pulsante Update
            di uno specifico controller.
            """
            if not n_clicks:
                # Se il bottone non è stato premuto, non fare nulla
                raise PreventUpdate

            if not ids:
                return "Nessun parametro trovato."

            # Tutti gli id hanno lo stesso 'controller'
            ctrl_name = ids[0]["controller"]
            ctrl = self.controllers[ctrl_name]

            # Costruisci il dizionario {nome_parametro: valore}
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

    # ---------- Run helpers ----------

    def _run_app(self):
        """
        Esegue app.run con reloader disabilitato (necessario in thread secondario).
        """
        self.app.run(
            host=self.host,
            port=self.port,
            debug=self.debug,
            dev_tools_serve_dev_bundles=self.serve_dev_bundles,
            use_reloader=False,  # <-- evita il problema dei signal nel thread
        )

    def start_background(self):
        """
        Avvia il server in un thread daemon (non bloccante).
        """
        if self.app_thread is None or not self.app_thread.is_alive():
            self.app_thread = threading.Thread(target=self._run_app, daemon=True)
            self.app_thread.start()

    def run(self):
        """
        Avvia il server in modo bloccante (main thread).
        """
        self._run_app()
