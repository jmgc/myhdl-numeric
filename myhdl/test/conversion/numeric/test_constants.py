from __future__ import absolute_import, print_function

from myhdl import Signal, bitarray, uintba, sintba, sfixba, always_comb, \
    instance, delay, conversion, fixmath, StopSimulation


def constants(t, v, u, x, y, z, a, s):
    b = Signal(bool(0))
    c = Signal(bool(1))
    d = Signal(uintba(5, 8))
    e = Signal(sintba(4, 6))
    f = Signal(sfixba(3.5, 8, -8))
    g = [Signal(sfixba(i/3.14159, 7, -15)) for i in range(8)]
    h = Signal(bitarray(0, len(f), 0))
    j = Signal(bitarray(0, high=1, low=0))

    @always_comb
    def logic():
        t.next = f
        u.next = d
        v.next = e
        x.next = b
        y.next = c
        z.next = a
        h.next = f.scalb(-f.low)
        j.next[0] = b
        for i in range(len(g)):
            s[i].next = g[i]

    return logic


x, y, z, a = [Signal(bool(0)) for _ in range(4)]
t = Signal(sfixba(0, 8, -8))
u = Signal(uintba(0, 8))
v = Signal(sintba(0, 6))
s = g = [Signal(sfixba(0, 7, -15)) for _ in range(8)]


def test_constants():
    assert conversion.analyze(constants, t, v, u, x, y, z, a, s) == 0


def sfixba_constant():
    v = 511.5
    h = Signal(sfixba(v))

    @instance
    def logic():
        yield delay(10)
        assert h == v
        print(h)

    return logic


def test_sfixba_constant():
    assert conversion.verify(sfixba_constant) == 0


def sfixba_resize():
    fmath = fixmath(fixmath.overflows.saturate, fixmath.roundings.round)
    v = Signal(sfixba(-0.00048828125, 17, -16, fmath))
    w = Signal(sfixba(-0.00048828125, fmath))
    h = Signal(sfixba(0, 8, -8, fmath))

    @instance
    def logic():
        yield delay(10)
        h.next = v
        yield delay(10)
        assert h == 0
        print("%s, %s" % (h, v))
        yield delay(10)
        h.next = w
        yield delay(10)
        assert h == 0
        print("%s, %s" % (h, w))

    return logic


def test_sfixba_resize():
    assert conversion.verify(sfixba_resize) == 0


def bitarray_constants():
    v = Signal(bitarray(0, 15, 0))
    w = Signal(bitarray(0, 16, low=0))
    h = Signal(bitarray(0, 14, 0))
    i = Signal(bitarray(0, 32, 0))
    data = 3913087651
    @instance
    def logic():
        yield delay(10)
        h.next = v[h.high:]
        i.next = uintba(data, 32)
        yield delay(10)
        assert h == uintba(0)
        assert i == uintba(data, 32)
        print("%s, %s" % (h, v))
        yield delay(10)
        h.next = w[h.high:]
        yield delay(10)
        assert h == uintba(0)
        print("%s, %s" % (h, w))
        yield delay(10)
        w.next[0] = 1
        v.next = sfixba(0.1, 7, -8).scalb(8)
        h.next = uintba(3)
        yield delay(10)
        print(w, v, h)
        yield delay(10)
        raise StopSimulation

    return logic


def test_bitarray_constants():
    assert conversion.verify(bitarray_constants) == 0
