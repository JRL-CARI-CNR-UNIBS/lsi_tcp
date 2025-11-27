# lsi_tcp – Laboratorio di Controllo con il Temperature Control Lab

Questo repository fornisce un piccolo framework Python per svolgere 
le esercitazioni di **controllo di processo** con il banco didattico
**Temperature Control Lab (TCLab)**.

L’obiettivo principale è supportare il progetto degli studenti che prevede tre fasi:

1. **Prova di identificazione** del sistema (anello aperto);
2. **Modellazione FOPDT** (First Order Plus Dead Time) a partire dai dati salvati nei CSV per entrambi i sistemi;
3. **Taratura di due anelli di controllo** (tipicamente sulle temperature T1 e T2) e validazione in anello chiuso.

Il pacchetto espone:

- classi per gestire il banco reale (`TCLabSystem`) e un modello simulato (`FakeTCLabSystem`);
- una gerarchia di controllori SISO (`BaseController`, `PController`, `ManualController`);
- una dashboard web (Dash/Plotly) per il monitoraggio e il tuning in tempo reale;
- utilità per gestire profili di setpoint e per orchestrare il loop di controllo.

---

## 1. Installazione

### 1.1. Clonare / installare il pacchetto

Installazione diretta da GitHub (consigliata per gli studenti):

```bash
pip install "git+https://github.com/JRL-CARI-CNR-UNIBS/lsi_tcp.git#master"
```

Oppure clonando il repository:

```bash
git clone https://github.com/JRL-CARI-CNR-UNIBS/lsi_tcp.git
cd lsi_tcp
pip install -e .
```

### 1.2. Dipendenze principali

Il file `requirements.txt` include i pacchetti necessari, fra cui:

- `tclab` – interfaccia al banco hardware;
- `dash`, `plotly`, `dash-html-components`, `dash-core-components`, `dash-table` – per la dashboard web.

Per installarli (se non già inclusi nell’installazione precedente):

```bash
pip install -r requirements.txt
```

> **Nota**: il pacchetto è pensato per Python ≥ 3.11 (vedi `pyproject.toml`).

---

## 2. Struttura del repository

All’interno dello zip / repo troverete indicativamente:

```text
tclab/
├── example_open_loop.py
├── example_proportional.py
├── lsi_tcp/
│   ├── __init__.py
│   ├── tclab_system.py
│   ├── base_controller.py
│   ├── proportional_controller.py
│   ├── manual_controller.py
│   ├── controllers_dashboard.py
│   ├── setpoint_profile.py
│   ├── utils.py
│   └── example.csv
├── pyproject.toml
├── requirements.txt
└── README.md   ← questo file
```

I file più importanti per il progetto sono:

- `example_open_loop.py`  
  Esempio di struttura di script per prove in **anello aperto** (identificazione) e logging su CSV.

- `example_proportional.py`  
  Esempio di struttura di script per controllo **proporzionale** in **anello chiuso**.

- `lsi_tcp/tclab_system.py`  
  Implementa:
  - `BaseTCLabSystem` (classe astratta);
  - `TCLabSystem` (hardware reale);
  - `FakeTCLabSystem` (simulatore).

- `lsi_tcp/base_controller.py`, `proportional_controller.py`, `manual_controller.py`  
  Gerarchia di controllori SISO.

- `lsi_tcp/controllers_dashboard.py`  
  Dashboard Dash per il tuning dei controllori e il monitoraggio dei segnali.

- `lsi_tcp/setpoint_profile.py` + `lsi_tcp/example.csv`  
  Gestione di profili di setpoint letti da CSV (T1 e T2).

- `lsi_tcp/utils.py`  
  Utility di alto livello (`build_process`, `build_setpoint_profile`, `init_controllers`, `run_closed_loop`) usate negli esempi.

---

## 3. Concetti di base del pacchetto

### 3.1. Sistemi TCLab: `TCLabSystem` e `FakeTCLabSystem`

Nel modulo `tclab_system.py` la classe astratta **`BaseTCLabSystem`** definisce il comportamento comune:

