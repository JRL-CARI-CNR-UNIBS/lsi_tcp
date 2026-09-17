# Cheatsheet: regole di taratura da modello FOPDT

A partire dal modello identificato

$$P(s)=\frac{K}{\tau s+1}e^{-sL}$$

(guadagno `K`, costante di tempo `τ`, tempo morto `L`) queste sono le formule
chiuse di alcune regole di taratura classiche per un PI o PID. Il calcolo dei
parametri (in MATLAB o a mano) è a vostra scelta; qui trovate solo le
formule, per non doverle cercare sulle slide mentre state lavorando al
codice.

> Promemoria notazione controllore: `Kp` (guadagno proporzionale), `Ti`
> (tempo integrale, con `Ki = Kp / Ti`), `Td` (tempo derivativo, con
> `Kd = Kp * Td`).

## Ziegler–Nichols (reaction curve / anello aperto)

Pensata per una risposta abbastanza aggressiva, con una sovraelongazione
tipicamente non trascurabile.

| Controllore | Kp | Ti | Td |
|---|---|---|---|
| P | $\dfrac{\tau}{K L}$ | — | — |
| PI | $\dfrac{0.9 \tau}{K L}$ | $3.33 L$ | — |
| PID | $\dfrac{1.2\tau}{K L}$ | $2L$ | $0.5 L$ |

## SIMC (Skogestad, IMC-based)

Più conservativa di Ziegler–Nichols, pensata per dare una risposta senza
grosse sovraelongazioni. Richiede di scegliere una costante di tempo di
anello chiuso desiderata `τ_c` (regola pratica: `τ_c = L`, cioè risposta ad
anello chiuso non più veloce del tempo morto del processo).

| Controllore | Kp | Ti |
|---|---|---|
| PI | $\dfrac{1}{K}\cdot\dfrac{\tau}{\tau_c + L}$ | $\min(\tau,\ 4(\tau_c+L))$ |

## AMIGO (Åström–Hägglund)

Compromesso fra aggressività e robustezza, pensata specificamente per
processi FOPDT con rapporto `L/τ` non piccolo (tipico del TCLab).

| Controllore | Kp | Ti | Td |
|---|---|---|---|
| PI | $\dfrac{1}{K}\left(0.15+0.35\dfrac{\tau}{L}-\dfrac{\tau^2}{(\tau+L)^2}\right)$ | $0.35L+\dfrac{13\tau L^2}{\tau^2+12\tau L+7L^2}$ | — |
| PID | $\dfrac{1}{K}\left(0.2+0.45\dfrac{\tau}{L}\right)$ | $\dfrac{0.4L+0.8\tau}{L+0.1\tau}L$ | $\dfrac{0.5L\tau}{0.3L+\tau}$ |

## Come usarle

1. Prendete `K, τ, L` stimati allo Step 2 (identificazione FOPDT).
2. Calcolate `Kp, Ti, (Td)` con una delle tabelle sopra.
3. Impostate i parametri del vostro controllore, tipicamente con
   `Ki = Kp / Ti` (e `Kd = Kp * Td` per un PID) tramite `setParameters(...)`.
4. **Prima di andare sul banco reale, validate la taratura in simulazione**
   con `FakeTCLabSystem` configurato con i VOSTRI `K1/tau1/L1` (o
   `K2/tau2/L2`) identificati — vedi [§5.5 della guida al progetto](guida_progetto.md#55-step-3--taratura-dei-due-anelli-di-controllo).

Confrontare la stessa prova con 2-3 regole diverse (o con un `Kp` tarato
manualmente a partire da una di queste) è il modo più diretto per vedere sul
grafico il trade-off velocità di risposta / sovraelongazione / robustezza:
è una parte richiesta dell'analisi allo Step 3 (§5.5, punto 4).
