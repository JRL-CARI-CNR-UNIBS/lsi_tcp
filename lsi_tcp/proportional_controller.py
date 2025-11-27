from lsi_tcp import  BaseController
class PController(BaseController):
    """
    Controllore proporzionale SISO con:
        - u_fb = Kp * (reference - measure)
        - u_ff = feedforward
        - u = u_fb + u_ff, con saturazione gestita dalla classe base
          tramite _apply_saturation().
    """

    def __init__(
        self,
        sampling_period: float,
        Kp: float = 1.0,
        u_min: float = 0.0,
        u_max: float = 100.0,
    ) -> None:
        # Inizializza la classe base: sampling_period, u_min, u_max
        super().__init__(sampling_period=sampling_period, u_min=u_min, u_max=u_max)

        # Aggiungi i parametri specifici del P
        self._parameters.update({
            "Kp": Kp,
        })

        # Esponi anche come attributo
        self.Kp = Kp

    def starting(
        self,
        reference: float,
        measure: float,
        initial_u: float,
        feedforward: float
    ) -> None:
        # Per il P puro non c'è stato interno da inizializzare.
        # Qui potresti fare controlli, logging, ecc.
        return

    def computeControlAction(
        self,
        reference: float,
        measure: float,
        feedforward: float
    ) -> float:
        # Errore
        error = reference - measure

        # Azione proporzionale di feedback
        u_fb = self.Kp * error

        # Somma con feedforward
        u = u_fb + feedforward

        # Saturazione tramite helper della classe base
        u = self._apply_saturation(u)

        return u
