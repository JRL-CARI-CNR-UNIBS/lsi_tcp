# 5. Guida al progetto degli studenti

Di seguito una **roadmap pratica** che collega il codice del repository ai tre step richiesti.

## 5.1. Preparare il codice
Creare una cartella di lavoro (non tclab)

## 5.2. Step 1 – Prova di identificazione (anello aperto)

Script per il controllo manuale (da copiare nella cartella di lavoro,
uguale a `example_open_loop.py` nella root del repo):

```python
from lsi_tcp import TCLabSystem, FakeTCLabSystem
from lsi_tcp import ManualController
from lsi_tcp import ControllerDashboard
from lsi_tcp import build_process, build_channels, init_channels, run_closed_loop
import time

# ==========================
# Configurazione generale
# ==========================

USE_FAKE = True            # True -> usa FakeTCLabSystem, False -> hardware reale
SAMPLING_PERIOD = 1.0      # [s]

def build_controllers(sampling_period: float):
    """
    Nessun controllore automatico ancora: entrambi i canali restano in
    ManualController (la potenza U si imposta a mano dalla dashboard).
    """
    c1 = ManualController(
        sampling_period=sampling_period,
        manual_control_action=0.0,
        u_min=0.0,
        u_max=100.0,
    )

    c2 = ManualController(
        sampling_period=sampling_period,
        manual_control_action=0.0,
        u_min=0.0,
        u_max=100.0,
    )

    return {
        "channel1": c1,
        "channel2": c2,
    }


def main():
    process, real_time_factor = build_process(USE_FAKE)
    controllers = build_controllers(SAMPLING_PERIOD)
    runtimes, state = build_channels(controllers, sampling_period=SAMPLING_PERIOD)
    init_channels(runtimes, state, process)

    run_closed_loop(
        process=process,
        runtimes=runtimes,
        state=state,
        real_time_factor=real_time_factor,
        is_simulator=USE_FAKE,
        max_duration=5*3600.0,
    )


if __name__ == "__main__":
    main()

```

1. **Preparazione del sistema**
   - scegliete se lavorare in simulazione (`USE_FAKE = True`) o con l’hardware reale (`USE_FAKE = False`);
   - impostate la frequenza di campionamento (`SAMPLING_PERIOD`, tipicamente 1 s).

2. **Esecuzione della prova**
   - partite con `U1 = U2 = 0%` e lasciate stabilizzare le temperature;
   - applicate un gradino su `U1` (es. da 0% a 40–60%);
   - mantenete il gradino per un tempo sufficiente a raggiungere un nuovo regime;
   - effettuate più prove con ampiezze di gradino diverse;
   - ripetete per `U2`.

3. **Raccolta dati**
   - assicuratevi che `log_flag=True` in `TCLabSystem` / `FakeTCLabSystem`;
   - al termine otterrete un file CSV `tclab_YYYYMMDDHHMMSS.csv` con colonne `Time, T1, T2, U1, U2`.

## 5.3. Step 2 – Modellazione FOPDT dai CSV

Questo step si svolge in **MATLAB**, non in Python: caricate il CSV
prodotto dallo Step 1 (colonne `Time, T1, T2, U1, U2`) e applicate il metodo
del 10%-90% già visto in un corso precedente (potete anche fare i conti a
mano, senza script, se preferite).

1. **Caricate il CSV** e costruite l'asse dei tempi in secondi (la colonna
   `Time` è un timestamp simulato: convertitelo in secondi rispetto al primo
   campione).

2. **Individuate il gradino**

   - verificate dove `U1` (o `U2`) cambia valore;
   - calcolate `U_initial` e `U_final`.

3. **Stima dei parametri FOPDT**

   Per ciascuna temperatura di interesse (es. T1 per un gradino su U1):

   - valore iniziale $T_0$ e valore finale $T_\infty$;
   - guadagno:

     $$K =\frac{T_\infty - T_0}{U_\text{final} - U_\text{initial}}$$
   - $t_{10}$ tempo in cui si raggiunge il 10\% della variazione
   - $t_{90}$ tempo in cui si raggiunge il 90\% della variazione
   - Costante di tempo $\tau=\frac{t_{90}-t_{10}}{2.2}$.
   - tempo morto $L=t_{10}-0.1\tau$


