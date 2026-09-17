# 2. Struttura del repository

All’interno dello zip / repo troverete indicativamente:

```text
tclab/
├── example_open_loop.py
├── example_proportional.py
├── example_pid_controller.py
├── lsi_tcp/
│   ├── __init__.py
│   ├── tclab_system.py
│   ├── base_controller.py
│   ├── proportional_controller.py
│   ├── pid_controller.py
│   ├── manual_controller.py
│   ├── channel_runtime.py
│   ├── dashboard_state.py
│   ├── controllers_dashboard.py
│   ├── setpoint_profile.py
│   ├── utils.py
│   └── example.csv
├── docs/
│   ├── taratura.md
│   ├── Antiwindup.md
│   └── ...
├── pyproject.toml
├── requirements.txt
└── README.md   ← indice generale
```

I file più importanti per il progetto sono:

- `example_open_loop.py`
  Esempio di struttura di script per la **prova di identificazione** in **anello aperto**.

- `example_proportional.py`
  Esempio di struttura di script per controllo **proporzionale** in **anello chiuso**.

- `example_pid_controller.py`
  Come `example_proportional.py`, ma con `PIDController` al posto di `PController`.

- `lsi_tcp/tclab_system.py`
  Implementa:
  - `BaseTCLabSystem` (classe astratta);
  - `TCLabSystem` (hardware reale);
  - `FakeTCLabSystem` (simulatore).

- `lsi_tcp/base_controller.py`, `proportional_controller.py`, `manual_controller.py`
  Gerarchia di controllori SISO.

- `lsi_tcp/pid_controller.py`
  Scheletro di `PIDController` da completare (vedi
  [`linee_guida_controllore.md`](linee_guida_controllore.md)): costruttore
  già scritto, `starting`/`computeControlAction` da implementare.

- `lsi_tcp/channel_runtime.py` + `lsi_tcp/dashboard_state.py`
  Coordinano, per ciascun canale, i due controllori sempre istanziati
  (`ManualController` + il vostro controllore automatico) e lo stato
  condiviso con la dashboard (modalità manuale/automatico, potenza manuale,
  setpoint). Non richiedono modifiche da parte vostra: sono usati
  internamente da `utils.build_channels`.

- `lsi_tcp/controllers_dashboard.py`
  Dashboard Dash per il tuning dei controllori e il monitoraggio dei segnali.

- `lsi_tcp/setpoint_profile.py` + `lsi_tcp/example.csv`
  Gestione di profili di setpoint letti da CSV (T1 e T2).

- `lsi_tcp/utils.py`
  Utility di alto livello (`build_process`, `build_setpoint_profile`,
  `build_channels`, `init_channels`, `run_closed_loop`) usate negli esempi.
