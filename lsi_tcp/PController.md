
# README - Controllore Proporzionale in Python

## Panoramica
Questo script Python definisce un **Controllore Proporzionale (PController)**, 
un tipo di sistema di controllo che regola l'uscita in base alla differenza (errore) 
tra il valore di riferimento (setpoint) e il valore misurato. 

### Concetti Chiave:
- **Controllore P (Proporzionale)**: Un sistema di controllo a feedback dove l'azione di 
- controllo è proporzionale all'errore. La formula è:

  $$
  u = K_p \cdot (r - y)
  $$

  Dove:
  - \(u\) è l'uscita di controllo (comando per l'attuatore),
  - \(K_p\) è il guadagno proporzionale scelto dall'utente,
  - \(r\) è il riferimento (setpoint desiderato),
  - \(y\) è l'uscita misurata (variabile di processo).

- **Feedforward**: Un'azione di controllo aggiuntiva che viene applicata direttamente, 
- senza considerare l'errore. È spesso utilizzata nei sistemi in cui si dispone di un
- modello per prevedere l'azione di controllo da applicare in anticipo.

## Componente Principali del Codice

Il codice è scritto come classe.

## Cos'è una Classe in Python?

In Python, **una classe è una "struttura" che definisce un insieme di variabile e funzioni**. 
Un oggetto è una "copia" di quella struttura, con valori specifici per ogni oggetto. 
Immagina la classe come un **progetto**, 
mentre l'oggetto è una **realizzazione** di quel progetto, 
con parametri che possono variare di volta in volta.

Per esempio, nel codice, la classe `PController` definisce come deve comportarsi 
un controllore proporzionale, ma quando crei un oggetto di quella classe
(ad esempio `controller = PController(...)`), stai creando un controllore 
che segue le regole della classe, ma con valori specifici come il guadagno $K_p$
e i limiti di saturazione.

### Cos'è una Classe Astratta?
Una **classe astratta** è una classe che non può essere usata direttamente per creare oggetti. 
È come un modello (un prototipo) che definisce alcune regole generali per altre classi. 
Le classi che ereditano da una classe astratta devono implementare alcune funzioni definite da essa. 
In altre parole, una classe astratta impone una struttura, ma lascia che le classi derivate 
decidano come riempire i dettagli.

Nel nostro caso, la classe `BaseController` è una classe astratta. 
Non può essere usata direttamente per creare oggetti. 
Invece, le classi come `PController` la utilizzano per costruire controllori specifici, 
implementando i metodi che `BaseController` definisce.

### Cos'è un Oggetto?
In Python, **un oggetto è una realizzazione di una classe**. 
Quando crei un oggetto, stai creando una "copia" di una classe con valori specifici. 
Per esempio, quando scrivi:

```python
controller = PController(sampling_period=0.1, Kp=2.0, u_min=0, u_max=10)
```

Stai creando un oggetto chiamato `controller` basato sulla classe `PController`, 
con i parametri che hai specificato. Ogni oggetto può avere valori diversi, 
ma tutti seguono le stesse regole stabilite dalla classe.

### Cos'è self?

In Python, self è una parola chiave che rappresenta l'oggetto stesso.

Ogni volta che si definisce un metodo in una classe, self è il primo parametro di quel metodo
e viene utilizzato per accedere agli attributi e ai metodi dell'oggetto stesso.
In altre parole, self permette a un oggetto di "conoscere" se stesso e 
di operare sui suoi valori interni.

Per accedere alle variabili interne (chiamate anche membri) di un oggetto, 
devi usare la sintassi self.variabile. Ad esempio, per accedere a un attributo Kp, scriverai `self.Kp`.

**Nota importante**: Quando **definisci** un metodo (ad esempio def metodo(self)), 
devi includere self come primo parametro. 
Tuttavia, quando **chiami** il metodo, non devi passare self. 
Python lo fa automaticamente quando il metodo viene invocato su un oggetto.


### 1. **Classe BaseController**
La classe `BaseController` è una classe **astratta** che definisce la struttura di base 
per tutti i controllori. **Una classe astratta** è una classe che non può essere utilizzata 
direttamente per creare oggetti, ma serve come "modello" per altre classi. Le classi che ereditano da essa devono implementare i metodi definiti nella classe astratta. In pratica, serve per garantire che tutte le classi derivate abbiano alcune funzioni di base. 

- `sampling_period`: Il tempo tra un aggiornamento del controllo e il successivo (in secondi).
- `u_min` e `u_max`: I limiti per l'uscita di controllo, per evitare che i valori diventino troppo grandi o troppo piccoli (saturazione).
- Metodi come `computeControlAction`, `starting`, e helper per la saturazione (`_apply_saturation`).

