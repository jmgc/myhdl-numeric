from __future__ import absolute_import, print_function

from myhdl import *

zero = 0
one = 1
two = 2
three = 3


def map_if4(z, a):

    @always_comb
    def logic():
        if a == zero:
            z.next = 0
        elif a == one:
            z.next = 1
        elif a == two:
            z.next = 2
        else:
            z.next = 3

    return logic


def map_if2(z, a):

    @always_comb
    def logic():
        z.next = 0
        if a == zero:
            z.next = 0
        elif a == one:
            z.next = 1

    return logic


def map_if3(z, a):

    @always_comb
    def logic():
        if a == zero:
            z.next = 0
        elif a == one:
            z.next = 1
        else:
            z.next = 2

    return logic


def map_if4_full(z, a):

    @always_comb
    def logic():
        if a == zero:
            z.next = 0
        elif a == one:
            z.next = 1
        elif a == two:
            z.next = 2
        elif a == three:
            z.next = 3

    return logic


def map_if5(z, a):

    @always_comb
    def logic():
        if a == zero:
            z.next = 0
        elif a in (one, two):
            z.next = 1
        elif a == three:
            z.next = 3

    return logic


def map_if6(z, a):

    @always_comb
    def logic():
        if a == zero:
            z.next = 0
        elif a in (one, two):
            z.next = 1
        else:
            z.next = 3

    return logic


def map_if7(z, a):

    @always_comb
    def logic():
        z.next = 3
        if a == zero:
            z.next = 0
        elif a in (one, two):
            z.next = 1

    return logic


def bench_if(map_case, N):

    a = Signal(intbv(0)[2:])
    z = Signal(intbv(0)[2:])

    inst = map_case(z, a)

    @instance
    def stimulus():
        for i in range(N):
            a.next = i
            yield delay(10)
            print(int(z))

    return stimulus, inst


def test_if4():
    assert conversion.verify(bench_if, map_if4, 4) == 0


def test_if2():
    assert conversion.verify(bench_if, map_if2, 2) == 0


def test_if3():
    assert conversion.verify(bench_if, map_if3, 3) == 0


def test_if4_full():
    assert conversion.verify(bench_if, map_if4_full, 4) == 0


def test_if5():
    assert conversion.verify(bench_if, map_if5, 4) == 0


def test_if6():
    assert conversion.verify(bench_if, map_if6, 4) == 0


def test_if7():
    assert conversion.verify(bench_if, map_if7, 4) == 0
