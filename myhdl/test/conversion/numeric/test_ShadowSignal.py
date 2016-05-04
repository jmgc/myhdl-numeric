from __future__ import absolute_import
from myhdl.test.conftest import bug
from myhdl import Signal, uintba, instance, delay, conversion, \
    ConcatSignal, TristateSignal, sfixba, always_comb, StopSimulation, \
    toVHDL, toVerilog


def bench_SliceSignal():
    s = Signal(uintba(0, 8))
    a, b, c = s(7), s(5), s(0)
    d, e, f, g = s(8, 5), s(6, 3), s(8, 0), s(4, 3)
    N = len(s)

    @instance
    def check():
        for i in range(N):
            s.next = i
            yield delay(10)
            print(int(a))
            print(int(b))
            print(int(c))
            print(int(d))
            print(int(e))
            print(int(f))
            print(int(g))

    return check


def test_SliceSignal():
    assert conversion.verify(bench_SliceSignal) == 0


def bench_ConcatSignal():

    a = Signal(uintba(0, 5))
    b = Signal(bool(0))
    c = Signal(uintba(0, 3))
    d = Signal(uintba(0, 4))

    s = ConcatSignal(a, b, c, d)

    I_max = 2**len(a)
    J_max = 2**len(b)
    K_max = 2**len(c)
    M_max = 2**len(d)

    @instance
    def check():
        for i in range(I_max):
            for j in range(J_max):
                for k in range(K_max):
                    for m in range(M_max):
                        a.next = i
                        b.next = j
                        c.next = k
                        d.next = m
                        yield delay(10)
                        print(int(s))

    return check


def test_ConcatSignal():
    assert conversion.verify(bench_ConcatSignal) == 0


def bench_ConcatSignalWithConsts():

    a = Signal(uintba(0, 5))
    b = Signal(bool(0))
    c = Signal(uintba(0, 3))
    d = Signal(uintba(0, 4))
    e = Signal(uintba(0, 1))

    c1 = "10"
    c2 = uintba(3, 3)
    c3 = '0'
    c4 = bool(1)
    c5 = uintba(42, 8)  # with leading zeroes

    s = ConcatSignal(c1, a, c2, b, c3, c, c4, d, c5, e)

    I_max = 2**len(a)
    J_max = 2**len(b)
    K_max = 2**len(c)
    M_max = 2**len(d)

    @instance
    def check():
        for i in range(I_max):
            for j in range(J_max):
                for k in range(K_max):
                    for m in range(M_max):
                        for n in range(2**len(e)):
                            a.next = i
                            b.next = j
                            c.next = k
                            d.next = m
                            e.next = n
                            yield delay(10)
                            print(int(s))

    return check


def test_ConcatSignalWithConsts():
    assert conversion.verify(bench_ConcatSignalWithConsts) == 0


def bench_TristateSignal():
    s = TristateSignal(uintba(0, 8))
    t = TristateSignal(sfixba(0, 1, 0))
    a = s.driver()
    b = s.driver()
    c = s.driver()
    d = t.driver()
    e = t.driver()

    @instance
    def check():
        a.next = None
        b.next = None
        c.next = None
        d.next = None
        e.next = None
        yield delay(10)
        a.next = 1
        d.next = 0
        yield delay(10)
        print(int(s))
        a.next = None
        b.next = 122
        yield delay(10)
        print(int(s))
        b.next = None
        c.next = 233
        yield delay(10)
        print(int(s))
        c.next = None
        yield delay(10)

    return check


#@bug("Tristate pending", "vhdl")
def test_TristateSignal():
    assert conversion.verify(bench_TristateSignal) == 0


def permute(x, a, mapping):

    p = [a(m) for m in mapping]

    q = ConcatSignal(*p)

    @always_comb
    def assign():
        x.next = q

    return assign


def bench_permute(conv=False):

    x = Signal(uintba(0, 3))
    a = Signal(sfixba(0, 3, -2))
    mapping = (0, 2, 1)

    if conv:
        dut = conv(permute, x, a, mapping)
    else:
        dut = permute(x, a, mapping)

    @instance
    def stimulus():
        for i in range(2**len(a)):
            a.next = i
            yield delay(10)
            print("%d %d" % (x, a))
            assert x[2] == a[0]
            assert x[1] == a[2]
            assert x[0] == a[1]
        raise StopSimulation()

    return dut, stimulus


def test_permute():
    assert conversion.verify(bench_permute) == 0

bench_permute(toVHDL)
bench_permute(toVerilog)
