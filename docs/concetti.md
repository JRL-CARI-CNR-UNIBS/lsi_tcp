# 3. Concetti di base del pacchetto

## 3.1. Sistemi TCLab: `TCLabSystem` e `FakeTCLabSystem`

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

  L’equazione è:

  $$
\frac{T}{U}=\frac{K}{\tau s+1}e^{-sL}
  $$

  Il tempo di ritardo L è implementato con una coda in funzione del `log_interval`.

### Costruttori tipici

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

### Metodi essenziali

- `readProcessVariables() -> (T1, T2)`
  Legge le temperature attuali (in °C).

- `writeControlCommands(u1, u2)`
  Scrive le potenze (0–100%) sui due heater.

- `stop()`
  Ferma l’acquisizione e chiude il file di log.

### File di log CSV

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

## 3.2. Controllori SISO

Nel modulo `base_controller.py` è definita la classe astratta **`BaseController`**, che stabilisce l’interfaccia comune:

- `computeControlAction(reference, measure) -> float`
- `starting(reference, measure, initial_u) -> None`
- `getListOfParameters() -> List[str]`
- `setParameters(params: Dict[str, Any]) -> None`
- `getParameters() -> Dict[str, Any]`

Inoltre gestisce centralmente:

- saturazione dell’azione di controllo (`u_min`, `u_max`);
- mappatura parametri ↔ attributi della classe.

### 3.2.1. `PController`

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
- azione: `u = Kp * e`;
- saturazione con `u_min`/`u_max`.

I parametri esposti (tipici) sono:

- `Kp` (guadagno proporzionale),
- eventuali limiti `u_min`, `u_max`.

È il controllore da cui partire per l'implementazione del controllore PID
(vedi sotto). Descrizione dettagliata: [`PController.md`](PController.md).

### 3.2.2. `PIDController` (da completare)

Scheletro definito in `pid_controller.py`, già importato in
`lsi_tcp/__init__.py`:

```python
from lsi_tcp import PIDController

c = PIDController(
    sampling_period=1.0,
    # METTI QUI I PARAMETRI
    u_min=0.0,
    u_max=100.0,
)
```

Il costruttore è da completare con i parametri del controllore necessari; `starting` e
`computeControlAction` contengono solo commenti `# inserisci il tuo codice
qui` e vanno implementati da voi seguendo
[`linee_guida_controllore.md`](linee_guida_controllore.md) — finché
`computeControlAction` non è completato, chiamarlo solleva
`NotImplementedError`.

### 3.2.3. `ManualController`

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

  indipendentemente da `reference`, `measure`;

- è utile per:
  - prove in **anello aperto** (identificazione);
  - confronti con il comportamento in automatico;
  - il jog manuale dalla dashboard: **ogni canale ha sempre, contemporaneamente,
    un `ManualController` e il vostro controllore automatico** (vedi §3.3 e
    §3.5); un flag per canale decide quale dei due calcola `u` in un dato
    istante, con bumpless transfer al cambio di modalità.

---

## 3.3. Dashboard dei controllori

Nel modulo `controllers_dashboard.py` c’è la classe **`ControllerDashboard`**, che crea una web app Dash/Plotly per:

- visualizzare nel tempo `T1`, `T2`, `U1`, `U2` ed eventuali setpoint `SP1`, `SP2`;
- passare da manuale ad automatico (e viceversa) **per canale**, con uno switch;
- un campo numerico "adattivo" per canale: in manuale imposta la potenza
  `U` [%], in automatico il setpoint [°C];
- impostare i parametri del controllore attivo (`Kp`, `Ki`, ... o
  `manual_control_action`) e, in simulazione, i parametri del modello
  (`K1/tau1/L1`, `K2/tau2/L2`) direttamente dal browser, senza fermare il loop.

Per ogni canale la dashboard **non parla direttamente con le classi
controllore**: legge/scrive uno stato condiviso in un `DashboardState` e
mostra i parametri del controllore attivo esposto da un `ChannelRuntime`
(che, nel loop di controllo, decide quale dei due controllori del canale —
`ManualController` o il vostro automatico — calcola `u`).

Non dovete costruire `ControllerDashboard` a mano: ci pensa
`utils.run_closed_loop` a partire da quanto preparato con
`utils.build_channels`/`init_channels` (§3.5). Costruzione tipica (uguale a
quella usata internamente da `run_closed_loop`):

