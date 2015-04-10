from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
import os
path = os.path
import random
from random import randrange
import unittest
random.seed(2)

from myhdl import *
from myhdl.conversion import verify

NRTESTS = 10

def functionCheck(delta, i, j):
    values = tuple(range(-128, 128))
    f_value = Signal(sfixba(0, 2, 0))
    fs_value = Signal(sfixba(0, f_value.high + delta, f_value.low + delta))
    value = Signal(sfixba(0, i, j))
    
    @instance
    def generate():
        for i in range(len(values)):
            yield delay(10)
            i_value = values[i]
            si_value = sfixba(i_value, 8, -3)
            sis_value = si_value.resize(8, 0)
            f_value.next = sis_value
            #f_value.next = sfixba(i_value)
            yield delay(10)
            tmp = f_value.scalb(-5)
            fs_value.next = tmp
            yield delay(10)
            value.next = fs_value
            yield delay(10)
            print(i_value, f_value, fs_value, value)
    
    return generate

def binaryOps(
              Bitand,
              Bitor,
              Bitxor,
              FloorDiv,
              #TrueDiv,
              LeftShift,
              Modulo,
              Mul,
              Pow,
              RightShift,
              Sub,
              Sum,
              EQ,
              NE,
              LT,
              GT,
              LE,
              GE,
              Booland,
              Boolor,
              left, right):

    @instance
    def logic():
        while 1:
            yield left, right
            Bitand.next = left & right
            Bitor.next = left | right
            Bitxor.next = left ^ right
            if right != 0:
                FloorDiv.next = left // right
            else:
                FloorDiv.next = 0
                #TrueDiv.next = left / right
    ##         if left < 256 and right < 40:
            if right >= 0 and right < 16: # fails in ghdl for > 26
                LeftShift.next = left.resize(LeftShift) << int(right)
            else:
                LeftShift.next = 0
            if right != 0:
                Modulo.next = left % right
            else:
                Modulo.next = 0
            Mul.next = left * right
            # Icarus doesn't support ** yet
            #if left < 256 and right < 40:
            #    Pow.next = left ** right
    ##         Pow.next = 0
            if right >= 0:
                RightShift.next = left >> int(right)
            else:
                RightShift.next = 0
            #if left >= right:
            Sub.next = left - right
            Sum.next = left + right
            EQ.next = left == right
            NE.next = left != right
            LT.next = left < right
            GT.next = left > right
            LE.next = left <= right
            GE.next = left >= right
            Booland.next = bool(left) and bool(right)
            Boolor.next = bool(left) or bool(right)
    return logic


