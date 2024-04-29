from myhdl import ToVHDLError, instance, delay, now, toVHDL, Signal, instances, StopSimulation, conversion


def bench_delay():
    clock = Signal(False)

    PERIOD = 10

    @instance
    def clockgen():
        clock.next = False
        while True:
            yield delay(PERIOD // 2 + 1)
            clock.next = not clock

    @instance
    def stimulus():
        for i in range(16):
            yield clock.posedge
            print(now())

        raise StopSimulation

    return instances()


def test_delay_ns():
    toVHDL.timescale = '1 ns'
    assert conversion.verify(bench_delay) == 0


def test_delay_ps():
    toVHDL.timescale = '1 ps'
    assert conversion.verify(bench_delay) == 0


def test_timescale_fail():
    try:
        toVHDL.timescale = '1ns'
        assert False, "Expected ToVHDLError"
    except ToVHDLError:
        pass

    try:
        toVHDL.timescale = '1'
        assert False, "Expected ToVHDLError"
    except ToVHDLError:
        pass

    try:
        toVHDL.timescale = 'ns'
        assert False, "Expected ToVHDLError"
    except ToVHDLError:
        pass

    try:
        toVHDL.timescale = '1 Ns'
        assert False, "Expected ToVHDLError"
    except ToVHDLError:
        pass
