from .dashboard_state import DashboardState


class ChannelRuntime:
    """
    Coordina, per UN canale, i due controllori SEMPRE istanziati
    (ManualController + controllore automatico dello studente) e la
    modalità corrente (letta da un DashboardState condiviso con la
    dashboard).

    Nessun 'if' dentro le classi controllore: qui, e solo qui, vive la
    logica che decide quale dei due controllori calcola u in una data
    iterazione, e la logica di bumpless transfer al cambio di modalità:

        - auto -> manuale: il ManualController riparte da
          initial_u = ultima azione calcolata dall'automatico;
        - manuale -> auto: il controllore automatico riparte da
          reference = setpoint appena impostato dallo studente,
          measure   = temperatura corrente.
    """

    def __init__(
        self,
        name: str,
        manual_controller,
        auto_controller,
        state: DashboardState,
        initial_mode: str = "manual",
    ) -> None:
        self.name = name
        self.manual_controller = manual_controller
        self.auto_controller = auto_controller
        self.state = state

        self._mode = initial_mode
        self.state.set_mode(name, initial_mode)
        self._last_auto_u = 0.0

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def active_controller(self):
        return self.manual_controller if self._mode == "manual" else self.auto_controller

    def _switch_mode(self, new_mode: str, measure: float, setpoint: float) -> None:
        if new_mode == self._mode:
            return

        if new_mode == "manual":
            # auto -> manuale: bumpless transfer con l'ultima azione dell'automatico.
            # Aggiorno anche lo stato condiviso (manual_u), altrimenti al prossimo
            # step() lo risincronizzerei con il vecchio valore del campo numerico
            # e vanificherei il bumpless transfer appena fatto.
            self.state.set_manual_u(self.name, self._last_auto_u)
            self.manual_controller.setParameters({"manual_control_action": self._last_auto_u})
            self.manual_controller.starting(
                reference=setpoint,
                measure=measure,
                initial_u=self._last_auto_u,
                feedforward=0.0,
            )
        else:
            # manuale -> auto: riparte dal setpoint appena impostato e dalla misura corrente
            self.auto_controller.starting(
                reference=setpoint,
                measure=measure,
                initial_u=self.manual_controller.manual_control_action,
                feedforward=0.0,
            )

        self._mode = new_mode

    def step(self, measure: float, feedforward: float = 0.0):
        """
        Da chiamare una volta per ciclo di controllo.

        Ritorna (u, reference_da_plottare):
          - reference_da_plottare è il setpoint corrente in automatico,
            None in manuale (per non plottare la curva di setpoint).
        """
        mode, manual_u, setpoint = self.state.snapshot(self.name)

        self._switch_mode(mode, measure=measure, setpoint=setpoint)

        if self._mode == "manual":
            self.manual_controller.setParameters({"manual_control_action": manual_u})
            u = self.manual_controller.computeControlAction(
                reference=setpoint, measure=measure, feedforward=feedforward
            )
            return u, None

        u = self.auto_controller.computeControlAction(
            reference=setpoint, measure=measure, feedforward=feedforward
        )
        self._last_auto_u = u
        return u, setpoint
