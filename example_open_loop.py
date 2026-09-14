from lsi_tcp import TCLabSystem, FakeTCLabSystem
from lsi_tcp import ManualController
from lsi_tcp import ControllerDashboard
from lsi_tcp import build_process, build_channels, init_channels, run_closed_loop
import time

# ==========================
# Configurazione generale
# ==========================

USE_FAKE = True            # True -> usa FakeTCLabSystem, False -> hardware reale
SAMPLING_PERIOD = 1.0      # [s]

def build_controllers(sampling_period: float):
    """
    Prova di identificazione (anello aperto): nessun controllore automatico
    ancora scritto, entrambi i canali restano in ManualController (la
    potenza U si imposta a mano dalla dashboard). Ritorna il dict richiesto
    da build_channels(): {"channel1": ..., "channel2": ...}.
    """
    c1 = ManualController(
        sampling_period=sampling_period,
        manual_control_action=0.0,
        u_min=0.0,
        u_max=100.0,
    )

    c2 = ManualController(
        sampling_period=sampling_period,
        manual_control_action=0.0,
        u_min=0.0,
        u_max=100.0,
    )

    return {
        "channel1": c1,
        "channel2": c2,
    }


def main():
    process, real_time_factor = build_process(USE_FAKE)
    controllers = build_controllers(SAMPLING_PERIOD)
    runtimes, state = build_channels(controllers, sampling_period=SAMPLING_PERIOD)
    init_channels(runtimes, state, process)

    run_closed_loop(
        process=process,
        runtimes=runtimes,
        state=state,
        real_time_factor=real_time_factor,
        is_simulator=USE_FAKE,
        max_duration=5*3600.0,
    )


if __name__ == "__main__":
    main()
