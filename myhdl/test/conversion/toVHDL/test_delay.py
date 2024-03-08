
from myhdl import *

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

def test_delay():
    assert conversion.verify(bench_delay) == 0
