import threading
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple


@dataclass
class ChannelState:
    """
    Stato di UN canale, condiviso tra il thread Dash (callback della UI) e
    il thread del loop di controllo.
    """
    mode: str = "manual"     # "manual" oppure "auto"
    manual_u: float = 0.0    # potenza manuale corrente [%]
    setpoint: float = 20.0   # setpoint corrente [°C], impostato a mano dallo studente


class DashboardState:
    """
    Piccolo oggetto dedicato che isola TUTTO lo stato condiviso fra:
      - i callback Dash (thread del server, es. switch manuale/automatico,
        campo numerico adattivo, bottone pausa grafico);
      - il loop di controllo (thread separato, in utils.run_closed_loop).

    Niente variabili globali sparse: ogni lettura/scrittura passa da qui,
    protetta da un lock interno.
    """

    def __init__(self, channel_names: Iterable[str]):
        self._lock = threading.Lock()
        self._channels: Dict[str, ChannelState] = {
            name: ChannelState() for name in channel_names
        }
        self._paused = False

    # ---- modalità ----

    def get_mode(self, channel: str) -> str:
        with self._lock:
            return self._channels[channel].mode

    def set_mode(self, channel: str, mode: str) -> None:
        if mode not in ("manual", "auto"):
            raise ValueError("mode deve essere 'manual' o 'auto'")
        with self._lock:
            self._channels[channel].mode = mode

    # ---- valore manuale / setpoint ----

    def get_manual_u(self, channel: str) -> float:
        with self._lock:
            return self._channels[channel].manual_u

    def set_manual_u(self, channel: str, value: float) -> None:
        with self._lock:
            self._channels[channel].manual_u = float(value)

    def get_setpoint(self, channel: str) -> float:
        with self._lock:
            return self._channels[channel].setpoint

    def set_setpoint(self, channel: str, value: float) -> None:
        with self._lock:
            self._channels[channel].setpoint = float(value)

    def snapshot(self, channel: str) -> Tuple[str, float, float]:
        """Ritorna (mode, manual_u, setpoint) in un'unica lettura atomica."""
        with self._lock:
            s = self._channels[channel]
            return s.mode, s.manual_u, s.setpoint

    # ---- pausa grafico (non ferma l'acquisizione, solo il refresh plot) ----

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self._paused = bool(paused)

    def is_paused(self) -> bool:
        with self._lock:
            return self._paused
