from lsi_tcp import BaseController


class PIDController(BaseController):
    """
    Controllore PID SISO — DA COMPLETARE.

    Struttura attesa (vedi anche PController per il caso P puro, e
    linee_guida_controllore.md per la guida passo-passo P -> PI -> PID):
        - termine proporzionale: Kp * error
        - termine integrale:     Ki * integrale(error) (con anti-windup)
        - termine derivativo:    Kd * derivata_filtrata(error)
        - u = P + I + D, con saturazione gestita da _apply_saturation()
    """

    def __init__(
        self,
        sampling_period: float,
        # METTI QUI I PARAMETRI
        u_min: float = 0.0,
        u_max: float = 100.0,
    ) -> None:
        # Inizializza la classe base: sampling_period, u_min, u_max
        super().__init__(sampling_period=sampling_period, u_min=u_min, u_max=u_max)

        # Parametri specifici del PID
        self._parameters.update({
            # INSERIRE CODICE
        })

        # Esponi anche come attributi
        # INSERIRE CODICE

    def starting(
        self,
        reference: float,
        measure: float,
        initial_u: float,
    ) -> None:
        """
        Inizializza gli stati interni del controllore (integratore, derivata
        filtrata, errore precedente, ...). Viene chiamata prima di
        run_closed_loop e ad ogni cambio manuale -> automatico (bumpless
        transfer).
        """
        # inserisci il tuo codice qui
        pass

    def computeControlAction(
        self,
        reference: float,
        measure: float,
    ) -> float:
        """
        Calcola l'azione di controllo u a partire da reference e measure.
        """
        # inserisci il tuo codice qui
        # 1. calcola l'errore (reference - measure)
        # 2. calcola il termine proporzionale
        # 3. aggiorna e calcola il termine integrale (con anti-windup, vedi
        #    docs/Antiwindup.md)
        # 4. aggiorna e calcola il termine derivativo filtrato (vedi
        #    docs/linee_guida_controllore.md, §5)
        # 5. somma i tre termini e applica la saturazione con
        #    self._apply_saturation(u)
        # 6. aggiorna lo stato per il prossimo passo (es. errore precedente)
        raise NotImplementedError("Implementare PIDController.computeControlAction")