- gestione del thread di acquisizione;
- lettura delle variabili di processo;
- scrittura dei comandi agli attuatori;
- logging su file CSV;
- (opzionale) interfaccia con dashboard in tempo reale.

Le implementazioni concrete sono:

- `TCLabSystem(BaseTCLabSystem)`  
  Usa il pacchetto `tclab` e comunica con la board reale.

- `FakeTCLabSystem(BaseTCLabSystem)`  
  Utilizza un **modello matematico** tipo FOPDT per simulare:

  - canale T1 ↔ U1 con parametri (K1, τ1, L1);
  - canale T2 ↔ U2 con parametri (K2, τ2, L2).

  L’equazione (schematica) è:

  $$ 
- \frac{T}{U}=\frac{K}{\tau s+1}e^{-sL}
  $$

  Il tempo di ritardo L è implementato con una coda in funzione del `log_interval`.

#### Costruttori tipici

- Per l’hardware reale:

  ```python
  from lsi_tcp import TCLabSystem

  process = TCLabSystem(
      log_flag=True,
      log_interval=1.0,   # [s] fra due campioni loggati
      plot_period=1.0,    # [s] fra due aggiornamenti dei grafici interni
      time_window=3000,   # [s] finestra storia grafici
  )
  ```

- Per il simulatore:

  ```python
  from lsi_tcp import FakeTCLabSystem

  process = FakeTCLabSystem(
      log_flag=True,
      log_interval=1.0,
      plot_period=1.0,
      time_window=3000,
      realtime_factor=10.0,  # sim 10 volte più veloce del tempo reale
  )
  ```

#### Metodi essenziali

- `readProcessVariables() -> (T1, T2)`  
  Legge le temperature attuali (in °C).

- `writeControlCommands(u1, u2)`  
  Scrive le potenze (0–100%) sui due heater.

- `stop()`  
  Ferma l’acquisizione e chiude il file di log.

#### File di log CSV

Quando `log_flag=True`, viene creato un file tipo:

```text
tclab_YYYYMMDDHHMMSS.csv
```

con intestazione:

```text
Time, T1, T2, U1, U2
```

- **Time**: timestamp *simulato* (derivato da `_get_sim_time()`), scalato da `realtime_factor`;
- **T1, T2**: temperature [°C];
- **U1, U2**: comandi in [%].

Per l’identificazione FOPDT userete proprio questi CSV.

---

### 3.2. Controllori SISO

Nel modulo `base_controller.py` è definita la classe astratta **`BaseController`**, che stabilisce l’interfaccia comune:

- `computeControlAction(reference, measure, feedforward) -> float`
- `starting(reference, measure, initial_u, feedforward) -> None`
- `getListOfParameters() -> List[str]`
- `setParameters(params: Dict[str, Any]) -> None`
- `getParameters() -> Dict[str, Any]`

Inoltre gestisce centralmente:

- saturazione dell’azione di controllo (`u_min`, `u_max`);
- mappatura parametri ↔ attributi della classe.

#### 3.2.1. `PController`

Definito in `proportional_controller.py`:

```python
from lsi_tcp import PController

c = PController(
    sampling_period=1.0,
    Kp=1.0,
    u_min=0.0,
    u_max=100.0,
)
```

Implementa:

- errore: `e = reference - measure`;
- azione: `u = Kp * e + feedforward`;
- saturazione con `u_min`/`u_max`.

I parametri esposti (tipici) sono:

- `Kp` (guadagno proporzionale),
- eventuali limiti `u_min`, `u_max`.

È il controllore da cui partire (in un file diverso nella vostra cartella) per l'implementazione
del controllore PID.

#### 3.2.2. `ManualController`

Definito in `manual_controller.py`, è un controllore puramente manuale:

```python
from lsi_tcp import ManualController

c = ManualController(
    sampling_period=1.0,
    manual_control_action=0.0,  # valore di U [%]
    u_min=0.0,
    u_max=100.0,
)
```

- l’azione di controllo è semplicemente:

  ```python
  u = manual_control_action
  ```

  indipendentemente da `reference`, `measure`, `feedforward`;

- è utile per:
  - prove in **anello aperto** (identificazione);
  - confronti con il comportamento in automatico.

