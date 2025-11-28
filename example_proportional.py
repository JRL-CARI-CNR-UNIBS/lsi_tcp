from lsi_tcp import TCLabSystem, FakeTCLabSystem
from lsi_tcp import PController, ManualController
from lsi_tcp import ControllerDashboard
from lsi_tcp import SetpointProfile
from lsi_tcp import build_setpoint_profile, build_process, init_controllers, run_closed_loop
import time

# ==========================
# Configurazione generale
# ==========================

USE_FAKE = False            # True -> usa FakeTCLabSystem, False -> hardware reale
SAMPLING_PERIOD = 1.0      # [s]

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

    c2 = PController(
        sampling_period=sampling_period,
        Kp=2.0,
        u_min=0.0,
        u_max=100.0,
    )

    controllers = {
        "controller1": c1,
        "controller2": c2,
    }
    return controllers


def main():
    process, real_time_factor = build_process(USE_FAKE)
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
