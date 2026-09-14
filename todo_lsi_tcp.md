# TODO — Aggiornamento laboratorio `lsi_tcp`

## 1. Controllore / filtro passa-basso

- [ ] Documentare (in `linee_guida_controllore.md` o dove finirà) che il filtro passa-basso va **implementato dentro la classe del controllore** dello studente (es. filtraggio del termine derivativo), non come classe separata.
- [ ] Aggiungere un esempio/commento su come uno stato di filtro (es. `self._d_filt`) convive con gli altri stati persistenti già previsti (integratore, errore precedente) all'interno di `computeControlAction` / `starting`.

## 2. `FakeTCLabSystem`

- [ ] Esporre `K1, tau1, L1, K2, tau2, L2` come parametri modificabili, con lo **stesso pattern già usato in `BaseController`**: `_parameters` + `getListOfParameters()` / `setParameters()` / `getParameters()`.
- [ ] Aggiungere un parametro di costruzione `L_max` (tetto massimo per il ritardo, non modificabile a runtime).
- [ ] Sostituire l'attuale gestione del ritardo con un **buffer a lunghezza fissa**:
  - `deque(maxlen=n_max)` dimensionato su `L_max`, riempito ad ogni passo con `append()`;
  - lettura del valore ritardato per **indicizzazione** (`self._u_buffer[-(n_delay + 1)]`), mai `popleft()`;
  - `n_delay` ricalcolato da `L` corrente ad ogni lettura → `L` modificabile a runtime senza mai ridimensionare il buffer.
- [ ] Validazione in `setParameters`: `L > L_max` → `ValueError`.
- [ ] Inizializzazione del buffer con `u0` costante (non zeri), per evitare un gradino fittizio nei primi `n_max` passi.
- [ ] Commento nel codice sul possibile errore di arrotondamento quando `L` non è multiplo esatto di `log_interval` (accettabile alle frequenze tipiche del TCLab, ma va reso esplicito come scelta consapevole).
- [ ] K e τ liberamente modificabili a runtime; L modificabile a runtime solo entro `L_max`.

## 3. Dashboard (`controllers_dashboard.py`)

### Logica manuale / automatico
- [ ] Un flag manuale/automatico **per canale**, non globale.
- [ ] Due oggetti controllore sempre istanziati per canale (`ManualController` + controllore automatico dello studente); il flag decide solo quale dei due calcola `u` in quell'iterazione — nessun `if` dentro le classi controllore.
- [ ] Al **cambio di modalità**, chiamare `starting()` sul controllore che diventa attivo per il bumpless transfer:
  - auto → manuale: `initial_u` = ultima azione calcolata dal controllore automatico;
  - manuale → auto: `reference` = setpoint appena impostato, `measure` = temperatura corrente.
- [ ] In modalità manuale: `SP1`/`SP2 = None` passati a `dashboard.get_values(...)` per non plottare la curva di setpoint (già supportato dal dashboard attuale).
- [ ] Isolare lo stato condiviso tra thread (modalità corrente, valore manuale/setpoint corrente per canale) in un piccolo oggetto dedicato, non variabili globali sparse.

### Setpoint
- [ ] In modalità automatica il setpoint è impostato **a mano dallo studente** nel dashboard, non più letto da `SetpointProfile`/CSV durante la fase di taratura interattiva.
- [ ] `SetpointProfile`/CSV mantenuto per la **fase di validazione finale** (profilo di riferimento standard per confrontare le tarature).

### Layout
- [ ] Griglia grafici 2×2 in vista principale (invariata).
- [ ] Un solo campo numerico "adattivo" per canale: etichetta e target cambiano con la modalità — "Potenza U [%]" in manuale, "Setpoint [°C]" in automatico.
- [ ] Switch manuale/automatico per canale con `dash_daq.BooleanSwitch`.
- [ ] Bottone **"Modifica parametri"** che apre un `dbc.Offcanvas` (pannello a scomparsa) invece di occupare spazio fisso sopra i grafici.

### Pannello parametri (Offcanvas)
- [ ] Campi generati **dinamicamente** da `controller.getListOfParameters()` (escludendo o separando `sampling_period`, `u_min`, `u_max`), submit → `setParameters({...})`.
- [ ] Componente riutilizzabile: stesso Offcanvas applicabile sia al controllore attivo sia — grazie allo stesso pattern `_parameters` — a `FakeTCLabSystem` per K/τ/L in fase di test in simulato.

### Polish visivo
- [ ] Template Plotly (`plotly_white` o `plotly_dark`).
- [ ] Doppio asse Y nello stesso subplot: temperatura a sinistra, U a destra, per canale.
- [ ] Setpoint tratteggiato, misura a linea continua.
- [ ] `dash-bootstrap-components` per il layout generale (card, grid).
- [ ] Bottone pausa/freeze dell'aggiornamento grafico (senza fermare l'acquisizione).
- [ ] Card con KPI live (errore corrente, parametri attivi, eventuale stima sovraelongazione).
- [ ] Slider (`dcc.Slider`, `updatemode="mouseup"`) come alternativa/aggiunta ai campi numerici per Kp/Ki/Kd.
- [ ] Bottone di export (PNG del grafico via `kaleido`, e/o CSV dei dati correnti) — utile direttamente per la relazione finale.
- [ ] Badge di stato: Simulatore/Hardware reale, Manuale/Automatico.
- [ ] *(bassa priorità)* tema scuro, gauge, sidebar per i controlli.

## 4. Documentazione e struttura del corso

- [ ] Spezzare il README monolitico in `docs/` per fase di laboratorio (setup, identificazione, modello FOPDT, filtro+controllore, taratura, relazione finale).
- [ ] Sezione iniziale esplicita "perché le classi" con l'analogia già presente nel repo (memorie/ritardi unitari di Simulink), resa più visibile.
- [ ] Sezione FAQ / errori comuni (es. dimenticare `super().__init__()`, `KeyError` da `setParameters`, integratore non inizializzato).
- [ ] Micro-esercizio "giocattolo" fuori dal dominio controlli, per introdurre `__init__`/`self`/stato persistente prima di arrivare al controllore vero.
- [ ] Script di debug offline per testare un controllore isolato (sequenza fittizia di reference/measure) prima di collegarlo al loop reale/simulato.
