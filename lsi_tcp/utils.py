from lsi_tcp import TCLabSystem, FakeTCLabSystem
from lsi_tcp import ManualController
from lsi_tcp import ControllerDashboard
from lsi_tcp import SetpointProfile
from lsi_tcp import DashboardState, ChannelRuntime
import time
from typing import Dict, Tuple


SAMPLING_PERIOD = 1.0      # [s]
CHANNEL_NAMES = ("channel1", "channel2")

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


def build_channels(auto_controllers: Dict[str, "BaseController"],
                    sampling_period: float,
                    u_min: float = 0.0,
                    u_max: float = 100.0) -> Tuple[Dict[str, ChannelRuntime], DashboardState]:
    """
    A partire da {"channel1": controllore_automatico_T1, "channel2": controllore_automatico_T2}
    (il controllore scritto dallo studente, es. PController o il vostro PID),
    crea per ciascun canale un ManualController SEMPRE istanziato e li
    coordina con un ChannelRuntime; entrambi i ChannelRuntime condividono lo
    stesso DashboardState, che è anche l'oggetto che la dashboard usa per
    leggere/scrivere modalità, potenza manuale e setpoint.

    Ritorna (runtimes, state):
        runtimes -> dict {"channel1": ChannelRuntime, "channel2": ChannelRuntime},
                    da passare a init_channels() e run_closed_loop();
        state    -> DashboardState condiviso, idem.
    """
    missing = [name for name in CHANNEL_NAMES if name not in auto_controllers]
    if missing:
        raise KeyError(
            f"auto_controllers deve contenere le chiavi {CHANNEL_NAMES}; mancano: {missing}"
        )

    state = DashboardState(CHANNEL_NAMES)
    runtimes = {}
    for name in CHANNEL_NAMES:
        manual_controller = ManualController(
            sampling_period=sampling_period,
            manual_control_action=0.0,
            u_min=u_min,
            u_max=u_max,
        )
        runtimes[name] = ChannelRuntime(name, manual_controller, auto_controllers[name], state)

    return runtimes, state


def init_channels(runtimes: Dict[str, ChannelRuntime],
                   state: DashboardState,
                   process,
                   initial_reference: float = 20.0) -> None:
    """
    Inizializza ENTRAMBI i controllori (manuale e automatico) di ciascun
    canale con starting(), e allinea il setpoint iniziale in DashboardState.

    Va chiamata una volta, prima di entrare in run_closed_loop(): senza
    questa chiamata lo stato interno del controllore automatico (es.
    l'integratore di un PI) non verrebbe mai inizializzato finché non
    avviene un primo cambio di modalità manuale->automatico dalla dashboard.
    """
    measure1, measure2 = process.readProcessVariables()
    measures = dict(zip(CHANNEL_NAMES, (measure1, measure2)))

    for name, runtime in runtimes.items():
        measure = measures[name]
        state.set_setpoint(name, initial_reference)
        runtime.manual_controller.starting(
            reference=initial_reference, measure=measure, initial_u=0.0, feedforward=0.0,
        )
        runtime.auto_controller.starting(
            reference=initial_reference, measure=measure, initial_u=0.0, feedforward=0.0,
        )


def run_closed_loop(process,
                    runtimes: Dict[str, ChannelRuntime],
                    state: DashboardState,
                    real_time_factor: float,
                    setpoint_profile: SetpointProfile | None = None,
                    setpoint_from_profile: bool = False,
                    is_simulator: bool = True,
                    max_duration: float | None = None,
                    sampling_period: float = SAMPLING_PERIOD):
    """
    Loop principale di controllo.

    setpoint_profile, setpoint_from_profile:
        setpoint_from_profile=False (default, fase di TARATURA INTERATTIVA):
            il setpoint di ciascun canale in automatico è quello impostato a
            mano dallo studente nella dashboard; setpoint_profile non serve
            (può restare None).
        setpoint_from_profile=True (fase di VALIDAZIONE FINALE):
            ad ogni ciclo il setpoint dei canali in automatico viene
            sovrascritto con il valore di `setpoint_profile` al tempo
            corrente; il campo numerico della dashboard viene disabilitato
            (coerentemente, ControllerDashboard riceve lo stesso flag).
            Richiede un setpoint_profile.
    is_simulator: True se `process` è un FakeTCLabSystem (solo per il badge
        di stato della dashboard).
    max_duration: durata massima dell'esperimento in secondi di processo (opzionale).
    sampling_period: periodo di campionamento del loop [s]. Va allineato al
        sampling_period effettivamente configurato sui controllori passati
        (altrimenti il loop gira comunque al valore di default, ignorando
        in modo silenzioso quello impostato sui controllori).
    """
    if setpoint_from_profile and setpoint_profile is None:
        raise ValueError("setpoint_from_profile=True richiede un setpoint_profile")

    dashboard = ControllerDashboard(
        runtimes,
        state,
        system=process,
        is_simulator=is_simulator,
        setpoint_from_profile=setpoint_from_profile,
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

            # 1) in fase di validazione: sovrascrivo il setpoint condiviso
            #    con il valore del profilo al tempo corrente
            if setpoint_from_profile:
                ref1, ref2 = setpoint_profile.get_setpoints(t_proc)
                state.set_setpoint("channel1", ref1)
                state.set_setpoint("channel2", ref2)

            # 2) leggo le misure dal processo
            measure1, measure2 = process.readProcessVariables()

            # 3) ogni ChannelRuntime decide quale dei suoi due controllori
            #    (manuale o automatico) calcola u, gestendo da solo il
            #    bumpless transfer al cambio di modalità
            u1, sp1 = runtimes["channel1"].step(measure=measure1, feedforward=0.0)
            u2, sp2 = runtimes["channel2"].step(measure=measure2, feedforward=0.0)

            # 4) scrivo comandi
            process.writeControlCommands(u1=u1, u2=u2)

            # 5) rispetto il periodo di campionamento
            time.sleep(sampling_period / real_time_factor)

            dashboard.get_values(T1=measure1, T2=measure2, U1=u1, U2=u2, SP1=sp1, SP2=sp2)

    except KeyboardInterrupt:
        print("Interrotto da tastiera.")
    finally:
        process.writeControlCommands(u1=0.0, u2=0.0)
        process.stop()
        print("Processo fermato e uscite azzerate.")
