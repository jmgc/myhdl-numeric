from __future__ import absolute_import, print_function

from myhdl import Signal, intbv, always_comb, instance, delay, \
    conversion, StopSimulation

N = 2
M = 2**N


def temp(enable, clk, a, b, c):
    @always_comb
    def test():
        if enable:
            if clk:
                a.next = b

    return test

def generator():
    """Conversion between intbv and list of boolean signals."""

    enable = Signal(True)
    clk = [Signal(bool(0)) for _ in range(N)]
    inp_s = Signal(intbv(0)[N:])
    out_array = [Signal(intbv(0)[N:]) for _ in range(N)]
    out_s = Signal(intbv(0)[N:])
    unused = Signal(True)

    gen = [temp(enable, clk[i], out_array[i], inp_s, unused) for i in range(N)]

    #@always_comb
    #def test():
    #    if clk[0]:
    #        out.next = inp

    @instance
    def stimulus():
        for i in range(M):
            for j in range(N):
                inp_s.next = i
                for k in range(N):
                    clk[k].next = False
                clk[j].next = True
                yield delay(10)
                out_s.next = out_array[j]
                yield delay(10)
                for k in range(N):
                    clk[k].next = False
                assert out_s == inp_s
                print(int(out_s))
        raise StopSimulation

    return gen, stimulus


# test
def test_gen():
    conversion.analyze(generator)
    assert conversion.verify(generator) == 0
