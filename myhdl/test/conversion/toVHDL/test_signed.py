from __future__ import absolute_import, print_function

from myhdl import instance, Signal, intbv, delay, StopSimulation
from myhdl.conversion import verify
from random import randrange
import pytest

NRTESTS = 10


def binaryOps(Bitand,
              LeftShift,
              Modulo,
              Mul,
              RightShift,
              Sub,
              Sum, Sum1, Sum2, Sum3,
              EQ,
              NE,
              LT,
              GT,
              LE,
              GE,
              BoolAnd,
              BoolOr,
              left, right, aBit):

    @instance
    def logic():
        while 1:
            yield left, right, aBit
            # Keep left shifts smaller than 2** 31 for VHDL's to_integer
            if left < 256 and right < 22 and right >= 0:
                LeftShift.next = left << right
            Mul.next = left * right
            Sub.next = left - right
            Sum.next = left + right
            Sum1.next = left + right[2:]
            Sum2.next = left + right[1]
            Sum3.next = left + aBit
            EQ.next = left == right
            NE.next = left != right
            LT.next = left < right
            GT.next = left > right
            LE.next = left <= right
            GE.next = left >= right
            BoolAnd.next = bool(left) and bool(right)
            BoolOr.next = bool(left) or bool(right)
    return logic


def binaryBench(Ll, Ml, Lr, Mr):
    seqL = []
    seqR = []
    for _ in range(NRTESTS):
        seqL.append(randrange(Ll, Ml))
        seqR.append(randrange(Lr, Mr))
    for j, k in ((Ll, Lr), (Ml-1, Mr-1), (Ll, Mr-1), (Ml-1, Lr)):
        seqL.append(j)
        seqR.append(k)
    seqL = tuple(seqL)
    seqR = tuple(seqR)

    aBit = Signal(bool(0))
    left = Signal(intbv(Ll, min=Ll, max=Ml))
    right = Signal(intbv(Lr, min=Lr, max=Mr))
    M = 2**14

    Bitand = Signal(intbv(0, min=-2**17, max=2**17))
    LeftShift = Signal(intbv(0, min=-2**64, max=2**64))
    Modulo = Signal(intbv(0)[M:])
    Mul = Signal(intbv(0, min=-2**17, max=2**17))
    RightShift = Signal(intbv(0, min=-M, max=M))
    Sub, Sub1, Sub2, Sub3 = [Signal(intbv(min=-M, max=M)) for _ in range(4)]
    Sum, Sum1, Sum2, Sum3 = [Signal(intbv(min=-M, max=M)) for _ in range(4)]
    EQ, NE, LT, GT, LE, GE = [Signal(bool()) for i in range(6)]
    BoolAnd, BoolOr = [Signal(bool()) for i in range(2)]

    binops = binaryOps(
        Bitand,
        LeftShift,
        Modulo,
        Mul,
        RightShift,
        Sub,
        Sum, Sum1, Sum2, Sum3,
        EQ,
        NE,
        LT,
        GT,
        LE,
        GE,
        BoolAnd,
        BoolOr,
        left, right, aBit)

    @instance
    def stimulus():
        for i in range(len(seqL)):
            left.next = seqL[i]
            right.next = seqR[i]
            yield delay(10)

    @instance
    def check():
        while True:
            yield left, right
            aBit.next = not aBit
            yield delay(1)
            print(int(left), "<<", int(right), "=", int(LeftShift))
            print(int(left), "*", int(right), "=", int(Mul))
            print(int(left), ">>", int(right), "=", int(RightShift))
            print(int(left), "-", int(right), "=", int(Sub))
            print(int(left), "+(0)", int(right), "=", int(Sum))
            print(int(left), "+(1)", int(right), "=", int(Sum1))
            print(int(left), "+(2)", int(right), "=", int(Sum2))
            print(int(left), "+(3)", int(right), "=", int(Sum3))
            print(int(left), "==", int(right), "=", int(EQ))
            print(int(left), "!=", int(right), "=", int(NE))
            print(int(left), "<", int(right), "=", int(LT))
            print(int(left), ">", int(right), "=", int(GT))
            print(int(left), "<=", int(right), "=", int(LE))
            print(int(left), ">=", int(right), "=", int(GE))
            print(int(left), "and", int(right), "=", int(BoolAnd))
            print(int(left), "or", int(right), "=", int(BoolOr))

    return binops, stimulus, check


@pytest.mark.parametrize("Ll, Ml, Lr, Mr", [
    (-254, 236, 0, 4),
    (-128, 128, -128, 128),
    (-53, 25, -23, 123),
    (-23, 145, -66, 12),
    (23, 34, -34, -16),
    (-54, -20, 45, 73),
    (-25, -12, -123, -66),
])
def testBinaryOps(Ll, Ml, Lr, Mr):
    assert verify(binaryBench, Ll, Ml, Lr, Mr) == 0


def unaryOps(BoolNot,
             Invert,
             UnaryAdd,
             UnarySub,
             arg):

    @instance
    def logic():
        while 1:
            yield arg
            Invert.next = ~arg
            UnarySub.next = --arg
    return logic


