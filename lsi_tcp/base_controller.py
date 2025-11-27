from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseController(ABC):
    """
    Classe base astratta per controllori SISO (single-input-single-output).

    Interfaccia minima che ogni controllore derivato deve rispettare:
        - u = computeControlAction(reference, measure, feedforward)
        - starting(reference, measure, initial_u, feedforward)
        - getListOfParameters()
        - setParameters(parameter_dict)

    Convenzioni:
        - reference: valore di setpoint / riferimento (r)
        - measure: misura dell'uscita di processo (y)
        - feedforward: contributo di controllo in anticipo (es. modello)
        - u: azione di controllo complessiva da inviare all’attuatore
        - sampling_period: periodo di campionamento [s] (dt)
        - u_min, u_max: limiti di saturazione dell’azione di controllo.
                        Se uno dei due è None, il limite corrispondente non viene applicato.

    Le sottoclassi DEVONO:
        - chiamare super().__init__(sampling_period=..., u_min=..., u_max=...) nel proprio __init__
        - eventualmente aggiungere altri parametri a self._parameters con .update(...)
    """

    def __init__(
        self,
        sampling_period: float = 1.0,
        u_min: Optional[float] = 0.0,
        u_max: Optional[float] = 100.0,
    ) -> None:
        """
        Inizializza il controllore base con periodo di campionamento e saturazioni.

        Parametri:
            - sampling_period: periodo di campionamento [s], deve essere > 0.
            - u_min: limite inferiore della variabile di controllo (o None per nessun limite inferiore).
            - u_max: limite superiore della variabile di controllo (o None per nessun limite superiore).
        """
        if sampling_period <= 0:
            raise ValueError("sampling_period deve essere > 0")

        if (u_min is not None) and (u_max is not None) and (u_min >= u_max):
            raise ValueError("u_min deve essere < u_max")

        # Dizionario interno dei parametri del controllore.
        # Contiene SEMPRE almeno: sampling_period, u_min, u_max.
        self._parameters: Dict[str, Any] = {
            "sampling_period": sampling_period,
            "u_min": u_min,
            "u_max": u_max,
        }

        # Esponi anche come attributi per uso diretto nelle sottoclassi
        self.sampling_period: float = sampling_period
        self.u_min: Optional[float] = u_min
        self.u_max: Optional[float] = u_max

    # --- Metodi astratti principali ---

    @abstractmethod
    def computeControlAction(
        self,
        reference: float,
        measure: float,
        feedforward: float
    ) -> float:
        """
        Calcola l'azione di controllo u a partire da:

            - reference: riferimento (setpoint)
            - measure: misura dell’uscita
            - feedforward: contributo in feedforward

        Il comportamento tipico in una sottoclasse può essere, ad esempio:
            u = u_feedback(reference, measure) + feedforward
            u = self._apply_saturation(u)

        Questo metodo:
            - può aggiornare lo stato interno del controllore (es. integratore),
              se previsto dal tipo di controllore.
            - deve restituire un valore float che rappresenta l’azione di controllo
              da inviare al processo.
        """
        pass

    @abstractmethod
    def starting(
        self,
        reference: float,
        measure: float,
        initial_u: float,
        feedforward: float
    ) -> None:
        """
        Esegue la fase di inizializzazione del controllore.

        Tipici utilizzi:
            - Azzerare o inizializzare l’integratore.
            - Allineare eventuali stati interni alla condizione iniziale del processo.
            - Eseguire logiche di "bumpless transfer" se si passa da manuale ad automatico.

        Parametri:
            - reference: riferimento iniziale al momento dello start.
            - measure: misura iniziale dell’uscita.
            - initial_u: azione di controllo iniziale (ad es. quella in manuale)
                         con cui si vuole partire.
            - feedforward: eventuale valore di feedforward attivo all’avvio.
        """
        pass

    # --- Helper comuni ---

    def _apply_saturation(self, u: float) -> float:
        """
        Applica la saturazione all'azione di controllo u usando u_min e u_max.

        Comportamento:
            - Se u_min è None: nessun limite inferiore.
            - Se u_max è None: nessun limite superiore.
        """
        if (self.u_min is not None) and (u < self.u_min):
            return self.u_min
        if (self.u_max is not None) and (u > self.u_max):
            return self.u_max
        return u

    # --- Gestione parametri ---

    def getListOfParameters(self) -> List[str]:
        """
        Ritorna la lista dei nomi dei parametri settabili del controllore.

        Esempio:
            controller._parameters = {"sampling_period": 1.0, "u_min": 0.0, "u_max": 100.0, "Kp": 2.0}
            controller.getListOfParameters() -> ["sampling_period", "u_min", "u_max", "Kp"]
        """
        return list(self._parameters.keys())

    def setParameters(self, parameter_dict: Dict[str, Any]) -> None:
        """
        Imposta i parametri del controllore a partire da un dizionario
        {nome_parametro: valore}.

        Comportamento:
            - Per ogni coppia (name, value) nel dizionario:
                * Se 'name' è un parametro riconosciuto (presente in self._parameters),
                  aggiorna il valore sia in self._parameters, sia come attributo
                  dell’istanza (self.name).
                * Se 'name' NON è riconosciuto, solleva KeyError.

        Nota:
            - È consentito modificare 'sampling_period', 'u_min' e 'u_max' a runtime,
              con i seguenti vincoli:
                * sampling_period > 0
                * se entrambi non-None: u_min < u_max
        """
        # Pre-calcola i nuovi limiti se presenti nel dict per validazione congiunta
        new_sampling_period = parameter_dict.get("sampling_period", self.sampling_period)
        new_u_min = parameter_dict.get("u_min", self.u_min)
        new_u_max = parameter_dict.get("u_max", self.u_max)

        # Validazioni generali
        if new_sampling_period <= 0:
            raise ValueError("sampling_period deve essere > 0")

        if (new_u_min is not None) and (new_u_max is not None) and (new_u_min >= new_u_max):
            raise ValueError("u_min deve essere < u_max")

        # Se tutte le validazioni passano, applica i parametri
        for name, value in parameter_dict.items():
            if name not in self._parameters:
                raise KeyError(
                    f"Parametro '{name}' non valido per {type(self).__name__}. "
                    f"Parametri validi: {self.getListOfParameters()}"
                )

            self._parameters[name] = value
            setattr(self, name, value)

    def getParameters(self) -> Dict[str, Any]:
        """
        Restituisce una COPIA dei parametri correnti del controllore.
        """
        return dict(self._parameters)
