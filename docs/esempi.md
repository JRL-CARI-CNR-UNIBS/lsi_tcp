# 4. Gli esempi: `example_open_loop.py` e `example_proportional.py`

Gli script nella root del progetto (`../example_open_loop.py`,
`../example_proportional.py`) sono pensati come **template** per il vostro codice.

Entrambi prevedono:

- una costante `USE_FAKE` per scegliere fra simulazione e hardware reale;
- un periodo di campionamento `SAMPLING_PERIOD`;
- una funzione `build_controllers(sampling_period: float)` che costruisce il
  dizionario dei **controllori automatici** (uno per canale — il
  `ManualController` per il jog manuale viene aggiunto automaticamente da
  `build_channels`, non va incluso qui):

  ```python
  controllers = {
      "channel1": <controllore automatico per U1/T1>,
      "channel2": <controllore automatico per U2/T2>,
  }
  ```

- una funzione `main()` che:
  1. crea il processo con `build_process(USE_FAKE, real_time_factor=...)`;
  2. crea i controllori automatici con `build_controllers(SAMPLING_PERIOD)`;
  3. chiama `build_channels(controllers, sampling_period=SAMPLING_PERIOD)` →
     `(runtimes, state)`;
  4. chiama `init_channels(runtimes, state, process)`;
  5. (solo in fase di validazione finale, §5.5) crea il profilo di setpoint
     con `build_setpoint_profile("lsi_tcp/example.csv")`;
  6. lancia `run_closed_loop(process=process, runtimes=runtimes, state=state, ...)`.

## 4.1. `example_open_loop.py` – Prova in anello aperto

Questo file è il punto di partenza per la **prova di identificazione**.
Nessun controllore automatico esiste ancora: entrambi i canali usano un
`ManualController` anche come "controllore automatico" (di fatto restano
sempre manuali finché non collegate il vostro):

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
    return {"channel1": c1, "channel2": c2}
```

Suggerimento di utilizzo:

- nel corso del test, variate la potenza `U` di ciascun canale (campo
  numerico "adattivo" nella dashboard, in modalità manuale) per applicare
  uno o più **gradini** su U1 e/o U2;
- lasciate che il sistema evolva finché la temperatura si assesta;
- usate i CSV generati (`log_flag=True`) per l’identificazione.

## 4.2. `example_proportional.py` – Controllo P in anello chiuso

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
    return {"channel1": c1, "channel2": c2}
```

Dopo aver identificato i parametri FOPDT di T1 e T2, userete questo script per:

- **taratura interattiva**: `SETPOINT_FROM_PROFILE = False` (default) — passate
  ciascun canale in automatico dalla dashboard e impostate il setpoint a
  mano, variando `Kp_T1`/`Kp_T2` (o gli altri parametri del vostro
  controllore) live dal pannello parametri;
- **validazione finale**: `SETPOINT_FROM_PROFILE = True` — il setpoint segue
  `example.csv` (o un vostro file CSV con la stessa struttura), il campo
  numerico si disabilita e valutate la risposta in anello chiuso
  (sovraelongazione, tempo di assestamento, errore a regime, ecc.).
