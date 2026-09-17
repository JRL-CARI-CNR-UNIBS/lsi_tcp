# Linee Guida per Scrivere una Nuova Classe Controllore

Questa guida ti aiuterà a scrivere una nuova classe per un controllore in Python, simile al `PController`. Il controllore che scriverai può essere un tipo diverso (come un `PIController`, `PIDController` o altro) ma seguirà una struttura di base comune.

> Per il PID trovate già lo scheletro pronto in
> [`lsi_tcp/pid_controller.py`](../lsi_tcp/pid_controller.py): costruttore
> già scritto (parametri `Kp`, `Ki`, `Kd`, `Tf`), `starting` e
> `computeControlAction` da completare (cercate i commenti `# inserisci il
> tuo codice qui`). Gli esempi di questa pagina vi guidano nel riempirli.

## 1. Modificare la Classe PIDController

**Nota**: potete usare la classe definita in **pid_controller.py** e saltare i punti 1 e 2.

Se la tua classe controllore eredita da una classe base, come `BaseController`, 
devi prima capire come funziona la classe base. 
Ad esempio, `BaseController` gestisce il periodo di campionamento, 
i limiti di saturazione e definisce i metodi che tutti i controllori devono avere.

### Come creare una nuova classe controllore:
- La tua nuova classe deve **ereditare** da `BaseController` (o una classe simile) per riutilizzare la logica comune.
- Devi **implementare** i metodi che la classe base richiede (come `computeControlAction` e `starting`).

### Esempio:
```python
class NuovoControllore(BaseController):
    """
    Questa è una classe base per un nuovo controllore, ad esempio un PIController.
    """
```

## 2. Aggiungere un Costruttore (`__init__`)

Il costruttore serve per inizializzare i parametri del controllore. Se la classe base ha un costruttore che gestisce alcuni parametri, usa `super().__init__()` per inizializzarli.
Come fare:
- Inizializza la classe base con `super().__init__(...)` per passare i parametri comuni come il periodo di campionamento, i limiti di saturazione, ecc.
- Aggiungi i parametri specifici del tuo controllore (come Kp, Ki, Kd se stai creando un controllore PID).

Esempio:
```python
def __init__(self, sampling_period: float, Kp: float = 1.0, Ki: float = 0.0, u_min: float = 0.0, u_max: float = 100.0) -> None:
    super().__init__(sampling_period=sampling_period, u_min=u_min, u_max=u_max)
    self._parameters.update({
        "Kp": Kp,
        "Ki": Ki
    })
    self.Kp = Kp
    self.Ki = Ki
```

## 3. Implementare il Metodo starting

Il metodo starting viene chiamato per inizializzare il controllore. In un controllore come il PController, non c'è nulla da inizializzare, ma potresti dover inizializzare uno stato interno (ad esempio, un integratore in un PIController o PIDController).
Come fare:
- Se il controllore ha variabili interne (ad esempio, il termine integratore in un PIController o PIDController), devi inizializzarle nel metodo starting.
- Puoi usare reference, measure e initial_u come parametri per inizializzare lo stato del controllore.

Esempio:

```python
def starting(self, reference: float, measure: float, initial_u: float) -> None:
    self.integratore = 0.0  # Se hai bisogno di un integratore
    # Altri stati o variabili (quelle che in Simulink sarebbero delle memorie (ritardi unitari)
    return
```

## 4. Implementare il Metodo computeControlAction

Questo è il metodo che calcola l'azione di controllo. In un controllore proporzionale, calcolavi l'errore e moltiplicavi per il guadagno. Per un controllore come un PIController o PIDController, dovrai considerare anche l'integrale e/o la derivata.
Come fare:
- Calcola l'errore come la differenza tra il riferimento (reference) e la misura (measure).
- Se è un PIController o PIDController, aggiorna lo stato integrale o derivativo.
- Usa il metodo `_apply_saturation` per applicare la saturazione ai valori di controllo.

Esempio per un PIController:
```python
def computeControlAction(self, reference: float, measure: float) -> float:
    # Calcolare l'errore
    error = reference - measure

    # Calcolare l'azione di feedback proporzionale
    u_fb = self.Kp * error

    # Calcolare l'azione integrale
    self.integratore += self.Ki * error * self.sampling_period
    
    # Sommare il feedback e l'integrale
    u = u_fb + self.integratore

    # Applicare la saturazione
    u = self._apply_saturation(u)
    
    # Gestire antiwindup (richiamo, già visto in un corso precedente: vedi Antiwindup.md)

    return u
```

> **Anti-windup**: lo avete già visto in un corso precedente. Trovate un
> richiamo rapido, con lo schema di clamping applicato a questo stesso
> pattern di codice, in [`Antiwindup.md`](Antiwindup.md).

## 4bis. Procedete a piccoli passi: P → PI → PID

Non scrivete un PID completo in un colpo solo: è più facile individuare un
bug in un passo alla volta.

1. Partite dal `PController` già fornito (§3 in [`PController.md`](PController.md)).
2. Estendete a **PI** aggiungendo solo il termine integrale (§4 sopra) e
   osservate l'effetto sull'errore a regime rispetto al solo P.
3. Aggiungete l'**anti-windup** (vedi sopra) e verificate che la
   sovraelongazione dopo un tratto in saturazione si riduca.
4. Solo alla fine aggiungete il termine **derivativo** (filtrato, §5 sotto)
   per ottenere il PID completo.

Ogni passo è testabile da solo prima di scrivere quello successivo, invece
di dover capire da dove arriva un bug in un PID scritto tutto insieme.

## 5. Il filtro passa-basso (es. sul termine derivativo)

Se il tuo controllore usa un termine derivativo (PID), sai già che la derivata pura amplifica il rumore di misura. Il rimedio classico è **filtrare** il termine derivativo con un filtro passa-basso del primo ordine.

**Importante**: il filtro NON va scritto come una classe separata. Va
implementato **dentro la classe del controllore**, esattamente come fai per
l'integratore: è un altro stato persistente, gestito con gli stessi strumenti
(un attributo `self._...`, inizializzato in `starting` e aggiornato in
`computeControlAction`).



## Conclusioni

Scrivere una nuova classe controllore è semplice seguendo questi passaggi:
- Eredita da una classe base.
- Aggiungi il costruttore per inizializzare i parametri.
- Implementa il metodo starting per inizializzare lo stato del controllore.
- Scrivi computeControlAction per calcolare l'azione di controllo.

## Checklist di autovalutazione

Prima di considerare il controllore pronto, verificate che:

- [ ] la classe eredita da `BaseController`;
- [ ] sono implementati sia `starting` che `computeControlAction`;
- [ ] tutti i parametri specifici (`Kp`, `Ki`, `Kd`, `Tf`, ...) sono stati
      aggiunti a `self._parameters` con `.update({...})` **e** impostati
      come attributi (`self.Kp = Kp`, ecc.), così da comparire nella
      dashboard e poter essere modificati con `setParameters(...)`;
- [ ] la saturazione usa `self._apply_saturation(u)` invece di essere
      reimplementata a mano;
- [ ] ogni stato persistente (integratore, derivata filtrata, errore
      precedente, ...) è inizializzato in `starting` e aggiornato in
      `computeControlAction`, non dichiarato solo nel costruttore;
- [ ] l'anti-windup è gestito (vedi [`Antiwindup.md`](Antiwindup.md)) se il
      controllore ha un termine integrale.