def unaryBench(m):
    M = 2**m
    seqM = tuple([i for i in range(-M, M)])

    arg = Signal(intbv(0, min=-M, max=+M))
    BoolNot = Signal(bool(0))
    Invert = Signal(intbv(0, min=-M, max=+M))
    UnaryAdd = Signal(intbv(0, min=-M, max=+M))
    UnarySub = Signal(intbv(0, min=-M, max=+M))

    unaryops = unaryOps(BoolNot,
                        Invert,
                        UnaryAdd,
                        UnarySub,
                        arg)

    @instance
    def stimulus():
        for i in range(len(seqM)):
            arg.next = seqM[i]
            yield delay(10)
        raise StopSimulation

    @instance
    def check():
        while 1:
            yield arg
            yield delay(1)
            print(int(Invert))
            print(int(UnarySub))

    return unaryops, stimulus, check


@pytest.mark.parametrize("m", [
    4,
    7,
])
def testUnaryOps(m):
    assert verify(unaryBench, m) == 0


def augmOps(LeftShift,
            Mul,
            RightShift,
            Sub,
            Sum,
            left, right):

    M = 2**17
    N = 2**64

    @instance
    def logic():
        var = intbv(0, min=-M, max=+M)
        var2 = intbv(0, min=-N, max=+N)
        while 1:
            yield left, right
            if left < 256 and right < 22 and right >= 0:
                var2[:] = left
                var2 <<= right
                LeftShift.next = var2
            var[:] = left
            var *= right
            Mul.next = var

            var[:] = left
            if right >= 0:
                var >>= right
                RightShift.next = var

            var[:] = left
            var -= right
            Sub.next = var
            var[:] = left
            var += right
            Sum.next = var

    return logic


def augmBench(Ll, Ml, Lr, Mr):
    M = 2**17

    seqL = []
    seqR = []
    for i in range(NRTESTS):
        seqL.append(randrange(Ll, Ml))
        seqR.append(randrange(Lr, Mr))
    for j, k in ((Ll, Lr), (Ml-1, Mr-1), (Ll, Mr-1), (Ml-1, Lr)):
        seqL.append(j)
        seqR.append(k)
    seqL = tuple(seqL)
    seqR = tuple(seqR)
    left = Signal(intbv(Ll, min=Ll, max=Ml))
    right = Signal(intbv(Lr, min=Lr, max=Mr))
    LeftShift = Signal(intbv(0, min=-2**64, max=2**64))
    Mul = Signal(intbv(0, min=-M, max=+M))
    RightShift = Signal(intbv(0, min=-M, max=+M))
    Sub = Signal(intbv(0, min=-M, max=+M))
    Sum = Signal(intbv(0, min=-M, max=+M))

    augmops = augmOps(LeftShift,
                      Mul,
                      RightShift,
                      Sub,
                      Sum,
                      left, right)

    @instance
    def stimulus():
        for i in range(len(seqL)):
            left.next = seqL[i]
            right.next = seqR[i]
            yield delay(10)

    @instance
    def check():
        while 1:
            yield left, right
            yield delay(1)
            print(int(LeftShift))
            print(int(Mul))
            print(int(RightShift))
            print(int(Sub))
            print(int(Sum))

    return augmops,  stimulus, check


@pytest.mark.parametrize("Ll, Ml, Lr, Mr", [
    (-254, 236, 0, 4),
    (-128, 128, -128, 128),
    (-53, 25, -23, 123),
    (-23, 145, -66, 12),
    (23, 34, -34, -16),
    (-54, -20, 45, 73),
    (-25, -12, -123, -66),
])
def testAugmOps(Ll, Ml, Lr, Mr):
    assert verify(augmBench, Ll, Ml, Lr, Mr) == 0


def expressions(a, b, clk):
    c = Signal(intbv(0, min=0, max=47))
    e = Signal(bool())

    @instance
    def logic():
        d = intbv(0, min=-23, max=43)
        d[:] = -17

        c.next = 5
        yield clk.posedge
        a.next = c + 1
        b.next = c + 1
        yield clk.posedge
        a.next = c + -10
        b.next = c + -1
        yield clk.posedge
        a.next = c < -10
        b.next = c < -1
        yield clk.posedge
        a.next = d + c
        b.next = d >= c
        yield clk.posedge
        yield clk.posedge
        a.next = d + -c
        b.next = c + (-d)
        yield clk.posedge
        a.next = -d
        yield clk.posedge
        a.next = -c
        yield clk.posedge
        c.next = 46
        yield clk.posedge
        a.next = ~d + 1
        b.next = ~c + 1
        yield clk.posedge
        a.next = ~c + 1
        b.next = ~d + 1
        yield clk.posedge
        raise StopSimulation

    return logic


def expressionsBench():
    a = Signal(intbv(0, min=-34, max=47))
    b = Signal(intbv(0, min=0, max=47))
    clk = Signal(bool())

    expr = expressions(a, b, clk)

    @instance
    def check():
        while 1:
            yield clk.posedge
            yield delay(1)
            print(int(a))
            print(int(b))

    @instance
    def clkgen():
        while True:
            yield delay(10)
            clk.next = not clk

    return expr, check, clkgen


def testExpressions():
    assert verify(expressionsBench) == 0