---

### 3.3. Dashboard dei controllori

Nel modulo `controllers_dashboard.py` c’è la classe **`ControllerDashboard`**, che crea una web app Dash/Plotly per:

- visualizzare nel tempo:
  - `T1`, `T2`;
  - `U1`, `U2`;
  - eventuali setpoint `SP1`, `SP2`;
- impostare i parametri dei controllori (`Kp`, `manual_control_action`, limiti, ecc.).

Costruzione tipica:

```python
from lsi_tcp import ControllerDashboard

controllers = {
    "controller1": controller_T1,
    "controller2": controller_T2,
}

dashboard = ControllerDashboard(
    controllers=controllers,
    host="127.0.0.1",
    port=8051,
    debug=True,
    serve_dev_bundles=False,
)

# Avvio in thread separato (tipico negli esempi)
dashboard.start_background()
```

Durante il loop di controllo, si aggiornano i dati del grafico chiamando:

```python
dashboard.get_values(
    T1=measure1,
    T2=measure2,
    U1=u1,
    U2=u2,
    SP1=ref1,   # opzionale
    SP2=ref2,   # opzionale
)
```

> Se `SP1` o `SP2` sono `None`, le relative curve non vengono plottate.

---

### 3.4. Profili di setpoint: `SetpointProfile`

Il modulo `setpoint_profile.py` definisce:

- `SetpointSample` – dataclass con campi `t`, `T1`, `T2`;
- `SetpointProfile` – classe che legge un CSV e fornisce i setpoint nel tempo.

Formato atteso del CSV (esempio in `lsi_tcp/example.csv`):

```text
t,T1,T2
0,25,25
300,40,25
600,50,30
900,50,50
1200,30,30
```

- `t` è il tempo in **secondi** dall’inizio (0 = start esperimento);
- `T1`, `T2` sono i setpoint delle due temperature.

Il profilo è **periodico**: quando `t` supera l’ultimo campione, si riparte da `t = 0`.

Uso tipico:

```python
from lsi_tcp import SetpointProfile

sp = SetpointProfile(csv_path="lsi_tcp/example.csv")

# Nel loop di controllo:
T1_ref, T2_ref = sp.get_setpoints(t_proc)  # t_proc in secondi
```

Il metodo `get_setpoints(t: float) -> Tuple[float, float]`:

- calcola `t_mod = t % t_end` (dove `t_end` è l’ultimo istante nel CSV);
- applica un **Zero-Order Hold (ZOH)**:
  - fra due tempi campionati mantiene l’ultimo valore valido;
- gestisce anche i casi al di fuori dell’intervallo.

---

### 3.5. Utility di alto livello: `utils.py`

Il modulo `utils.py` contiene funzioni pronte per essere usate negli esempi e nell'elaborato:

#### `build_process(use_fake: bool, real_time_factor: float = 10.0)`

```python
from lsi_tcp import build_process

process, real_time_factor = build_process(use_fake=True, real_time_factor=10.0)
```

- se `use_fake=True` → istanzia `FakeTCLabSystem` con il `realtime_factor` richiesto;
- se `use_fake=False` → istanzia `TCLabSystem` e imposta `real_time_factor = 1.0`.

Restituisce:

- `process` – oggetto `TCLabSystem` o `FakeTCLabSystem`;
- `real_time_factor` – fattore effettivo (modificato a 1.0 in caso di hardware reale).

#### `build_setpoint_profile(csv_path: str) -> SetpointProfile`

```python
from lsi_tcp import build_setpoint_profile

setpoint_profile = build_setpoint_profile("lsi_tcp/example.csv")
```

Restituisce un `SetpointProfile` con profilo a gradini.

#### `init_controllers(controllers, process)`

```python
from lsi_tcp import init_controllers

controllers = {
    "controller1": controller_T1,
    "controller2": controller_T2,
}

init_controllers(controllers, process)
```

- legge le misure iniziali (`T1`, `T2`) dal processo;
- chiama `starting(...)` su `controller1` e `controller2` con riferimento iniziale (tipicamente 20°C) e `initial_u=0`.

