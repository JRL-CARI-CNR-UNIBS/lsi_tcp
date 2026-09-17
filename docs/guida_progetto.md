# 5. Guida al progetto degli studenti

Di seguito una **roadmap pratica** che collega il codice del repository ai tre step richiesti.

## 5.1. Preparare il codice

- Aprire _Anaconda Powershell Prompt_
- impostare la cartella di lavoro (mettete il percorso giusto!)
  ```bash
  cd "C:\Users\beschi\Documents\lsa"
  ```
- Attivare l'ambiente
  ```bash
  conda activate lsa
  cd lsi_tcp
  ```

## 5.2. Step 1 – Prova di identificazione (anello aperto)

Script per il controllo manuale:

1. **Preparazione del sistema**
   - scegliete se lavorare in simulazione (`python example_proportional.py --fake`) o con l’hardware reale (`python example_proportional.py`);


2. **Esecuzione della prova**
   - partite con `U1 = U2 = 0%` e lasciate stabilizzare le temperature;
   - applicate un gradino su `U1` (es. da 0% a 40–60%);
   - mantenete il gradino per un tempo sufficiente a raggiungere un nuovo regime;
   - effettuate più prove con punti di partenza e ampiezze di gradino diversi;
   - ripetete per `U2`.

3. **Raccolta dati**
   - assicuratevi che `log_flag=True` in `TCLabSystem` / `FakeTCLabSystem`;
   - al termine otterrete un file CSV `tclab_YYYYMMDDHHMMSS.csv` con colonne `Time, T1, T2, U1, U2`.

## 5.3. Step 2 – Modellazione FOPDT dai CSV

Questo step si svolge in **MATLAB**, non in Python: caricate il CSV
prodotto dallo Step 1 (colonne `Time, T1, T2, U1, U2`) e applicate il metodo
del 10%-90% già visto in un corso precedente (potete anche fare i conti a
mano, senza script, se preferite).

1. **Caricate il CSV** e costruite l'asse dei tempi in secondi (la colonna
   `Time` è un timestamp: convertitelo in secondi rispetto al primo
   campione).

  ```matlab
%% 1. Apertura del file
% readtable legge il CSV e riconosce automaticamente header e tipi di dato
data = readtable('tclab_20260917153728.csv');

% La colonna Time viene letta come datetime (o come stringa, dipende
% dalla versione di MATLAB). Se serve, forziamo la conversione esplicita:
if ~isdatetime(data.Time)
    data.Time = datetime(data.Time, 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
end

%% 2. Convertire il tempo in secondi, con t(1) = 0
% seconds(diff) calcola la differenza tra istanti come durata in secondi
t = seconds(data.Time - data.Time(1));

%% 3. Creare i vettori t, u1, y1, u2, y2
y1 = data.T1;   % temperatura canale 1 (uscita)
y2 = data.T2;   % temperatura canale 2 (uscita)
u1 = data.U1;   % comando canale 1 (ingresso)
u2 = data.U2;   % comando canale 2 (ingresso)

%% 4. Grafico con 4 subplot (2 righe x 2 colonne)
figure;

subplot(2,2,1)
plot(t, y1, 'b', 'LineWidth', 1.2)
xlabel('t [s]'); ylabel('y1 [°C]')
title('Uscita canale 1')
grid on

subplot(2,2,2)
plot(t, y2, 'r', 'LineWidth', 1.2)
xlabel('t [s]'); ylabel('y2 [°C]')
title('Uscita canale 2')
grid on

subplot(2,2,3)
plot(t, u1, 'b', 'LineWidth', 1.2)
xlabel('t [s]'); ylabel('u1 [%]')
title('Ingresso canale 1')
grid on

subplot(2,2,4)
plot(t, u2, 'r', 'LineWidth', 1.2)
xlabel('t [s]'); ylabel('u2 [%]')
title('Ingresso canale 2')
grid on
  ```

2. **Individuate il gradino**

   - verificate dove `U1` (o `U2`) cambia valore;
   - calcolate `U_initial` e `U_final`.

3. **Stima dei parametri FOPDT**

   Per ciascuna temperatura di interesse (es. T1 per un gradino su U1):

   - valore iniziale $T_0$ e valore finale $T_\infty$;
   - guadagno:

     $$K =\frac{T_\infty - T_0}{U_\text{final} - U_\text{initial}}$$
   - $t_{10}$ tempo in cui si raggiunge il 10\% della variazione
   - $t_{90}$ tempo in cui si raggiunge il 90\% della variazione
   - Costante di tempo $\tau=\frac{t_{90}-t_{10}}{2.2}$.
   - tempo morto $L=t_{10}-0.1\tau$


