import tclab
import time
import threading
import csv
from datetime import datetime
import logging
import math
from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Dict, List


class BaseTCLabSystem(ABC):
    """
    ABC per sistemi tipo TCLab (reali o simulati).

    Gestisce:
    - thread di acquisizione
    - logging su CSV
    - buffer dati (time_data, t1_data, ...)
      (NON fa più la dashboard: niente Dash/Plotly qui)

    Le sottoclassi DEVONO implementare:
        _initialize_lab()
        readProcessVariables()
        _apply_control(u1, u2)
        _close_lab()
    """

    def __init__(self, log_flag=False, log_interval=1.0,
                 plot_period=1.0, time_window=300,
                 realtime_factor=1.0):
        # Imposta il livello di log di Flask per evitare la verbosità
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        # Parametri generali
        self.log_flag = log_flag
        self.log_interval = float(log_interval)
        self.plot_period = float(plot_period)   # tenuti per compatibilità
        self.time_window = int(time_window)     # tenuti per compatibilità

        # Fattore di tempo (1.0 = reale)
        self.realtime_factor = float(realtime_factor) if realtime_factor > 0 else 1.0

        self.running = True

        # Lock per thread-safety
        self.lock = threading.Lock()

        # Buffer dati
        self.time_data = []
        self.t1_data = []
        self.t2_data = []
        self.u1_data = []
        self.u2_data = []

        self.u1 = 0.0
        self.u2 = 0.0

        # Tempo iniziale (base per il tempo simulato)
        self.start_time = datetime.now()

        # File di log (solo se log_flag è True)
        self.log_file = None
        if self.log_flag:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            self.log_file = open(f'tclab_{timestamp}.csv', mode='w', newline='')
            self.csv_writer = csv.writer(self.log_file)
            self.csv_writer.writerow(['Time', 'T1', 'T2', 'U1', 'U2'])

        # Inizializzazione specifica (hardware o simulatore)
        self._initialize_lab()

        # Thread di acquisizione
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    # --------- Utilità tempo simulato ----------

    def _get_sim_time(self):
        """
        Ritorna il tempo simulato come:

            t_sim = t_start + (now - t_start) * realtime_factor
        """
        now = datetime.now()
        delta = now - self.start_time
        return self.start_time + delta * self.realtime_factor

    # --------- Metodi astratti da implementare nelle sottoclassi ----------

    @abstractmethod
    def _initialize_lab(self):
        """Inizializzazione specifica del 'laboratorio' (hardware o simulatore)."""
        pass

    @abstractmethod
    def readProcessVariables(self):
        """
        Legge le variabili di processo (T1, T2).

        Deve restituire: (t1, t2)
        """
        pass

    @abstractmethod
    def _apply_control(self, u1, u2):
        """
        Applica i comandi di controllo (ai riscaldatori fisici o al modello).

        Parametri:
        - u1, u2 in [0, 100]
        """
        pass

    @abstractmethod
    def _close_lab(self):
        """Chiusura e clean-up specifico (es. chiudere la board o niente per fake)."""
        pass

    # ---------------- Metodi concreti comuni ------------------------------

    def _run(self):
        """Ciclo principale per leggere/loggare i dati."""
        while self.running:
            # Legge le variabili di processo
            t1, t2 = self.readProcessVariables()

            # Tempo simulato per timestamp
            sim_time = self._get_sim_time()
            timestamp = sim_time.strftime("%H:%M:%S")

            # Aggiorna buffer
            with self.lock:
                self.time_data.append(timestamp)
                self.t1_data.append(t1)
                self.t2_data.append(t2)
                self.u1_data.append(self.u1)
                self.u2_data.append(self.u2)

            # Log dei dati (se log_flag è attivo)
            if self.log_flag:
                self._log_data(t1, t2, self.u1, self.u2)

            # Pausa per il periodo di ciclo definito, scalato dal realtime_factor
            if self.realtime_factor > 0:
                effective_sleep = self.log_interval / self.realtime_factor
            else:
                effective_sleep = self.log_interval
            time.sleep(effective_sleep)

    def writeControlCommands(self, u1=0, u2=0):
        """Imposta i comandi di controllo manualmente, con controllo dei limiti."""
        with self.lock:
            u1 = max(0, min(100, float(u1)))
            u2 = max(0, min(100, float(u2)))

            # Scrivi i comandi di controllo (specifico della sottoclasse)
            self._apply_control(u1, u2)
            self.u1 = u1
            self.u2 = u2

        return u1, u2

    def _log_data(self, t1, t2, u1, u2):
        """Scrive i dati su file CSV con timestamp simulato."""
        if not self.log_flag:
            return

        with self.lock:
            sim_time = self._get_sim_time()
            timestamp = sim_time.strftime("%Y-%m-%d %H:%M:%S")
            self.csv_writer.writerow([timestamp, t1, t2, u1, u2])
            self.log_file.flush()

    def stop(self):
        """Ferma i thread e chiude il file di log."""
        self.running = False
        self.thread.join()

        if self.log_flag and self.log_file:
            self.log_file.close()

        # Chiusura specifica della sottoclasse
        self._close_lab()


