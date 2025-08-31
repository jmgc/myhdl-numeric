from myhdl import Signal, intbv, always_seq, instance, delay, StopSimulation, \
    ResetSignal, conversion

def hierachy_level(clk, reset, z, a):
    @always_seq(clk.posedge, reset)
    def logic():
        if a == 1:
            z.next = 0
        elif a in (2, 3):
            z.next = 1
        else:
            z.next = 3

    return logic

def hierachy_level_2(clk, reset, z, a):
    y = Signal(intbv(0)[3:])
    comp1 = hierachy_level(clk, reset, y, a)
    comp2 = hierachy_level(clk, reset, z, y)
    return comp1, comp2

def hierachy_level_1(clk, reset, z, a):
    y = Signal(intbv(0)[4:])
    comp1 = hierachy_level_2(clk, reset, y, a)
    comp2 = hierachy_level_2(clk, reset, z, y)
    return comp1, comp2


def test_hierarchy_analyse():
    clk = Signal(False)
    reset = ResetSignal(True, True, False)
    a = Signal(intbv(0)[3:])
    z = Signal(intbv(0)[4:])

    assert conversion.analyze(hierachy_level_1, clk, reset, z, a) == 0