4. **Modello finale**

   Ottenete per ciascun canale un modello:

    $$P(s)=\frac{K}{\tau s+1}e^{-sL}$$

   da usare nella fase di taratura.

## 5.4. Step 3 – Implementare il Controllore
Implementare il controllore PID derivando dalla classe [base](../lsi_tcp/base_controller.py)

Potete partire dall'implementazione del [proporzionale](../lsi_tcp/proportional_controller.py)

La descrizione dettagliata del controllore proporzionale si trova [qui](PController.md)

Le linee guida per implementare il codice sono [qui](linee_guida_controllore.md)

Per poter modificare i parametri online aggiungeteli qui:
```python
        # Aggiungi i parametri specifici del controllore
        self._parameters.update({
            "Kp": Kp,
        })
```

Un esempio di script per lanciare il controllore è [qui](../example_proportional.py).
In particolare va modificata `build_controllers` per restituire il VOSTRO
controllore automatico (il `ManualController` per il jog manuale viene
aggiunto da `build_channels`, non va incluso qui — vedi [§3.5](concetti.md#35-utility-di-alto-livello-utilspy) e [§4](esempi.md)):
```python
def build_controllers(sampling_period: float):
    """
    Crea i controllori automatici e li restituisce in un dict
    {"channel1": ..., "channel2": ...}.
    """
    c1 = YourMagicController(
        sampling_period=sampling_period,
        u_min=0.0,
        u_max=100.0,
    )

    c2 = YourMagicController(
        sampling_period=sampling_period,
        u_min=0.0,
        u_max=100.0,
    )

    return {
        "channel1": c1,
        "channel2": c2,
    }
```

## 5.5. Step 3 – Taratura dei due anelli di controllo

1. **Scelta della struttura di controllo**

   - iniziate con lo sviluppo di controllore **PI(D)**, seguendo la
     progressione **P → PI → PID** descritta in
     [`linee_guida_controllore.md`](linee_guida_controllore.md#4bis-procedete-a-piccoli-passi-p--pi--pid);
   - **prima di andare sul banco reale, validate SEMPRE la taratura in
     simulazione**: configurate `FakeTCLabSystem` con i VOSTRI `K1/tau1/L1`
     (o `K2/tau2/L2`) identificati allo Step 2, e usatelo come strumento di
     debug del controllore prima di collegarvi all'hardware. È il workflow
     standard in ambito industriale (si simula prima di toccare l'impianto)
     ed è ripetibile a piacere, a differenza della prova sul banco reale.

2. **Regola di taratura**

   Usate i parametri FOPDT stimati e applicate una regola di taratura
   (Ziegler–Nichols, SIMC, AMIGO, ecc.) per determinare `Kp`, `Ti` (e `Td`
   per un PID). Le formule chiuse delle tre regole sono raccolte in
   [`taratura.md`](taratura.md); il calcolo di `Kp/Ti/Td` a partire
   da `K/τ/L` fatelo in MATLAB.

3. **Implementazione in `example_proportional.py`**

   - impostate i parametri dei due Controllori secondo la taratura;
   - con `SETPOINT_FROM_PROFILE = True` (vedi [§4.2](esempi.md#42-example_proportionalpy--controllo-p-in-anello-chiuso)), il loop usa il profilo
     di setpoint (`example.csv` o un vostro file CSV con la stessa
     struttura, vedi [§3.4](concetti.md#34-profili-di-setpoint-setpointprofile)) invece del setpoint impostato a mano;
   - eseguite il loop in anello chiuso.

4. **Analisi delle prestazioni**

   - valutate tempo di assestamento, sovraelongazione, errore a regime;
   - **ripetete la stessa prova (stesso profilo di setpoint) con 2-3
     tarature diverse** (es. una regola vs un'altra, oppure una delle due
     con `Kp` raddoppiato a mano) e confrontate i risultati: è il modo
     migliore per vedere sul grafico il trade-off velocità di
     risposta/sovraelongazione/robustezza di un PID;
   - discutete l’interazione tra i due canali (es. come un cambiamento di U1 influisce anche su T2).
