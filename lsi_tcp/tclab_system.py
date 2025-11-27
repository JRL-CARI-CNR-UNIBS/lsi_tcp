
# Crea il grafico con 2 righe
fig = make_subplots(
    rows=4, cols=1,  # 2 righe e 1 colonna
    shared_xaxes=True,  # Condividi l'asse X tra i grafici
    vertical_spacing=0.01,  # Spaziatura tra i grafici
    subplot_titles=('Temperature (T1)', 'Temperature (T2)', 'Control Command (U1)', 'Control Command (U2)')
)

# Aggiungi i dati per T1 e T2 alla prima riga
fig.add_trace(go.Scatter(x=time_data, y=t1_data, mode='lines', name='T1'), row=1, col=1)
fig.add_trace(go.Scatter(x=time_data, y=t2_data, mode='lines', name='T2'), row=3, col=1)

# Aggiungi i dati per U1 e U2 alla seconda riga
fig.add_trace(go.Scatter(x=time_data, y=u1_data, mode='lines', name='U1'), row=2, col=1)
fig.add_trace(go.Scatter(x=time_data, y=u2_data, mode='lines', name='U2'), row=4, col=1)

subplot_positions = [(1, 1), (3, 1), (2, 1), (4, 1)]

# Ciclo per aggiornare gli assi X per ciascun sotto-grafico
for row, col in subplot_positions:
    fig.update_xaxes(
        tickvals=[time_data[i] for i in range(0, len(time_data), 15)],  # Imposta i tick ogni 5 unità
        ticktext=[str(time_data[i]) for i in range(0, len(time_data), 15)],  # Personalizza le etichette dei tick
        row=row, col=col  # Per ogni grafico specificato dalla posizione
    )

# Impostazioni finali del grafico
fig.update_layout(
    title="Temperatures and Control Commands in Real Time",
    xaxis={'title': 'Time'},
    yaxis={'title': 'Temperature'},
    showlegend=True,
    width=1200,   # Larghezza della figura in pixel
    height=2400, # Altezza della figura in pixel
)

return fig

def run_dash(self):
    """Esegui il server Dash in un thread separato."""
    self.app.run(debug=False, use_reloader=False)

def stop(self):
    """Ferma i thread e chiude il file di log."""
    self.running = False
    self.thread.join()  # Attende che il thread principale termini


    if self.log_flag:
        self.log_file.close()  # Chiude il file di log
    self.lab.close()  # Chiude il laboratorio TCLab
    # Invia un segnale per terminare il server Dash
    self.app.shutdown()
    os.kill(os.getpid(), signal.SIGINT)  # Questo invia un CTRL+C al processo corrente
