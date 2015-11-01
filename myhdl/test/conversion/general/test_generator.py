from __future__ import absolute_import, print_function

from myhdl import Signal, intbv, always_comb, instance, delay, \
    conversion, StopSimulation

N = 8
M = 2**N


def temp(clk, a, b):
 
    @always_comb
    def test():
        if clk:
            a.next = b


def generator():
    """Conversion between intbv and list of boolean signals."""

    clk = [Signal(bool(0)) for _ in range(N)]
    inp = Signal(intbv(0)[N:])
    out = Signal(intbv(0)[N:])

    gen = [temp(clk[i], inp, out) for i in range(N)]

    #@always_comb
    #def test():
    #    if clk[0]:
    #        out.next = inp

    @instance
    def stimulus():
        for i in range(M):
            for j in range(N):
                inp.next = i
                for k in range(N):
                    clk[k].next = False
                clk[j].next = True
                yield delay(10)
                assert out == inp
                print(int(out))
        raise StopSimulation

    return gen, stimulus


# test
def test_gen():
    assert conversion.verify(generator) == 0
