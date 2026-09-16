# Richiamo: Anti-windup

L'anti-windup non è un argomento nuovo: lo avete già visto in un corso
precedente. Questa pagina è solo un **richiamo rapido**, utile nel momento in
cui scrivete l'integratore del vostro `PIController`/`PIDController` in
questo laboratorio.

## Il problema

Il termine integrale di un PI(D) accumula l'errore nel tempo:

```python
self.integratore += self.Ki * error * self.sampling_period
```

Se l'azione di controllo `u` va in saturazione (`u_min`/`u_max`, vedi
`_apply_saturation`) per un periodo prolungato — tipico quando il setpoint è
molto lontano dalla misura, es. all'accensione — l'errore resta grande e
**l'integratore continua a crescere anche se l'attuatore non può fare di
meglio**: quando poi l'errore si inverte, il controllore impiega un tempo
lungo a "smaltire" l'integrale accumulato prima di reagire nella direzione
corretta. Questo fenomeno si chiama **windup**.

## Il rimedio più semplice: clamping / back-calculation

Nel laboratorio è sufficiente il rimedio più diretto: **non far crescere
l'integratore se il controllore è già saturo e l'errore lo spingerebbe
ulteriormente in saturazione**.

```python
def computeControlAction(self, reference, measure, feedforward):
    error = reference - measure
    u_fb = self.Kp * error

    u_unsaturated = u_fb + self.integratore + feedforward
    u = self._apply_saturation(u_unsaturated)

    # Aggiorna l'integratore SOLO se non siamo in saturazione, oppure se
    # l'errore spingerebbe u ad allontanarsi dalla saturazione (non a
    # peggiorarla ulteriormente).
    satura = (u != u_unsaturated)
    spinge_oltre = (u_unsaturated > u and error > 0) or (u_unsaturated < u and error < 0)
    if not (satura and spinge_oltre):
        self.integratore += self.Ki * error * self.sampling_period

    return u
```

Nota come questo stato (`self.integratore`) si inizializza in `starting`,
esattamente come gli altri stati persistenti (derivata filtrata, errore
precedente) descritti in `linee_guida_controllore.md`.

## Perché è importante qui

Sul TCLab l'anti-windup si vede facilmente: all'accensione (T molto sotto il
setpoint) l'uscita satura a `u_max` per svariati secondi. Senza anti-windup,
quando la temperatura si avvicina al setpoint il controllore continua a
scaldare oltre il necessario per via dell'integrale accumulato, producendo
una sovraelongazione ben visibile sul grafico — un buon modo per verificare
empiricamente che l'implementazione funzioni.