#### `run_closed_loop(process, controllers, setpoint_profile, real_time_factor, max_duration=None)`

Questa è la funzione che implementa il **loop di controllo completo**:

```python
from lsi_tcp import run_closed_loop

run_closed_loop(
    process=process,
    controllers=controllers,
    setpoint_profile=setpoint_profile,
    real_time_factor=real_time_factor,
    max_duration=5 * 3600.0,  # opzionale
)
```

Al suo interno:

1. Crea una `ControllerDashboard` e la avvia in background.
2. In un ciclo `while True`:
   - calcola `t_proc` (tempo di processo) in secondi usando `real_time_factor`;
   - se `max_duration` è specificata, termina quando `t_proc >= max_duration`;
   - legge i setpoint: `ref1, ref2 = setpoint_profile.get_setpoints(t_proc)`;
   - legge le misure dal processo: `measure1, measure2 = process.readProcessVariables()`;
   - calcola le azioni di controllo:

     ```python
     u1 = controllers["controller1"].computeControlAction(ref1, measure1, feedforward=0.0)
     u2 = controllers["controller2"].computeControlAction(ref2, measure2, feedforward=0.0)
     ```

   - scrive i comandi: `process.writeControlCommands(u1=u1, u2=u2)`;
   - aspetta `SAMPLING_PERIOD / real_time_factor` secondi;
   - aggiorna la dashboard con `dashboard.get_values(...)`.

3. In caso di `KeyboardInterrupt` o alla fine:
   - azzera le uscite;
   - chiude il processo (`stop()`).

---

## 4. Gli esempi: `example_open_loop.py` e `example_proportional.py`

Gli script nella root del progetto sono pensati come **template** per il vostro codice.

Entrambi prevedono:

- una costante `USE_FAKE` per scegliere fra simulazione e hardware reale;
- un periodo di campionamento `SAMPLING_PERIOD`;
- una funzione `build_controllers(sampling_period: float)` che costruisce il dizionario:

  ```python
  controllers = {
      "controller1": <controllore per U1>,
      "controller2": <controllore per U2>,
  }
  ```

- una funzione `main()` che:
  1. crea il processo con `build_process(USE_FAKE, real_time_factor=...)`;
  2. crea i controllori con `build_controllers(SAMPLING_PERIOD)`;
  3. chiama `init_controllers(controllers, process)`;
  4. crea il profilo di setpoint con `build_setpoint_profile("lsi_tcp/example.csv")`;
  5. lancia `run_closed_loop(...)`.

### 4.1. `example_open_loop.py` – Prova in anello aperto

Questo file è il punto di partenza per la **prova di identificazione**.

Suggerimento di utilizzo:

- definite `controller1` come `ManualController`:

  ```python
  def build_controllers(sampling_period: float):
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
      return {"controller1": c1, "controller2": c2}
  ```

- nel corso del test, variate `manual_control_action` (ad esempio tramite dashboard) per applicare uno o più **gradini** su U1 e/o U2;
- lasciate che il sistema evolva finché la temperatura si assesta;
- usate i CSV generati per l’identificazione.

In alternativa, potete implementare direttamente in questo script una sequenza di gradini (senza dashboard) modificando `manual_control_action` nel tempo.

### 4.2. `example_proportional.py` – Controllo P in anello chiuso

Questo file è il punto di partenza per il **controllo automatico** con i modelli FOPDT identificati.

Suggerimento di utilizzo:

```python
def build_controllers(sampling_period: float):
    c1 = PController(
        sampling_period=sampling_period,
        Kp=Kp_T1,       # da tarare
        u_min=0.0,
        u_max=100.0,
    )
    c2 = PController(
        sampling_period=sampling_period,
        Kp=Kp_T2,       # da tarare
        u_min=0.0,
        u_max=100.0,
    )
    return {"controller1": c1, "controller2": c2}
```

Dopo aver identificato i parametri FOPDT di T1 e T2, userete questo script per:

- impostare i setpoint da tracciare (tramite `example.csv` o un vostro file CSV);
- tarare `Kp_T1`, `Kp_T2` usando le regole di taratura discusse a lezione;
- valutare la risposta in anello chiuso (sovraelongazione, tempo di assestamento, errore a regime, ecc.).

