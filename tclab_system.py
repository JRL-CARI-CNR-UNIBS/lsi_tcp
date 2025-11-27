import tclab
import time
import threading
import csv
from datetime import datetime
import dash
from dash import dcc, html
import plotly.graph_objs as go
import dash.dependencies as dd
from plotly.subplots import make_subplots
import logging
import os
import signal
import math

class TCLabSystem:
    def __init__(self, log_flag=False, log_interval=1.0, plot_period=1.0, time_window=300):
        # Imposta il livello di log di Flask per evitare la verbosità
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)  # Solo errori, niente info o debug

        # Inizializzazione dell'oggetto TCLab
        self.lab = tclab.TCLab()
        self.log_flag = log_flag
        self.log_interval = log_interval
        self.plot_period = plot_period
        self.time_window = time_window  # Finestra temporale (numero di dati da visualizzare)
        self.running = True

        # File di log (solo se log_flag è True)
        self.log_file = None
        if self.log_flag:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            self.log_file = open(f'tclab_{timestamp}.csv', mode='w', newline='')
            self.csv_writer = csv.writer(self.log_file)
            self.csv_writer.writerow(['Time', 'T1', 'T2', 'U1', 'U2'])

        # Creazione di un lock per la sicurezza del thread
        self.lock = threading.Lock()

        # Liste per memorizzare i dati delle temperature e comandi
        self.time_data = []
        self.t1_data = []
        self.t2_data = []
        self.u1_data = []
        self.u2_data = []
        
        self.u1 = 0.0
        self.u2 = 0.0

        # Variabile per sapere se è il primo ciclo
        self.first_run = True

        # Creazione e avvio del thread per il ciclo di lettura e scrittura
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

        # Inizializzazione di Dash
        self.app = dash.Dash(__name__)
        self.app.layout = html.Div([
            html.Div([
                dcc.Input(id='time-window', type='number', value=self.time_window, min=1, step=1,
                          style={'width': '100px'}),
                html.Label('Finestra temporale (n° dati da visualizzare)')
            ]),
            dcc.Graph(id='real-time-graph'),
            dcc.Interval(id='interval-component', interval=self.plot_period * 1000, n_intervals=0)
        ])

        # Callback per aggiornare il grafico in tempo reale
        self.app.callback(
            dd.Output('real-time-graph', 'figure'),
            [dd.Input('interval-component', 'n_intervals'),
             dd.Input('time-window', 'value')]
        )(self.update_graph)

        # Avvio del server Dash in un thread separato
        self.app_thread = threading.Thread(target=self.run_dash)
        self.app_thread.start()

    def _run(self):
        """Ciclo principale per leggere e scrivere i dati del laboratorio."""
        while self.running:
            # Acquisizione delle variabili di processo
            t1, t2 = self.readProcessVariables()

            # Se T1 o T2 > 40, accendi i riscaldatori
            u1, u2 = self.u1, self.u2

            # Log dei dati (se log_flag è attivo)
            if self.log_flag:
                self._log_data(t1, t2, u1, u2)

            # Pausa per il periodo di ciclo definito
            time.sleep(self.log_interval)

    def readProcessVariables(self):
        """Legge le variabili di processo (temperature T1 e T2)."""
        with self.lock:
            t1 = self.lab.T1  # Temperatura del riscaldatore 1
            t2 = self.lab.T2  # Temperatura del riscaldatore 2
        return t1, t2
    def writeControlCommands(self, u1 = 0, u2 = 0):
        """Imposta i comandi di controllo manualmente, con controllo dei limiti."""
        with self.lock:
            # Controllo che u1 e u2 siano tra 0 e 100
            u1 = max(0, min(100, u1))
            u2 = max(0, min(100, u2))
            
            # Scrivi i comandi di controllo
            self.lab.Q1(u1)
            self.lab.Q2(u2)
            self.u1=u1
            self.u2=u2

        return u1, u2



    def _log_data(self, t1, t2, u1, u2):
        """Scrive i dati su file CSV."""
        with self.lock:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.csv_writer.writerow([timestamp, t1, t2, u1, u2])
            self.log_file.flush()

    def update_graph(self, n, time_window):
        """Funzione per aggiornare il grafico in tempo reale."""
        # Leggi le temperature e i comandi
        t1, t2 = self.readProcessVariables()
        
        # Aggiungi i dati al grafico
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Se è il primo ciclo, inizializza tutti i dati con il primo valore
        if self.first_run:
            self.time_data = [timestamp] * time_window
            self.t1_data = [t1] * time_window
            self.t2_data = [t2] * time_window
            self.u1_data = [self.u1] * time_window
            self.u2_data = [self.u2] * time_window
            self.first_run = False
        else:
            self.time_data.append(timestamp)
            self.t1_data.append(t1)
            self.t2_data.append(t2)
            self.u1_data.append(self.u1)
            self.u2_data.append(self.u2)

        # Limita la visualizzazione della finestra temporale
        # Assicurati che non vengano richiesti più dati di quelli disponibili
        max_time_window = min(len(self.time_data), time_window)

        time_data = self.time_data[-max_time_window:]
        t1_data = self.t1_data[-max_time_window:]
        t2_data = self.t2_data[-max_time_window:]
        u1_data = self.u1_data[-max_time_window:]
        u2_data = self.u2_data[-max_time_window:]

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

if __name__ == "__main__":
    controller = TCLabSystem(log_flag=True, log_interval=1.0, plot_period=1.0, time_window=3000)

    u_initial = 40.0
    u_final   = 60.0
    delta_step = 5.0
    step_duration = 900.0  # [s]

    u1 = u_initial
    direction = 1.0
    dt = 1.0  # [s]

    import time
    t_init_step = time.time()  # inizio del primo step

    while True:
        now = time.time()
        t = now - t_init_step   # tempo trascorso dall'inizio dello step corrente

        if t >= step_duration:
            # passo allo step successivo
            t_init_step = now   # reset del tempo di inizio step
            u1 += delta_step * direction

            if u1 > u_final:
                direction *= -1
                u1 = u_final + delta_step * direction

            if u1 < u_initial:
                direction *= -1
                u1 = u_initial + delta_step * direction

        controller.writeControlCommands(u1=u1)
        time.sleep(dt)

    controller.writeControlCommands(u1=0.0)
    controller.stop()

