# Linee Guida per Scrivere una Nuova Classe Controllore

Questa guida ti aiuterà a scrivere una nuova classe per un controllore in Python, simile al `PController`. Il controllore che scriverai può essere un tipo diverso (come un `PIController`, `PIDController` o altro) ma seguirà una struttura di base comune.

## 1. Creare la Classe Base

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
- Puoi usare reference, measure, initial_u, e feedforward come parametri per inizializzare lo stato del controllore.

Esempio:

```python
def starting(self, reference: float, measure: float, initial_u: float, feedforward: float) -> None:
    self.integratore = 0.0  # Se hai bisogno di un integratore
    # Altri stati o variabili (quelle che in Simulink sarebbero delle memorie (ritardi unitari)
    return
```

## 4. Implementare il Metodo computeControlAction

Questo è il metodo che calcola l'azione di controllo. In un controllore proporzionale, calcolavi l'errore e moltiplicavi per il guadagno. Per un controllore come un PIController o PIDController, dovrai considerare anche l'integrale e/o la derivata.
Come fare:
- Calcola l'errore come la differenza tra il riferimento (reference) e la misura (measure).
- Se è un PIController o PIDController, aggiorna lo stato integrale o derivativo.
- Combina il feedback e il feedforward per determinare l'uscita di controllo.
- Usa il metodo `_apply_saturation` per applicare la saturazione ai valori di controllo.

Esempio per un PIController:
```python
def computeControlAction(self, reference: float, measure: float, feedforward: float) -> float:
    # Calcolare l'errore
    error = reference - measure

    # Calcolare l'azione di feedback proporzionale
    u_fb = self.Kp * error

    # Calcolare l'azione integrale
    self.integratore += self.Ki * error * self.sampling_period
    
    # Sommare il feedback, l'integrale e il feedforward
    u = u_fb + self.integratore + feedforward

    # Applicare la saturazione
    u = self._apply_saturation(u)
    
    # Gestire antiwindup

    return u
```

## Conclusioni

Scrivere una nuova classe controllore è semplice seguendo questi passaggi:
- Eredita da una classe base.
-   Aggiungi il costruttore per inizializzare i parametri.
-   Implementa il metodo starting per inizializzare lo stato del controllore.
-   Scrivi computeControlAction per calcolare l'azione di controllo.
