from __future__ import absolute_import, print_function

from collections import namedtuple
from myhdl import Signal, intbv, always_seq, ResetSignal, instance, delay, \
    conversion, StopSimulation

N = 2
M = 2**N

Consts = namedtuple("Consts", "a b c")


def vars():
    """Conversion between intbv and list of boolean signals."""

    reset = ResetSignal(True, True, False)
    clk = Signal(False)
    inp_s = Signal(intbv(0)[N:])
    idx = Signal(intbv(0)[N:])
    rom = (1, 2)
    out_s = [Signal(intbv(0)[N:]) for i in range(2)]
    consts = Consts(1, 2, 3)

    @always_seq(clk.posedge, reset)
    def dut():
        tmp2 = 0
        i = idx
        tmp = rom[i]
        ii = idx.val
        if ii == consts.a:
            tmp2 = consts.a
        elif ii == consts.b:
            tmp2 = rom[1]
        else:
            tmp2 = rom[i]
        inp_s.next = rom[i]
        out_s[0].next = tmp
        out_s[1].next = tmp2

    @instance
    def stimulus():
        reset.next = True
        clk.next = False
        yield delay(10)
        reset.next = False
        yield delay(10)
        for k in range(N):
            clk.next = False
            yield delay(10)
            clk.next = True
            yield delay(10)
            assert out_s[0] == inp_s
            assert out_s[1] == inp_s
            print(int(out_s[0]))
        raise StopSimulation

    return dut, stimulus


# test
def test_vars():
    assert conversion.verify(vars) == 0
