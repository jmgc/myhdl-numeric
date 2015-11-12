from __future__ import absolute_import

from myhdl import Signal, uintba, sintba, sfixba, always_comb, conversion


def constants(t, v, u, x, y, z, a, s):

    b = Signal(bool(0))
    c = Signal(bool(1))
    d = Signal(uintba(5, 8))
    e = Signal(sintba(4, 6))
    f = Signal(sfixba(3.5, 8, -8))
    g = [Signal(sfixba(i/3.14159, 7, -15)) for i in range(8)]

    @always_comb
    def logic():
        t.next = f
        u.next = d
        v.next = e
        x.next = b
        y.next = c
        z.next = a
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
