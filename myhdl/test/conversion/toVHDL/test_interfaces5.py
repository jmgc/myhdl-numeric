from myhdl import Signal, intbv, always_seq, ResetSignal, now, \
    instance, delay, StopSimulation, Simulation, toVHDL, delay
from myhdl import ToVHDLError, always_comb, always_seq
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


def test_five_verify_std_logic():
    toVHDL.name = "five_verify_std_logic"
    toVHDL.std_logic_ports = True
    assert verify(c_testbench_five) == 0
    toVHDL.std_logic_ports = False
    toVHDL.name = None

def test_five_verify():
    toVHDL.std_logic_ports = False
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


def test_six_verify():
    try:
        analyze(c_test_six_up)
        assert False, "Should have raised an exception"
    except ToVHDLError:
        pass


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


def test_seven_verify():
    assert verify(c_test_seven_signals) == 0
    #sim = Simulation(c_test_seven_signals())
    #sim.run()


class ClkReset:
    def __init__(self):
        self.clk = Signal(False)
        self.reset = ResetSignal(True, True, False)
        self.value = Signal(False)


def clk_reset_transfer(clk_in: Signal, reset_in: ResetSignal, value_in: Signal,
                       clk_out: Signal, reset_out: ResetSignal, value_out: Signal):

    @always_comb
    def comb():
        clk_out.next = clk_in
        reset_out.next = reset_in
        value_out.next = value_in

    return comb

def clk_reset_test_bench():
    clk_0 = Signal(False)
    reset_0 = ResetSignal(True, True, False)
    clk_1 = Signal(False)
    reset_1 = ResetSignal(True, True, False)
    value_0 = Signal(False)
    value_1 = Signal(False)
    class_0 = ClkReset()
    class_1 = ClkReset()

    comb_signal = clk_reset_transfer(clk_0, reset_0, value_0, clk_1, reset_1, value_1)
    comb_class = clk_reset_transfer(class_0.clk, class_0.reset, class_0.value,
                                    class_1.clk, class_1.reset, class_1.value)

    data_signal = Signal(intbv(0)[8:])

    @always_seq(clk_1.posedge, reset_1)
    def seq_signal():
        if value_1:
            print(now(), "%d" % data_signal)
            data_signal.next = data_signal + 1

    data_class = Signal(intbv(0)[8:])

    @always_seq(class_1.clk.posedge, class_1.reset)
    def seq_class():
        if class_1.value:
            print(now(), "%d" % data_class)
            data_class.next = data_class + 1

    @instance
    def stimulus():
        clk_0.next = False
        reset_0.next = True
        class_0.clk.next = False
        class_0.reset.next = True
        yield delay(10)
        reset_0.next = False
        class_0.reset.next = False
        yield delay(10)
        for _ in range(10):
            clk_0.next = False
            class_0.clk.next = True
            yield delay(10)
            clk_0.next = True
            class_0.clk.next = False
            yield delay(10)
            value_0.next = not value_0
            class_0.value.next = not class_0.value
        clk_0.next = False
        class_0.clk.next = True
        yield delay(10)
        raise StopSimulation

    return comb_signal, comb_class, seq_signal, seq_class, stimulus


def test_clk_reset():
    assert verify(clk_reset_test_bench) == 0


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