```python
from lsi_tcp import ControllerDashboard

dashboard = ControllerDashboard(
    runtimes,             # dict {"channel1": ChannelRuntime, "channel2": ChannelRuntime}
    state,                # DashboardState condiviso
    system=process,       # FakeTCLabSystem o TCLabSystem, opzionale
    is_simulator=True,    # solo per il badge di stato
    setpoint_from_profile=False,  # True per far seguire il setpoint da un SetpointProfile (§3.4) invece che dalla dashboard
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

> Se `SP1` o `SP2` sono `None` (canale in manuale), le relative curve non vengono plottate.

---

## 3.4. Profili di setpoint: `SetpointProfile`

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

## 3.5. Utility di alto livello: `utils.py`

Il modulo `utils.py` contiene funzioni pronte per essere usate negli esempi e nell'elaborato:

### `build_process(use_fake: bool, real_time_factor: float = 10.0)`

```python
from lsi_tcp import build_process

process, real_time_factor = build_process(use_fake=True, real_time_factor=10.0)
```

- se `use_fake=True` → istanzia `FakeTCLabSystem` con il `realtime_factor` richiesto;
- se `use_fake=False` → istanzia `TCLabSystem` e imposta `real_time_factor = 1.0`.

Restituisce:

- `process` – oggetto `TCLabSystem` o `FakeTCLabSystem`;
- `real_time_factor` – fattore effettivo (modificato a 1.0 in caso di hardware reale).

### `build_setpoint_profile(csv_path: str) -> SetpointProfile`

```python
from lsi_tcp import build_setpoint_profile

setpoint_profile = build_setpoint_profile("lsi_tcp/example.csv")
```

Restituisce un `SetpointProfile` con profilo a gradini.

### `build_channels(auto_controllers, sampling_period, u_min=0.0, u_max=100.0)`

```python
from lsi_tcp import build_channels

auto_controllers = {
    "channel1": controller_T1,   # il VOSTRO controllore (PController, PID, ...)
    "channel2": controller_T2,
}

runtimes, state = build_channels(auto_controllers, sampling_period=SAMPLING_PERIOD)
```

- crea, per ciascun canale, un `ManualController` **sempre istanziato** (per
  il jog manuale dalla dashboard) e lo affianca al vostro controllore
  automatico in un `ChannelRuntime`;
- crea un `DashboardState` condiviso da tutti i canali;
- ritorna `(runtimes, state)`, entrambi da passare a `init_channels` e `run_closed_loop`.

### `init_channels(runtimes, state, process, initial_reference=20.0)`

```python
from lsi_tcp import init_channels

init_channels(runtimes, state, process)
```

- legge le misure iniziali (`T1`, `T2`) dal processo;
- chiama `starting(...)` su **entrambi** i controllori (manuale e
  automatico) di ciascun canale, con riferimento iniziale (default 20°C) e
  `initial_u=0`;
- **va chiamata prima di `run_closed_loop`**: senza, lo stato interno del
  vostro controllore (es. l'integratore di un PI) non verrebbe mai
  inizializzato finché non avviene un primo cambio di modalità dalla
  dashboard.

### `run_closed_loop(process, runtimes, state, real_time_factor, setpoint_profile=None, setpoint_from_profile=False, is_simulator=True, max_duration=None, sampling_period=SAMPLING_PERIOD)`

Questa è la funzione che implementa il **loop di controllo completo**:

```python
from lsi_tcp import run_closed_loop

run_closed_loop(
    process=process,
    runtimes=runtimes,
    state=state,
    real_time_factor=real_time_factor,
    max_duration=5 * 3600.0,  # opzionale
)
```

Al suo interno:

1. Crea una `ControllerDashboard(runtimes, state, system=process, ...)` e la avvia in background.
2. In un ciclo `while True`:
   - calcola `t_proc` (tempo di processo) in secondi usando `real_time_factor`;
   - se `max_duration` è specificata, termina quando `t_proc >= max_duration`;
   - se `setpoint_from_profile=True`, sovrascrive il setpoint condiviso con
     `setpoint_profile.get_setpoints(t_proc)`; altrimenti il setpoint resta
     quello impostato a mano dallo studente nella dashboard (workflow
     seguito negli esempi, §4);
   - legge le misure dal processo: `measure1, measure2 = process.readProcessVariables()`;
   - lascia decidere a ciascun `ChannelRuntime` quale dei suoi due
     controllori calcola `u` (gestendo da solo il bumpless transfer):

     ```python
     u1, sp1 = runtimes["channel1"].step(measure=measure1)
     u2, sp2 = runtimes["channel2"].step(measure=measure2)
     ```

   - scrive i comandi: `process.writeControlCommands(u1=u1, u2=u2)`;
   - aspetta `sampling_period / real_time_factor` secondi;
   - aggiorna la dashboard con `dashboard.get_values(...)` (`sp1`/`sp2` sono
     `None` per i canali in manuale, così la curva SP non viene plottata).

3. In caso di `KeyboardInterrupt` o alla fine:
   - azzera le uscite;
   - chiude il processo (`stop()`).
