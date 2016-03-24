from __future__ import absolute_import, print_function

from myhdl import Signal, intbv, always_seq, ResetSignal, now, \
    instance, delay, StopSimulation, Simulation, toVHDL
from myhdl.conversion import analyze, verify
from myhdl.test.conftest import bug


"""
This set of tests exercies a peculiar scenario where an
expanded interface Signal is flagged as having multiple
drivers.  This appears to be a name collision in the name
expansion and was introduced in 08519b4.
"""


class Intf1(object):
    def __init__(self, elements):
        if elements > 1:
            self.sig1 = Signal(False)
            self.sig2 = [Signal(False) for _ in range(elements)]
            self.sig3 = [Signal(intbv(0)[8:]) for _ in range(elements)]
        else:
            self.sig1 = Signal(False)
            self.sig2 = Signal(False)
            self.sig3 = Signal(intbv(0)[8:])


def m_top(clock, reset, intf1, intf2, intf3):

    @always_seq(clock.posedge, reset)
    def proc():
        if intf2.sig1:
            intf1.sig1.next = True
            intf2.sig2.next = intf1.sig2[0]
            intf1.sig3[0].next = intf2.sig3
            intf1.sig3[1].next = 0
        elif intf3.sig1:
            intf1.sig1.next = True
            intf3.sig2.next = intf1.sig2[1]
            intf1.sig3[0].next = 0
            intf1.sig3[1].next = intf3.sig3
        else:
            intf1.sig1.next = False
            intf2.sig2.next = False
            intf3.sig2.next = False
            intf1.sig3[0].next = 0
            intf1.sig3[1].next = 0

    return proc


def c_testbench_five():
    """ yet another interface test.
    This test is used to expose a particular bug that was discovered
    during the development of interface conversion.  The structure
    used in this example caused and invalid multiple driver error.
    """
    clock = Signal(False)
    reset = ResetSignal(False, True, False)

    intf1 = Intf1(2)
    intf2 = Intf1(1)
    intf3 = Intf1(1)

    tbdut = m_top(clock, reset, intf1, intf2, intf3)

    @instance
    def tbclk():
        clock.next = False
        while True:
            yield delay(10)
            clock.next = not clock

    @instance
    def tbstim():
        reset.next = True
        intf1.sig2[0].next = False
        intf1.sig2[1].next = False
        intf2.sig1.next = False
        intf2.sig3.next = 0
        intf3.sig1.next = False
        intf3.sig3.next = 0
        yield clock.posedge
        reset.next = False
        yield clock.posedge
        intf1.sig2[0].next = True
        intf1.sig2[1].next = False
        intf2.sig1.next = True
        intf2.sig3.next = 1
        intf3.sig1.next = False
        intf3.sig3.next = 0
        yield clock.posedge
        intf1.sig2[0].next = False
        intf1.sig2[1].next = False
        intf2.sig1.next = False
        intf2.sig3.next = 1
        intf3.sig1.next = True
        intf3.sig3.next = 0
        yield clock.posedge
        intf1.sig2[0].next = True
        intf1.sig2[1].next = True
        intf2.sig1.next = False
        intf2.sig3.next = 1
        intf3.sig1.next = True
        intf3.sig3.next = 3
        yield clock.posedge
        intf1.sig2[0].next = True
        intf1.sig2[1].next = True
        intf2.sig1.next = False
        intf2.sig3.next = 1
        intf3.sig1.next = False
        intf3.sig3.next = 3
        yield clock.posedge
        yield clock.posedge
        yield clock.posedge

        raise StopSimulation

    @always_seq(clock.posedge, reset)
    def tbcheck():
        if intf1.sig1:
            print(now(), intf1.sig1)
            print(now(), intf1.sig2[0], intf1.sig2[1])
            print(now(), int(intf1.sig3[0]), int(intf1.sig3[1]))

        if intf2.sig1:
            print(now(), intf2.sig1, intf2.sig2, int(intf2.sig3))

        if intf3.sig1:
            print(now(), intf3.sig1, intf3.sig2, int(intf3.sig3))

    return tbclk, tbstim, tbdut, tbcheck


def test_five_testbench():
    Simulation(c_testbench_five()).run()


def test_five_analyze():
    clock = Signal(False)
    reset = ResetSignal(False, True, False)

    intf1 = Intf1(2)
    intf2 = Intf1(1)
    intf3 = Intf1(1)

    analyze(m_top, clock, reset, intf1, intf2, intf3)


def test_five_verify():
    assert verify(c_testbench_five) == 0


def test_conversion():
    toVHDL(c_testbench_five)


def c_test_six_intermediate_names(reset, clk, intf1, intf2, intf3):

    @always_seq(clk.posedge, reset)
    def fsm():
        intf3.sig1.next = intf1.sig1
        intf3.sig2.next = intf2.sig2

    return fsm


def c_test_six_up():
    clk = Signal(False)
    reset = ResetSignal(False, True, False)
    intf1 = Intf1(2)
    intf3 = Intf1(1)

    dut = c_test_six_intermediate_names(reset, clk, intf1, intf1, intf3)

    return dut


@bug("Detection of ports names", "vhdl")
def test_six_verify():
    assert verify(c_test_six_up) == 0


def c_test_seven_intermediate_signals(reset, clk, intf1, intf2, intf3):

    @always_seq(clk.posedge, reset)
    def fsm():
        intf3.sig1.next = intf1.sig1
        intf3.sig2.next = intf2.sig2

    return fsm


def c_test_seven_signals():
    clk = Signal(False)
    reset = ResetSignal(True, True, False)
    intf1 = Intf1(1)
    intf2 = Intf1(1)
    intf3 = Intf1(1)

    dut = c_test_seven_intermediate_signals(reset, clk, intf1, intf2, intf3)

    @instance
    def stimulus():
        reset.next = True
        intf1.sig1.next = False
        intf2.sig2.next = False
        clk.next = False
        yield delay(10)
        clk.next = True
        reset.next = False
        yield delay(10)
        clk.next = False
        intf1.sig1.next = True
        while not intf3.sig1:
            yield delay(10)
            clk.next = True
            yield delay(10)
            clk.next = False
        yield delay(10)
        clk.next = True
        yield delay(10)
        raise StopSimulation

    @always_seq(clk.posedge, reset)
    def fsm():
        print(now())
        print(intf3.sig2)

    return dut, stimulus, fsm


@bug("Detection of ports names", "vhdl")
def test_seven_verify():
    assert verify(c_test_seven_signals) == 0
    #sim = Simulation(c_test_seven_signals())
    #sim.run()


if __name__ == '__main__':
    print("*** verify example testbench ")
    test_five_testbench()
    print("*** verify example module conversion ")
    test_five_analyze()
    print("*** test testbench conversion ")
    test_conversion()
    print("*** verify testbench conversion and execution")
    test_five_verify()
    print("*** verify testbench intermediate level")
    test_six_verify()
    print("*** verify testbench intermediate signals")
    test_seven_verify()
