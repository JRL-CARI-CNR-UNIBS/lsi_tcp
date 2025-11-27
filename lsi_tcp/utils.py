from lsi_tcp import TCLabSystem, FakeTCLabSystem
from lsi_tcp import PController, ManualController
from lsi_tcp import ControllerDashboard
from lsi_tcp import SetpointProfile
import time


SAMPLING_PERIOD = 1.0      # [s]

# ==========================
# Configurazione generale
def build_process(use_fake: bool, real_time_factor: float = 10.0):
    """
    Crea il sistema di processo (reale o fake) e restituisce:
        process, real_time_factor, step_duration
    """
    if use_fake:
        # Simulazione accelerata
        process = FakeTCLabSystem(
            log_flag=True,
            log_interval=1.0,
            plot_period=1.0,
            time_window=3000,
            realtime_factor=real_time_factor,
        )
    else:
        # Hardware reale
        real_time_factor = 1.0
        process = TCLabSystem(
            log_flag=True,
            log_interval=1.0,
            plot_period=1.0,
            time_window=3000,
        )

    return process, real_time_factor

def build_setpoint_profile(csv_path: str) -> SetpointProfile:
    # interpolate=False -> profilo "a gradini"
    # se vuoi profilo liscio: interpolate=True
    return SetpointProfile(csv_path=csv_path)

def init_controllers(controllers, process):
    """
    Chiama .starting() sui controllori con le misure iniziali.
    """
    measure1, measure2 = process.readProcessVariables()

    controllers["controller1"].starting(
        reference=20.0,
        measure=measure1,
        initial_u=0.0,
        feedforward=0.0,
    )

    controllers["controller2"].starting(
        reference=20.0,
        measure=measure2,
        initial_u=0.0,
        feedforward=0.0,
    )

def run_closed_loop(process,
                    controllers,
                    setpoint_profile: SetpointProfile,
                    real_time_factor: float,
                    max_duration: float | None = None):
    """
    Loop principale di controllo.
    max_duration: durata massima dell'esperimento in secondi di processo (opzionale).
    """

    dashboard = ControllerDashboard(
        controllers,
        host="127.0.0.1",
        port=8051,
        debug=True,
        serve_dev_bundles=False,
        start_in_background=True,
    )

    t_init = time.time()

    try:
        while True:
            now = time.time()
            # tempo di processo (in secondi "fisici" del modello)
            t_proc = (now - t_init) * real_time_factor

            # opzionale: fermami dopo max_duration
            if (max_duration is not None) and (t_proc >= max_duration):
                print("Durata massima raggiunta, esco dal loop.")
                break

            # 1) leggo i setpoint dal profilo
            ref1, ref2 = setpoint_profile.get_setpoints(t_proc)

            # 2) leggo le misure dal processo
            measure1, measure2 = process.readProcessVariables()

            # 3) calcolo azioni di controllo
            u1 = controllers["controller1"].computeControlAction(
                reference=ref1,
                measure=measure1,
                feedforward=0.0,
            )
            u2 = controllers["controller2"].computeControlAction(
                reference=ref2,
                measure=measure2,
                feedforward=0.0,
            )

            # 4) scrivo comandi
            process.writeControlCommands(u1=u1, u2=u2)

            # 5) rispetto il periodo di campionamento
            time.sleep(SAMPLING_PERIOD / real_time_factor)

            dashboard.get_values(T1=measure1, T2=measure2, U1=u1, U2=u2, SP1=ref1, SP2=ref2)

    except KeyboardInterrupt:
        print("Interrotto da tastiera.")
    finally:
        process.writeControlCommands(u1=0.0, u2=0.0)
        process.stop()
        print("Processo fermato e uscite azzerate.")

