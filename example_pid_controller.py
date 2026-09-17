from lsi_tcp import TCLabSystem, FakeTCLabSystem
from lsi_tcp import PIDController
from lsi_tcp import ControllerDashboard
from lsi_tcp import build_process, build_channels, init_channels, run_closed_loop
import argparse
import time

# ==========================
# Configurazione generale
# ==========================

SAMPLING_PERIOD = 1.0      # [s]

def build_controllers(sampling_period: float):
    """
    Crea i controllori AUTOMATICI (uno per canale) e li restituisce in un
    dict {"channel1": ..., "channel2": ...}. Il controllore manuale di
    ciascun canale (per il jog "a mano" dalla dashboard) viene creato
    internamente da build_channels(): qui basta il vostro controllore.
    """
    c1 = PIDController(
        sampling_period=sampling_period,
        # METTI QUI I PARAMETRI
        u_min=0.0,
        u_max=100.0,
    )

    c2 = PIDController(
        sampling_period=sampling_period,
        # METTI QUI I PARAMETRI
        u_min=0.0,
        u_max=100.0,
    )

    return {
        "channel1": c1,
        "channel2": c2,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Esempio controllore PID")
    parser.add_argument(
        "--fake",
        action="store_true",
        help="Usa FakeTCLabSystem invece dell'hardware reale",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    use_fake = args.fake

    process, real_time_factor = build_process(use_fake)
    controllers = build_controllers(SAMPLING_PERIOD)
    runtimes, state = build_channels(controllers, sampling_period=SAMPLING_PERIOD)
    init_channels(runtimes, state, process)

    run_closed_loop(
        process=process,
        runtimes=runtimes,
        state=state,
        real_time_factor=real_time_factor,
        is_simulator=use_fake,
        max_duration=5*3600.0,
    )


if __name__ == "__main__":
    main()
