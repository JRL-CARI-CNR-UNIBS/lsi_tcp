from lsi_tcp import TCLabSystem, FakeTCLabSystem
from lsi_tcp import PController, ManualController
from lsi_tcp import ControllerDashboard
from lsi_tcp import SetpointProfile
import time

# ==========================
# Configurazione generale
# ==========================

USE_FAKE = True            # True -> usa FakeTCLabSystem, False -> hardware reale
SAMPLING_PERIOD = 1.0      # [s]

REFERENCE_1 = 50.0
REFERENCE_2 = 50.0

INITIAL_U1 = 0.0
INITIAL_U2 = 0.0


def build_process(use_fake: bool):
    """
    Crea il sistema di processo (reale o fake) e restituisce:
        process, real_time_factor, step_duration
    """
    if use_fake:
        # Simulazione accelerata
        real_time_factor = 10.0
        process = FakeTCLabSystem(
            log_flag=True,
            log_interval=1.0,
            plot_period=1.0,
            time_window=3000,
            realtime_factor=real_time_factor,
        )
        step_duration = 200.0  # [s] tempo simulato
    else:
        # Hardware reale
        real_time_factor = 1.0
        process = TCLabSystem(
            log_flag=True,
            log_interval=1.0,
            plot_period=1.0,
            time_window=3000,
        )
        step_duration = 900.0  # [s] tempo reale

    return process, real_time_factor, step_duration


def build_controllers(sampling_period: float):
    """
    Crea i controllori e li restituisce in un dict.
    """
    c1 = PController(
        sampling_period=sampling_period,
        Kp=2.0,
        u_min=0.0,
        u_max=100.0,
    )
    # tuning iniziale
    c1.setParameters({"Kp": 3.0})

    c2 = ManualController(
        sampling_period=sampling_period,
        manual_control_action=20.0,
        u_min=0.0,
        u_max=100.0,
    )

    controllers = {
        "controller1": c1,
        "controller2": c2,
    }
    return controllers

def build_setpoint_profile(csv_path: str) -> SetpointProfile:
    # interpolate=False -> profilo "a gradini"
    # se vuoi profilo liscio: interpolate=True
    return SetpointProfile(csv_path=csv_path, interpolate=False)

def init_controllers(controllers, process):
    """
    Chiama .starting() sui controllori con le misure iniziali.
    """
    measure1, measure2 = process.readProcessVariables()

    controllers["controller1"].starting(
        reference=REFERENCE_1,
        measure=measure1,
        initial_u=INITIAL_U1,
        feedforward=0.0,
    )

    controllers["controller2"].starting(
        reference=REFERENCE_2,
        measure=measure2,
        initial_u=INITIAL_U2,
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

    except KeyboardInterrupt:
        print("Interrotto da tastiera.")
    finally:
        process.writeControlCommands(u1=0.0, u2=0.0)
        process.stop()
        print("Processo fermato e uscite azzerate.")



def main():
    process, real_time_factor, step_duration = build_process(USE_FAKE)
    controllers = build_controllers(SAMPLING_PERIOD)
    init_controllers(controllers, process)

    setpoint_profile = build_setpoint_profile("lsi_tcp/example.csv")
    run_closed_loop(
        process=process,
        controllers=controllers,
        setpoint_profile=setpoint_profile,
        real_time_factor=real_time_factor,
        max_duration=5*3600.0,
    )


if __name__ == "__main__":
    main()
