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
- una gerarchia di controllori SISO (`BaseController`, `PController`, `PIDController` da completare, `ManualController`);
- una dashboard web (Dash/Plotly) per il monitoraggio e il tuning in tempo reale;
- utilità per gestire profili di setpoint e per orchestrare il loop di controllo.

## Documentazione

La documentazione completa è nella cartella [`docs/`](docs/):

- [1. Installazione](docs/installazione.md)
- [2. Struttura del repository](docs/struttura.md)
- [3. Concetti di base del pacchetto](docs/concetti.md) (`TCLabSystem`/`FakeTCLabSystem`, controllori SISO, dashboard, profili di setpoint, utility)
- [4. Codice esempio: `example_open_loop.py`, `example_proportional.py`, `example_pid_controller.py`](docs/esempi.md)
- [5. Guida allo sviluppo del progetto degli studenti](docs/guida_progetto.md)
- [6. Suggerimenti per la relazione finale](docs/relazione.md)

Approfondimenti sui controllori:

- [`PController.md`](docs/PController.md) – spiegazione dettagliata del controllore proporzionale fornito
- [`linee_guida_controllore.md`](docs/linee_guida_controllore.md) – come scrivere una nuova classe controllore (PI/PID)
- [`Antiwindup.md`](docs/Antiwindup.md) – richiamo sull'anti-windup
- [`taratura.md`](docs/taratura.md) – formule delle regole di taratura (Ziegler–Nichols, SIMC, AMIGO)