def binaryBench(l, r):
    tmp_i = 10
    tmp_si = sfixba(tmp_i)
    tmp_sis = tmp_si.scalb(-1)

    M = 2**(l.high - l.low - 1)
    N = 2**(r.high - r.low - 1)
    P = min(M, N)

    seqP = tuple(range(P))
    seqM = tuple([randrange(M) for i in range(NRTESTS)])
    seqN = tuple([randrange(N) for i in range(NRTESTS)])

    left = Signal(l)
    right = Signal(r)
    Bitand = Signal(l & r)
    Bitor = Signal(l | r)
    Bitxor = Signal(l ^ r)
    FloorDiv = Signal(l // r)
    #TrueDiv = Signal(l / r)
    LeftShift = Signal(left.resize(left.high * 8, left.low * 8))
    Modulo = Signal(l % r)
    Mul = Signal(l * r)
    Pow = Signal(left.resize(64))
    RightShift = Signal(l)
    Sub = Signal(l - r)
    Sum = Signal(l + r)
    EQ, NE, LT, GT, LE, GE = [Signal(bool()) for i in range(6)]
    Booland, Boolor = [Signal(bool()) for i in range(2)]

    binops = binaryOps(Bitand,
                       Bitor,
                       Bitxor,
                       FloorDiv,
                       #TrueDiv,
                       LeftShift,
                       Modulo,
                       Mul,
                       Pow,
                       RightShift,
                       Sub,
                       Sum,
                       EQ,
                       NE,
                       LT,
                       GT,
                       LE,
                       GE,
                       Booland,
                       Boolor,
                       left, right)

    @instance
    def stimulus():
        tmpi = 10
        tmpsi = sfixba(tmp_i)
        tmpsis = tmpsi.scalb(-1)
        left.next = tmpsis
        right.next = tmpsis
        yield delay(10)
#         left.next = 1
#         right.next = 1
#         yield delay(10)
#         left.next = 0
#         right.next = 0
#         yield delay(10)
#         left.next[:] = 0
#         right.next = N-1
#         yield delay(10)
#         left.next = M-1
#         right.next[:] = 0
#         yield delay(10)
#         left.next = M-1
#         right.next = N-1
#         for i in range(len(seqP)):
#             left.next = sfixed(seqP[i]).scalb(left.low)
#             right.next = seqP[i]
#             yield delay(10)
#         for i in range(NRTESTS):
#             tmpM = seqM[i]
#             l_low = left.low
#             tmp_sm = sfixba(tmpM)
#             print(tmp_sm)
#             tmp_sms = tmp_sm.scalb(l_low)
#             left.next = tmp_sms
#             tmpN = seqN[i]
#             r_low = right.low
#             tmp_sn = sfixba(tmpN)
#             print(tmp_sn)
#             tmp_sns = tmp_sn.scalb(r_low)
#             right.next = tmp_sns
#             yield delay(10)
        # raise StopSimulation


    @instance
    def check():
        while True:
            yield left, right
            yield delay(1)

            print("left: ", left)
            print("right: ", right)
            print("and: ", left, right, Bitand)
            print("or: ", left, right, Bitor)
            print("xor: ", left, right, Bitxor)
            #print(TrueDiv)
            print("<<: ", left, right, LeftShift)

            # print Pow, Pow_v

            print(">>: ", left, right, RightShift)
            print("+: ", left, right, Sum)
            print("-: ", left, right, Sub)
            print("//: ", left, right, FloorDiv)
            print("%: ", left, right, Modulo)
            print("*: ", left, right, Mul)
            print("==: ", left, right, int(EQ))
            print("!=: ", left, right, int(NE))
            print("<: ", left, right, int(LT))
            print(">: ", left, right, int(GT))
            print("<=: ", left, right, int(LE))
            print(">=: ", left, right, int(GE))
            print("bool_and: ", int(Booland))
            print("bool_or: ", int(Boolor))

    return binops, stimulus, check

def checkBinary(m, n):
    assert verify(binaryBench, m, n) == 0

def multiOps(
              Bitand,
              Bitor,
              Bitxor,
              Booland,
              Boolor,
              argm, argn, argp):
    @instance
    def logic():
        while 1:
            yield argm, argn, argp
            Bitand.next = argm & argn & argp
            Bitor.next = argm | argn | argp
            Bitxor.next = argm ^ argn ^ argp
            Booland.next = bool(argm) and bool(argn) and bool(argp)
            Boolor.next = bool(argm) and bool(argn) and bool(argp)
    return logic


def multiBench(m, n, p):

    M = 2**m
    N = 2**n
    P = 2**p

    Q = min(M, N, P)
    seqQ = tuple(range(1, Q))
    seqM = tuple([randrange(M) for i in range(NRTESTS)])
    seqN = tuple([randrange(N) for i in range(NRTESTS)])
    seqP = tuple([randrange(P) for i in range(NRTESTS)])

    argm = Signal(intbv(0)[m:])
    argn = Signal(intbv(0)[n:])
    argp = Signal(intbv(0)[p:])
    Bitand = Signal(intbv(0)[max(m, n, p):])
    Bitor = Signal(intbv(0)[max(m, n, p):])
    Bitxor = Signal(intbv(0)[max(m, n, p):])
    Booland, Boolor = [Signal(bool()) for i in range(2)]

    multiops = multiOps(Bitand,
                        Bitor,
                        Bitxor,
                        Booland,
                        Boolor,
                        argm, argn, argp)

    @instance
    def stimulus():
        for i in range(len(seqQ)):
            argm.next = seqQ[i]
            argn.next = seqQ[i]
            argp.next = seqQ[i]
            yield delay(10)
        for i in range(NRTESTS):
            argm.next = seqM[i]
            argn.next = seqN[i]
            argp.next = seqP[i]
            yield delay(10)
##         for j, k, l in ((0, 0, 0),   (0, 0, P-1), (0, N-1, P-1),
##                         (M-1, 0, 0),  (M-1, 0, P-1), (M-1, N-1, 0),
##                         (0, N-1, 0), (M-1, N-1, P-1)):
##             argm.next = j
##             argn.next = k
##             argp.next = l
##             yield delay(10)

    @instance
    def check():
        while 1:
            yield argm, argn, argp
            yield delay(1)

            print(Bitand)
            print(Bitor)
            print(Bitxor)
            print(int(Booland))
            print(int(Boolor))

    return multiops, stimulus, check

def checkMultiOps(m, n, p):
    assert verify(multiBench, m, n, p) == 0

def testMultiOps():
    for m, n, p in ((4, 4, 4,), (5, 3, 2), (3, 4, 6), (3, 7, 4)):
        yield checkMultiOps, m, n, p


def unaryOps(
             Not_kw,
             Invert,
             UnaryAdd,
             UnarySub,
             arg):
    @instance
    def logic():
        while 1:
            yield arg
            Not_kw.next = not arg
            Invert.next = ~arg
            # unary operators not supported ?
            #UnaryAdd.next = +arg
            # UnarySub.next = --arg
    return logic

def unaryBench(m):

    M = 2**m
    seqM = tuple([randrange(M) for i in range(NRTESTS)])

    arg = Signal(intbv(0)[m:])
    Not_kw = Signal(bool(0))
    Invert = Signal(intbv(0)[m:])
    UnaryAdd = Signal(intbv(0)[m:])
    UnarySub = Signal(intbv(0)[m:])

    unaryops = unaryOps(Not_kw,
                        Invert,
                        UnaryAdd,
                        UnarySub,
                        arg)

    @instance
    def stimulus():
        for i in range(NRTESTS):
            arg.next = seqM[i]
            yield delay(10)
        raise StopSimulation

    @instance
    def check():
        while 1:
            yield arg
            yield delay(1)
            print(int(Not_kw))
            print(Invert)
            # check unary operator support in vhdl
            # print UnaryAdd
            # print UnarySub

    return unaryops, stimulus, check

def checkUnaryOps(m):
    assert verify(unaryBench, m) == 0
    
def testUnaryOps():
    for m in (4, 7):
        yield checkUnaryOps, m


def augmOps(  Bitand,
              Bitor,
              Bitxor,
              FloorDiv,
              LeftShift,
              Modulo,
              Mul,
              RightShift,
              Sub,
              Sum,
              left, right):
    @instance
    def logic():
        # var = intbv(0)[min(64, len(left) + len(right)):]
        var = intbv(0)[len(left) + len(right):]
        var2 = intbv(0)[64:]
        while True:
            yield left, right
            var[:] = left
            var &= right
            Bitand.next = var
            var[:] = left
            var |= right
            Bitor.next = var
            var[:] = left
            var ^= left
            Bitxor.next = var
            if right != 0:
                var[:] = left
                var //= right
                FloorDiv.next = var
            if left >= right:
                var[:] = left
                var -= right
                Sub.next = var
            var[:] = left
            var += right
            Sum.next = var
            if left < 256 and right < 26:
                var2[:] = left
                var2 <<= right
                LeftShift.next = var2
            if right != 0:
                var[:] = left
                var %= right
                Modulo.next = var
            var[:] = left
            var *= right
            Mul.next = var
            var[:] = left
            var >>= right
            RightShift.next = var
    return logic


        


def augmBench(m, n):

    M = 2**m
    N = 2**n
    
    seqM = tuple([randrange(M) for i in range(NRTESTS)])
    seqN = tuple([randrange(N) for i in range(NRTESTS)])

    left = Signal(intbv(0)[m:])
    right = Signal(intbv(0)[n:])
    Bitand = Signal(intbv(0)[max(m, n):])
    Bitor = Signal(intbv(0)[max(m, n):])
    Bitxor = Signal(intbv(0)[max(m, n):])
    FloorDiv = Signal(intbv(0)[m:])
    LeftShift = Signal(intbv(0)[64:])
    Modulo = Signal(intbv(0)[m:])
    Mul = Signal(intbv(0)[m+n:])
    RightShift = Signal(intbv(0)[m:])
    Sub = Signal(intbv(0)[max(m, n):])
    Sum = Signal(intbv(0)[max(m, n)+1:])

    augmops = augmOps( Bitand,
                       Bitor,
                       Bitxor,
                       FloorDiv,
                       LeftShift,
                       Modulo,
                       Mul,
                       RightShift,
                       Sub,
                       Sum,
                       left, right)

    @instance
    def stimulus():
        left.next = 1
        right.next = 1
        yield delay(10)
        left.next = 0
        right.next = 0
        yield delay(10)
        left.next = 0
        right.next = N-1
        yield delay(10)
        left.next = M-1
        right.next = 0
        yield delay(10)
        left.next = M-1
        right.next = N-1
        for i in range(NRTESTS):
            left.next = seqM[i]
            right.next = seqN[i]
            yield delay(10)
            

    @instance
    def check():
        while True:
            yield left, right
            yield delay(1)
            print(left, right)
            print(Bitand)
            print(Bitor)
            print(Bitxor)
            print(Sub)
            print(Sum)
            print(FloorDiv)
            print(LeftShift)
            print(Modulo)
            print(Mul)
            print(RightShift)
            
    return augmops, stimulus, check


def checkAugmOps(m, n):
    assert verify(augmBench, m, n) == 0

def testAugmOps():
    for m, n in ((4, 4,), (5, 3), (2, 6), (8, 7)):
        yield checkAugmOps, m, n


class Test(unittest.TestCase):
#     def test_SimBinary(self):
#         self.vectors()
#         for left in self.lefts:
#             for right in self.rights:
#                 #tb_fsm = traceSignals(delayBufferTestBench)
#                 #sim = Simulation(tb_fsm)
#                 toVHDL(binaryBench, left, right)
#                 sim = Simulation(binaryBench(left, right))
#                 sim.run()

    def vectors(self):
        self.lefts = (#uintba(9, 8),
                      #sintba(10, 6),
                      #sintba(-10, 8),
                      sfixba(20, 9, -4),
                      sfixba(-13, 10, -3))
        self.rights = (#uintba(3, 4),
                       #sintba(9, 8),
                       #sintba(-10, 5),
                       sfixba(1, 4, 0),
                       sfixba(13, 12, 3),)

#     def test_Binary(self):
#         self.vectors()
#         for left in self.lefts:
#             for right in self.rights:
#                 self.assertEqual(conversion.verify(binaryBench, left, right), 0)
            
    def testSimFunctions(self):
        #tb_fsm = traceSignals(functionCheck)
        #sim = Simulation(tb_fsm)
        toVHDL(functionCheck, 0, 3, 0)
        sim = Simulation(functionCheck(0, 3, 0))
        sim.run()

#     def testFunctions(self):
#         for delta in range(-5, 0):
#             for i in range(0, 8):
#                 for j in range(delta, i-1):
#                     self.assertEqual(conversion.verify(functionCheck,
#                                                        delta, i, j), 0)

        
if __name__ == "__main__":
    unittest.main()
