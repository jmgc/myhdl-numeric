
from myhdl import Signal, intbv, ResetSignal, always_seq, instance, delay, \
    StopSimulation, conversion
import os
path = os.path


def NonlocalBench():

    ALL_ONES = 2**7-1
    ONE = 1

    qout = Signal(intbv(ONE)[8:])
    init = Signal(bool(0))
    clk = Signal(bool(0))
    reset = ResetSignal(0, active=1, asynchronous=True)

    q = intbv(ONE)[8:]

    @always_seq(clk.posedge, reset=reset)
    def scrambler():
        if init:
            q[8:1] = ALL_ONES
        else:
            q[0] = q[7] ^ q[6]
            q[8:1] = q[7:0]
        qout.next = q[8:1]

    @instance
    def clkgen():
        clk.next = 1
        while True:
            yield delay(10)
            clk.next = not clk

    @instance
    def stimulus():
        reset.next = 0
        init.next = 0
        yield clk.negedge
        reset.next = 1
        yield clk.negedge
        print(int(qout))
        assert qout == ONE
        reset.next = 0
        for _ in range(100):
            yield clk.negedge
            print(int(qout))
        init.next = 1
        yield clk.negedge
        assert qout == ALL_ONES
        print(int(qout))
        init.next = 0
        for _ in range(300):
            print(int(qout))
        raise StopSimulation()

    return scrambler, clkgen, stimulus


def test_nonlocal():
    assert conversion.verify(NonlocalBench) == 0