4. **Modello finale**

   Ottenete per ciascun canale un modello:

    $$P(s)=\frac{K}{\tau s+1}e^{-sL}$$

   da usare nella fase di taratura.

## 5.4. Step 3 – Implementare il Controllore
Per Implementare il controllore PID potete partire dall'implementazione del [proporzionale](../lsi_tcp/proportional_controller.py), copiandolo in un nuovo file chiamato pid_controller.py nella cartella  `lsi_tcp`.
Rinominare la classe in **PIDController**

Aggiungrre a [__init__.py](lsi_tcp/__init__.py) la riga:
```python
from .pid_controller import PIDController
```
e aggiungere a `__all__` il nome del nuovo controllore  _"PIDController"_


La descrizione dettagliata del controllore proporzionale si trova [qui](PController.md)

Le linee guida per implementare il codice sono [qui](linee_guida_controllore.md)

Per poter modificare i parametri online aggiungeteli qui:
```python
        # Aggiungi i parametri specifici del controllore
        self._parameters.update({
            "Kp": Kp,
        })
```

Un esempio di script per lanciare il controllore è [qui](../example_proportional.py), createne una copia che lanci il vostro controllore.
In particolare va modificata `build_controllers` per restituire il VOSTRO
controllore automatico (il `ManualController` per il jog manuale viene
aggiunto da `build_channels`, non va incluso qui — vedi [§3.5](concetti.md#35-utility-di-alto-livello-utilspy) e [§4](esempi.md)):
```python
from lsi_tcp import import PIDController
def build_controllers(sampling_period: float):
    """
    Crea i controllori automatici e li restituisce in un dict
    {"channel1": ..., "channel2": ...}.
    """
    c1 = PIDController(
        sampling_period=sampling_period,
        METTETE QUI I VOSTRI PARAMETRI IN INGRESSO
        u_min=0.0,
        u_max=100.0,
    )

    c2 = PIDController(
        sampling_period=sampling_period,
        METTETE QUI I VOSTRI PARAMETRI IN INGRESSO
        u_min=0.0,
        u_max=100.0,
    )

    return {
        "channel1": c1,
        "channel2": c2,
    }
```

## 5.5. Step 3 – Taratura dei due anelli di controllo

1. **Scelta della struttura di controllo**

   - iniziate con lo sviluppo di controllore **PI(D)**, seguendo la
     progressione **P → PI → PID** descritta in
     [`linee_guida_controllore.md`](linee_guida_controllore.md#4bis-procedete-a-piccoli-passi-p--pi--pid);
   - **prima di andare sul banco reale, validate SEMPRE la taratura in
     simulazione**: configurate `FakeTCLabSystem` con i VOSTRI `K1/tau1/L1`
     (o `K2/tau2/L2`) identificati allo Step 2, e usatelo come strumento di
     debug del controllore prima di collegarvi all'hardware. È il workflow
     standard in ambito industriale (si simula prima di toccare l'impianto)
     ed è ripetibile a piacere, a differenza della prova sul banco reale.

2. **Regola di taratura**

   Usate i parametri FOPDT stimati e applicate una regola di taratura
   (Ziegler–Nichols, SIMC, AMIGO, ecc.) per determinare `Kp`, `Ti` (e `Td`
   per un PID). Le formule chiuse delle tre regole sono raccolte in
   [`taratura.md`](taratura.md); il calcolo di `Kp/Ti/Td` a partire
   da `K/τ/L` fatelo in MATLAB.

3. **Implementazione in `example_proportional.py`**

   - impostate i parametri dei due Controllori secondo la taratura;
   - con `SETPOINT_FROM_PROFILE = True` (vedi [§4.2](esempi.md#42-example_proportionalpy--controllo-p-in-anello-chiuso)), il loop usa il profilo
     di setpoint (`example.csv` o un vostro file CSV con la stessa
     struttura, vedi [§3.4](concetti.md#34-profili-di-setpoint-setpointprofile)) invece del setpoint impostato a mano;
   - eseguite il loop in anello chiuso.

4. **Analisi delle prestazioni**

   - valutate tempo di assestamento, sovraelongazione, errore a regime;
   - **ripetete la stessa prova (stesso profilo di setpoint) con 2-3
     tarature diverse** (es. una regola vs un'altra, oppure una delle due
     con `Kp` raddoppiato a mano) e confrontate i risultati: è il modo
     migliore per vedere sul grafico il trade-off velocità di
     risposta/sovraelongazione/robustezza di un PID;
   - discutete l’interazione tra i due canali (es. come un cambiamento di U1 influisce anche su T2).
