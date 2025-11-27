from lsi_tcp import TCLabSystem, FakeTCLabSystem

if __name__ == "__main__":

    USE_FAKE = False
    if USE_FAKE:
        controller = TCLabSystem(log_flag=True, log_interval=1.0, plot_period=1.0, time_window=3000)
        step_duration = 900.0  # [s]
        real_time_factor = 1.0
    else:
        controller = FakeTCLabSystem(log_flag=True, log_interval=1.0, plot_period=1.0, time_window=3000, realtime_factor=10.0)
        step_duration = 200.0  # [s]
        real_time_factor = 10.0


    u_initial = 40.0
    u_final   = 60.0
    delta_step = 5.0

    u1 = u_initial
    direction = 1.0
    dt = 1.0  # [s]

    import time
    t_init_step = time.time()  # inizio del primo step

    while True:
        now = time.time()
        t = (now - t_init_step)*real_time_factor   # tempo trascorso dall'inizio dello step corrente

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
        time.sleep(dt/real_time_factor)

    controller.writeControlCommands(u1=0.0)
    controller.stop()

