from lsi_tcp import TCLabSystem, FakeTCLabSystem
from lsi_tcp import PController
from lsi_tcp import ControllerDashboard
from lsi_tcp import build_process, build_channels, init_channels, run_closed_loop, build_setpoint_profile
import argparse
import time

# ==========================
# Configurazione generale
# ==========================

SAMPLING_PERIOD = 1.0      # [s]

# False -> taratura interattiva: il setpoint di ciascun canale in automatico
#          si imposta a mano dalla dashboard.
# True  -> validazione finale: il setpoint segue lsi_tcp/example.csv (o un
#          vostro CSV con la stessa struttura, vedi README §3.4).
SETPOINT_FROM_PROFILE = False

def build_controllers(sampling_period: float):
    """
    Crea i controllori AUTOMATICI (uno per canale) e li restituisce in un
    dict {"channel1": ..., "channel2": ...}. Il controllore manuale di
    ciascun canale (per il jog "a mano" dalla dashboard) viene creato
    internamente da build_channels(): qui basta il vostro controllore.
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

    return {
        "channel1": c1,
        "channel2": c2,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Esempio controllore proporzionale")
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

    setpoint_profile = build_setpoint_profile("lsi_tcp/example.csv") if SETPOINT_FROM_PROFILE else None

    run_closed_loop(
        process=process,
        runtimes=runtimes,
        state=state,
        real_time_factor=real_time_factor,
        setpoint_profile=setpoint_profile,
        setpoint_from_profile=SETPOINT_FROM_PROFILE,
        is_simulator=use_fake,
        max_duration=5*3600.0,
    )


if __name__ == "__main__":
    main()