---

## 5. Guida al progetto degli studenti

Di seguito una **roadmap pratica** che collega il codice del repository ai tre step richiesti.

### 5.1. Step 1 – Prova di identificazione (anello aperto)

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

### 5.2. Step 2 – Modellazione FOPDT dai CSV

In un notebook Jupyter o in uno script Python separato:

1. **Caricate il CSV**

   ```python
   import pandas as pd

   df = pd.read_csv("tclab_YYYYMMDDHHMMSS.csv")
   ```

2. **Costruite l’asse dei tempi in secondi**

   - la colonna `Time` è un timestamp simulato;
   - potete convertirlo in `datetime` e poi in secondi rispetto al primo campione.

3. **Individuate il gradino**

   - verificate dove `U1` (o `U2`) cambia valore;
   - calcolate `U_initial` e `U_final`.

4. **Stima dei parametri FOPDT**

   Per ciascuna temperatura di interesse (es. T1 per un gradino su U1):

   - valore iniziale \(T_0\) e valore finale \(T_\infty\);
   - guadagno:

     \[
     K = rac{T_\infty - T_0}{U_	ext{final} - U_	ext{initial}}
     \]

   - tempo morto \(	heta\): istante in cui la risposta inizia a deviare in modo significativo;
   - costante di tempo \(	au\): istante in cui la risposta raggiunge il 63% dell’incremento, meno la \(	heta\).

   Potete anche usare metodi numerici (es. `scipy.optimize.curve_fit`) per affinare la stima.

5. **Modello finale**

   Ottenete per ciascun canale un modello:

   \[
   G_i(s) = rac{K_i}{	au_i s + 1} e^{-	heta_i s}, \quad i = 1,2
   \]

   da usare nella fase di taratura.

### 5.3. Step 3 – Taratura dei due anelli di controllo

1. **Scelta della struttura di controllo**

   - iniziate con lo sviluppo di controllore **PI(D)**;
   - testatelo in simulazione
   
2. **Regola di taratura**

   Usate i parametri FOPDT stimati e applicate una regola di taratura (Ziegler–Nichols, SIMC, AMIGO, ecc.) per determinare:

   

3. **Implementazione in `example_proportional.py`**

   - impostate i parametri dei due Controllori secondo la taratura;
   - utilizzate il profilo di setpoint XXXX;
   - eseguite il loop in anello chiuso.

4. **Analisi delle prestazioni**

   - valutate tempo di assestamento, sovraelongazione, errore a regime;
   - confrontate diversi valori dei paramtri;
   - discutete l’interazione tra i due canali (es. come un cambiamento di U1 influisce anche su T2).

---

## 6. Suggerimenti per la relazione finale

Nella relazione di progetto è consigliabile includere:

1. **Descrizione del sistema**
   - schema del TCLab;
   - definizione di input (U1, U2) e output (T1, T2).

2. **Prova di identificazione**
   - descrizione degli esperimenti (gradini applicati, durate, condizioni);
   - grafici di T1, T2, U1, U2 nel tempo.

3. **Modellazione FOPDT**
   - procedura adottata per la stima di K, τ, θ;
   - confronto grafico tra dati sperimentali e modello FOPDT.

4. **Progetto dei controllori**
   - regola di taratura utilizzata;
   - parametri finali dei controllori (per T1 e T2);
   - eventuali limitazioni (saturazione, comportamento ai grandi errori).

5. **Risultati in anello chiuso**
   - risposta a gradino sul setpoint;
   - confronto fra diverse tarature;
   - commenti sulla robustezza (es. cambi di setpoint, disturbi).

6. **Conclusioni e sviluppi futuri**
   - validità e limiti del modello FOPDT;
   - possibili miglioramenti.

---

Questo README è pensato come guida operativa: 
seguite gli esempi `example_open_loop.py` e `example_proportional.py`, 
usate le utility in `lsi_tcp.utils` e completate le parti mancanti 
per costruire il vostro progetto completo di 

identificazione→ modellazione → taratura dei controlli.