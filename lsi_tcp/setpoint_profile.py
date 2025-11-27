import csv
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class SetpointSample:
    t: float
    T1: float
    T2: float


class SetpointProfile:
    """
    Gestisce un profilo di setpoint periodico letto da CSV.

    Il CSV deve avere intestazioni: t, T1, T2
    - t in secondi (tempo dall'inizio)
    - T1, T2 setpoint per i due loop
    Il profilo è considerato periodico: quando t > t_end, si ricomincia da t=0.
    """

    def __init__(self, csv_path: str, interpolate: bool = False):
        self.samples: List[SetpointSample] = []

        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            # ci aspettiamo colonne: t, T1, T2
            for row in reader:
                self.samples.append(
                    SetpointSample(
                        t=float(row["t"]),
                        T1=float(row["T1"]),
                        T2=float(row["T2"]),
                    )
                )

        if not self.samples:
            raise ValueError("Profilo di setpoint vuoto: il CSV non contiene righe.")

        # Assicuro ordinamento per tempo
        self.samples.sort(key=lambda s: s.t)

        # Controlli base
        if self.samples[0].t != 0.0:
            raise ValueError("Il primo tempo nel CSV deve essere t=0.")

        self.t_end = self.samples[-1].t
        if self.t_end <= 0:
            raise ValueError("t_end deve essere > 0.")

        self.interpolate = interpolate

    def get_setpoints(self, t: float) -> Tuple[float, float]:
        """
        Restituisce (T1_ref, T2_ref) per il tempo t [s].
        Il profilo è periodico: uso t_mod = t % t_end.
        """
        if t < 0:
            t = 0.0

        # tempo "modulato" sul periodo
        t_mod = t % self.t_end

        # Se t_mod <= primo campione, restituisco il primo
        if t_mod <= self.samples[0].t:
            s0 = self.samples[0]
            return s0.T1, s0.T2

        prev = self.samples[0]
        # Cerco l'intervallo [prev, s] in cui cade t_mod
        for s in self.samples[1:]:
            if t_mod <= s.t:
                if not self.interpolate:
                    # Zero-Order Hold: mantengo il valore precedente
                    return prev.T1, prev.T2

                # Interpolazione lineare tra prev e s
                dt = s.t - prev.t
                if dt <= 0:
                    # tempi uguali o ordinamento strano: fallback ZOH
                    return prev.T1, prev.T2

                alpha = (t_mod - prev.t) / dt
                T1 = prev.T1 + alpha * (s.T1 - prev.T1)
                T2 = prev.T2 + alpha * (s.T2 - prev.T2)
                return T1, T2

            prev = s

        # In teoria non dovremmo arrivare qui, ma per sicurezza:
        last = self.samples[-1]
        return last.T1, last.T2
