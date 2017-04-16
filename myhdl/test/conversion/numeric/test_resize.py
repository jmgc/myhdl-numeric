from __future__ import absolute_import, print_function

from myhdl import Signal, uintba, sintba, sfixba, always_comb, \
    instance, delay, conversion, fixmath


def sfixba_resize_sfixba():
    fmath = fixmath(fixmath.overflows.saturate, fixmath.roundings.round)
    v = Signal(sfixba(-0.00048828125, 17, -16, fmath))
    w = Signal(sfixba(-0.00048828125, fmath))
    h = Signal(sfixba(0, 8, -8, fmath))
    i = Signal(uintba(3, 2))
    j = Signal(sfixba(-1.5, 2, -2))
    k = Signal(sintba(-1, 4))
    t = Signal(i & j)
    u = Signal(t & k)
    s = Signal(i & j & k)

    @instance
    def logic():
        yield delay(10)
        h.next = w.resize(v)
        yield delay(10)
        assert h == 0
        print("%s, %s" % (h, v))
        yield delay(10)
        h.next = w
        yield delay(10)
        assert h == 0
        print("%s, %s" % (h, w))
        yield delay(10)
        t.next = i & j
        yield delay(10)
        u.next = t & k
        s.next = i & j & k
        yield delay(10)
        assert u == -2
        print("%s, %s, %s, %s, %s, %s" % (i, j, t, k, u, s))

    return logic


def test_sfixba_resize_sfixba():
    assert conversion.verify(sfixba_resize_sfixba) == 0
