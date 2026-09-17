# 4. Gli esempi: `example_open_loop.py`, `example_proportional.py`, `example_pid_controller.py`

Gli script nella root del progetto (`../example_open_loop.py`,
`../example_proportional.py`, `../example_pid_controller.py`) sono pensati
come **template** per il vostro codice.

Tutti e tre prevedono:

- un parametro `--fake` da linea di comando (gestito con `argparse`) per
  scegliere fra simulazione (es. `python example_proportional.py --fake`) e
  hardware reale (`python example_proportional.py`, senza il flag);
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
  1. legge il flag `--fake` da linea di comando (`parse_args()`) e crea il
     processo con `build_process(use_fake, real_time_factor=...)`;
  2. crea i controllori automatici con `build_controllers(SAMPLING_PERIOD)`;
  3. chiama `build_channels(controllers, sampling_period=SAMPLING_PERIOD)` →
     `(runtimes, state)`;
  4. chiama `init_channels(runtimes, state, process)`;
  5. lancia `run_closed_loop(process=process, runtimes=runtimes, state=state, ...)`.

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
- ogni prova a scalino deve partire da un valore di temperatura assestato e dovete lasciare che il sistema evolva finché la temperatura si assesta;
- usate i CSV generati (`log_flag=True`) per l’identificazione.

## 4.2. `example_proportional.py` – Controllo P in anello chiuso

Questo file è il **punto di partenza** per il controllo automatico con i modelli FOPDT identificati.

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

- passate ciascun canale in automatico dalla dashboard e impostate il setpoint a
  mano, variando `Kp_T1`/`Kp_T2` (e gli altri parametri del vostro
  controllore) live dal pannello parametri;
- potete usare il codice in modalità `--fake` per simulare il comportamento della scheda. In quel caso impostate i parametri del simulatore cliccando su **Modifica parametri simulatore** impostando i valori di guadagno, costante di tempo e ritardo identificati.

## 4.3. `example_pid_controller.py` – Controllo PI(D) in anello chiuso

Stessa struttura di `example_proportional.py`, ma con
[`PIDController`](../lsi_tcp/pid_controller.py) al posto di `PController`.
La classe `PIDController` va completata da voi (vedi
[`linee_guida_controllore.md`](linee_guida_controllore.md)): finché
`computeControlAction` non è implementato, passare un canale in automatico
solleva `NotImplementedError`.

```python
def build_controllers(sampling_period: float):
    c1 = PIDController(
        sampling_period=sampling_period,
        Kp=Kp_T1,   # da tarare
        Ki=Ki_T1,   # da tarare
        Kd=Kd_T1,   # da tarare
        Tf=Tf_T1,   # da tarare (solo se usate il termine derivativo)
        u_min=0.0,
        u_max=100.0,
    )
    c2 = PIDController(
        sampling_period=sampling_period,
        Kp=Kp_T2,   # da tarare
        Ki=Ki_T2,   # da tarare
        Kd=Kd_T2,   # da tarare
        Tf=Tf_T2,   # da tarare (solo se usate il termine derivativo)
        u_min=0.0,
        u_max=100.0,
    )
    return {"channel1": c1, "channel2": c2}
```

Suggerimento di utilizzo: seguite la progressione **P → PI → PID**
descritta in [§4bis di `linee_guida_controllore.md`](linee_guida_controllore.md#4bis-procedete-a-piccoli-passi-p--pi--pid)
— si può testare il termine integrale (`Ki`) lasciando `Kd=0.0`, e
aggiungere il derivativo solo alla fine.
