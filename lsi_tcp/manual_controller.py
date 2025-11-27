from typing import Optional
from lsi_tcp import BaseController


class ManualController(BaseController):
    """
    Controllore manuale: l'azione di controllo è semplicemente
        u = manual_control_action
    indipendentemente da reference, measure e feedforward.
    """

    def __init__(
        self,
        sampling_period: float = 1.0,
        u_min: Optional[float] = 0.0,
        u_max: Optional[float] = 100.0,
        manual_control_action: float = 0.0,
    ) -> None:
        # Inizializza la parte comune (sampling_period, u_min, u_max)
        super().__init__(sampling_period=sampling_period, u_min=u_min, u_max=u_max)

        # Aggiunge il parametro specifico del controllore manuale
        self.manual_control_action: float = manual_control_action
        self._parameters.update({
            "manual_control_action": manual_control_action
        })

    def computeControlAction(
        self,
        reference: float,
        measure: float,
        feedforward: float
    ) -> float:
        """
        Ritorna semplicemente u = manual_control_action (con saturazione).
        I parametri reference, measure, feedforward sono ignorati.
        """
        u = self.manual_control_action
        return self._apply_saturation(u)

    def starting(
        self,
        reference: float,
        measure: float,
        initial_u: float,
        feedforward: float
    ) -> None:
        """
        All'avvio, imposta U=manual_control_action.
        """
        self.manual_control_action = self.manual_control_action