### 2. **Classe del Controllore Proporzionale (`PController`)**
La classe `PController` eredita da `BaseController` e implementa la logica del controllore P. Include:
- **Costruttore (`__init__`)**: Inizializza il controllore con il periodo di campionamento, il guadagno proporzionale \(K_p\), e i limiti per l'uscita (`u_min`, `u_max`).
- **Metodo di Avvio (`starting`)**: Inizializza il controllore. Questo metodo non deve fare molto per un controllore proporzionale, ma può essere utilizzato per personalizzazioni future.
- **Calcolo dell'Azione di Controllo (`computeControlAction`)**: Calcola l'uscita di controllo in base all'errore tra il riferimento e la misura, poi applica eventuale azione feedforward e la saturazione.

### 3. **Metodi di Supporto**
- **Saturazione**: Il metodo `_apply_saturation` assicura che l'uscita di controllo rimanga all'interno dei limiti specificati (`u_min` e `u_max`).


## Transizione da MATLAB a Python

Se sei abituato a lavorare in MATLAB, ecco alcune delle principali differenze:
- **Classi**: Le classi in Python sono utilizzate per raggruppare comportamenti e stati. In MATLAB, questa struttura esiste, ma è spesso utilizzata tramite oggetti e funzioni separate.
- **Funzioni (Metodi)**: In Python, le funzioni all'interno di una classe sono chiamate "metodi" e sono definite utilizzando la parola chiave `def`.
- **Creazione di Oggetti**: In Python, si creano gli oggetti tramite il nome della classe (ad esempio `controller = PController(...)`).



### Commento del Codice riga per riga
Il [codice](PController.py) del propozionale è composto da:


```python
from lsi_tcp import BaseController
```
- Importa la classe `BaseController` dal modulo `lsi_tcp`. `BaseController` è la classe di base da cui eredita il `PController`.


```python
class PController(BaseController):
```
- Definisce la classe `PController` che eredita dalla classe `BaseController`. Questo significa che `PController` avrà tutte le funzionalità di `BaseController` e potrà aggiungere o modificare metodi specifici.


```python
    def __init__(
        self,
        sampling_period: float,
        Kp: float = 1.0,
        u_min: float = 0.0,
        u_max: float = 100.0,
    ) -> None:
```
- Il costruttore (`__init__`) della classe `PController`. Questo metodo viene chiamato quando crei un nuovo oggetto della classe `PController`. Prende i seguenti parametri:
  - `sampling_period`: il periodo di campionamento per il controllore.
  - `Kp`: il guadagno proporzionale.
  - `u_min` e `u_max`: i limiti per l'uscita di controllo.


```python
        super().__init__(sampling_period=sampling_period, u_min=u_min, u_max=u_max)
```
- Chiamata al costruttore della classe base (`BaseController`). Questo permette a `PController` di inizializzare la classe base con i parametri di campionamento e i limiti di saturazione.


```python
        self._parameters.update({
            "Kp": Kp,
        })
```
- Aggiunge il parametro `Kp` (guadagno proporzionale) al dizionario dei parametri del controllore. Questo dizionario è usato per memorizzare i parametri configurabili del controllore in modo che l'interfaccia grafica li legga.


```python
        self.Kp = Kp
```
- Imposta il valore di `Kp` come attributo dell'oggetto. Questo permette di accedere direttamente a `Kp` come `self.Kp`.

```python
    def starting(
        self,
        reference: float,
        measure: float,
        initial_u: float,
        feedforward: float
    ) -> None:
```
- Il metodo `starting` viene utilizzato per inizializzare il controllore. In questo caso, non sono necessari stati interni da inizializzare per un controllore proporzionale, quindi la funzione è vuota. Potresti usarla per altre inizializzazioni o controlli.


```python
        return
```
- Poiché non è necessario fare nulla nell'inizializzazione del controllore proporzionale, il metodo `starting` termina senza fare nulla.


```python
    def computeControlAction(
        self,
        reference: float,
        measure: float,
        feedforward: float
    ) -> float:
```
- Il metodo `computeControlAction` calcola l'azione di controllo. Riceve i seguenti parametri:
  - `reference`: il valore di riferimento (setpoint).
  - `measure`: il valore misurato (uscita).
  - `feedforward`: il contributo di controllo in anticipo.


```python
        error = reference - measure
```
- Calcola l'errore, che è la differenza tra il riferimento (`reference`) e la misura (`measure`).


```python
        u_fb = self.Kp * error
```
- Calcola l'azione di feedback proporzionale, moltiplicando l'errore per il guadagno `Kp`


```python
        u = u_fb + feedforward
```
- Somma l'azione di feedback proporzionale (`u_fb`) e l'azione feedforward (`feedforward`).


```python
        u = self._apply_saturation(u)
```
- Applica la saturazione all'azione di controllo `u` utilizzando il metodo `_apply_saturation` della classe base. Questo metodo assicura che l'uscita di controllo rimanga entro i limiti `u_min` e `u_max`


```python
        return u
```
- Restituisce l'azione di controllo calcolata e saturata.