# -------------------------------------------------------------------------
#  Implementazione reale con TCLab (hardware)
# -------------------------------------------------------------------------

class TCLabSystem(BaseTCLabSystem):
    """Implementazione reale con la board TCLab.

    realtime_factor è implicitamente 1.0 (default del BaseTCLabSystem).
    """

    def __init__(self, log_flag=False, log_interval=1.0,
                 plot_period=1.0, time_window=300):
        super().__init__(log_flag=log_flag,
                         log_interval=log_interval,
                         plot_period=plot_period,
                         time_window=time_window,
                         realtime_factor=1.0)

    def _initialize_lab(self):
        self.lab = tclab.TCLab()

    def readProcessVariables(self):
        with self.lock:
            t1 = self.lab.T1
            t2 = self.lab.T2
        return t1, t2

    def _apply_control(self, u1, u2):
        # Comandi reali alla board
        self.lab.Q1(u1)
        self.lab.Q2(u2)

    def _close_lab(self):
        # Chiusura della board
        self.lab.close()


# -------------------------------------------------------------------------
#  Implementazione Fake: FOPDT per (T1/U1) e (T2/U2)
# -------------------------------------------------------------------------

class FakeTCLabSystem(BaseTCLabSystem):
    """
    Simulatore del TCLab:

    - T1/U1: FOPDT con (K1, tau1, L1)
    - T2/U2: FOPDT con (K2, tau2, L2)

    Modello:
        dT/dt = (-(T - Tamb) + K * u_delayed) / tau
        u_delayed(t) = u(t - L)

    Gestione parametri:
        K1, tau1, L1, K2, tau2, L2 sono esposti con lo stesso pattern
        usato in BaseController: self._parameters + getListOfParameters() /
        setParameters() / getParameters(). K e tau sono liberamente
        modificabili a runtime; L è modificabile a runtime ma solo entro
        il tetto massimo L_max, fissato in costruzione e non modificabile
        in seguito.

    Dead-time:
        implementato con un buffer a lunghezza FISSA (deque(maxlen=n_max),
        dimensionato su L_max), riempito ad ogni passo con append() e MAI
        svuotato con popleft(). Il valore ritardato si legge per
        indicizzazione (self._u1_buffer[-(n_delay + 1)]), con n_delay
        ricalcolato dalla L corrente ad ogni lettura: questo permette di
        cambiare L a runtime senza mai ridimensionare il buffer.

    realtime_factor > 1: sim più veloce del tempo reale
    realtime_factor < 1: sim più lenta del tempo reale
    """

    def __init__(self,
                 log_flag=False,
                 log_interval=1.0,
                 plot_period=1.0,
                 time_window=300,
                 K1=0.8, tau1=100.0, L1=10.0,
                 K2=0.5, tau2=120.0, L2=15.0,
                 Tamb=23.0,
                 L_max=60.0,
                 u0=0.0,
                 realtime_factor=1.0):
        """
        L_max: tetto massimo per il ritardo [s]. Non modificabile a runtime;
               dimensiona il buffer del dead-time. L1 e L2 non possono
               superarlo, né in costruzione né in setParameters().
        u0:    valore costante con cui viene pre-riempito il buffer del
               dead-time, per evitare un gradino fittizio nei primi
               passi di simulazione (invece di riempirlo con zeri).
        """
        if L_max <= 0:
            raise ValueError("L_max deve essere > 0")
        if L1 > L_max:
            raise ValueError(f"L1={L1} non può superare L_max={L_max}")
        if L2 > L_max:
            raise ValueError(f"L2={L2} non può superare L_max={L_max}")

        self.Tamb = float(Tamb)
        self.L_max = float(L_max)
        self._u0 = float(u0)

        # Parametri del modello, gestiti con lo stesso pattern di BaseController
        self._parameters: Dict[str, Any] = {
            "K1": float(K1), "tau1": float(tau1), "L1": float(L1),
            "K2": float(K2), "tau2": float(tau2), "L2": float(L2),
        }
        for name, value in self._parameters.items():
            setattr(self, name, value)

        # Inizializza il BaseTCLabSystem con realtime_factor settabile
        super().__init__(log_flag=log_flag,
                         log_interval=log_interval,
                         plot_period=plot_period,
                         time_window=time_window,
                         realtime_factor=realtime_factor)

    def _initialize_lab(self):
        # Stati iniziali
        self.T1 = self.Tamb
        self.T2 = self.Tamb

        # Timestamp dell'ultimo avanzamento del modello, usato per calcolare
        # il dt REALMENTE trascorso tra due letture (vedi _advance_model):
        # readProcessVariables() può essere chiamato da più punti (thread di
        # acquisizione, loop di controllo) e il modello deve avanzare in base
        # al tempo simulato davvero trascorso, non di un passo fisso per
        # chiamata (altrimenti la dinamica risulterebbe più veloce di quanto
        # dichiarato dai parametri K/tau/L se letta da più punti).
        self._last_advance_time = time.monotonic()

        dt = self.log_interval if self.log_interval > 0 else 1.0

        # Buffer a lunghezza fissa dimensionato sul massimo ritardo possibile
        # (L_max), con un campione di margine per l'indicizzazione
        # self._u_buffer[-(n_delay + 1)]. Il buffer non viene MAI
        # ridimensionato: cambiare L a runtime cambia solo n_delay.
        n_max = max(1, int(math.ceil(self.L_max / dt))) + 1

        # Pre-riempito con u0 costante (non zeri) per evitare un gradino
        # fittizio nei primi n_max passi di simulazione.
        self._u1_buffer = deque([self._u0] * n_max, maxlen=n_max)
        self._u2_buffer = deque([self._u0] * n_max, maxlen=n_max)

    def _advance_model(self, dt):
        """
        Aggiorna il modello FOPDT per T1 e T2 di un passo dt.

        dt in [s].
        """
        if dt <= 0.0:
            return

        # Riempimento del buffer: SEMPRE append(), mai popleft(). Il buffer
        # ha lunghezza fissa (maxlen), quindi l'append più vecchio esce da solo.
        self._u1_buffer.append(self.u1)
        self._u2_buffer.append(self.u2)

        # n_delay ricalcolato dalla L corrente ad ogni lettura: L può essere
        # cambiata a runtime (entro L_max) senza mai toccare il buffer.
        # Nota: n_delay = round(L / dt) introduce un errore di arrotondamento
        # quando L non è multiplo esatto di dt (log_interval). Alle frequenze
        # tipiche del TCLab (dt ~ 1 s, L decine di secondi) l'errore è
        # trascurabile: è una scelta consapevole, non una svista.
        # Clamp difensivo: con un dt reale molto piccolo (due chiamate a
        # readProcessVariables() ravvicinate) n_delay potrebbe eccedere la
        # lunghezza del buffer; lo limitiamo all'indice massimo disponibile.
        max_index = len(self._u1_buffer) - 1
        n_delay1 = min(int(round(self.L1 / dt)), max_index)
        n_delay2 = min(int(round(self.L2 / dt)), max_index)

        u1_delayed = self._u1_buffer[-(n_delay1 + 1)]
        u2_delayed = self._u2_buffer[-(n_delay2 + 1)]

        # Eulero esplicito
        if self.tau1 > 0:
            self.T1 += dt / self.tau1 * (-(self.T1 - self.Tamb) + self.K1 * u1_delayed)

        if self.tau2 > 0:
            self.T2 += dt / self.tau2 * (-(self.T2 - self.Tamb) + self.K2 * u2_delayed)

    def readProcessVariables(self):
        """
        Per la versione Fake, ogni lettura:

        - fa avanzare il modello del tempo simulato REALMENTE trascorso
          dall'ultima lettura (dt = tempo reale trascorso * realtime_factor),
          non di un incremento fisso per chiamata. Così il modello avanza
          correttamente anche se readProcessVariables() viene chiamato da
          più punti (thread di acquisizione + loop di controllo) con
          frequenze diverse.
        - restituisce T1, T2 aggiornati
        """
        now = time.monotonic()

        with self.lock:
            dt = (now - self._last_advance_time) * self.realtime_factor
            self._last_advance_time = now
            self._advance_model(dt)
            t1 = self.T1
            t2 = self.T2

        return t1, t2

    def _apply_control(self, u1, u2):
        """Nel fake non c'è hardware: memorizzo solo i comandi."""
        pass

    def _close_lab(self):
        """Niente da chiudere per il simulatore."""
        pass

    # ---------------- Gestione parametri (stesso pattern di BaseController) ----

    def getListOfParameters(self) -> List[str]:
        """Ritorna la lista dei nomi dei parametri settabili del modello."""
        return list(self._parameters.keys())

    def setParameters(self, parameter_dict: Dict[str, Any]) -> None:
        """
        Imposta i parametri del modello a partire da {nome: valore}.

        K1, tau1, K2, tau2 sono liberamente modificabili. L1, L2 sono
        modificabili a runtime solo entro L_max (oltre, ValueError):
        il buffer del dead-time è dimensionato una volta per tutte su
        L_max e non viene mai ridimensionato.
        """
        new_L1 = parameter_dict.get("L1", self.L1)
        new_L2 = parameter_dict.get("L2", self.L2)

        if new_L1 > self.L_max:
            raise ValueError(f"L1={new_L1} non può superare L_max={self.L_max}")
        if new_L2 > self.L_max:
            raise ValueError(f"L2={new_L2} non può superare L_max={self.L_max}")

        for name, value in parameter_dict.items():
            if name not in self._parameters:
                raise KeyError(
                    f"Parametro '{name}' non valido per {type(self).__name__}. "
                    f"Parametri validi: {self.getListOfParameters()}"
                )
            self._parameters[name] = value
            setattr(self, name, value)

    def getParameters(self) -> Dict[str, Any]:
        """Restituisce una COPIA dei parametri correnti del modello."""
        return dict(self._parameters)
