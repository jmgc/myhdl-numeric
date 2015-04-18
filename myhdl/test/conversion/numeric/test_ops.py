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

def resizeCheck(delta, i, j):
    values = tuple(range(-128, 128))
    f_value = Signal(sfixba(0, 2, 0))
    fs_value = Signal(sfixba(0, f_value.high + delta, f_value.low + delta))
    value = Signal(sfixba(0, i, j))
    
    @instance
    def generate():
        for i in range(len(values)):
            yield delay(10)
            i_value = values[i]
            f_value.next = sfixba(i_value)
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
              # TrueDiv,
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
            if right >= 0 and right < 16:  # fails in ghdl for > 26
                LeftShift.next = left.resize(LeftShift) << int(right)
            else:
                LeftShift.next = 0
            if right != 0:
                Modulo.next = left % right
            else:
                Modulo.next = 0
            Mul.next = left * right
            if right >= 0:
                RightShift.next = left >> int(right)
            else:
                RightShift.next = 0
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
    maxP = min(l.max, r.max)
    minP = max(l.min, r.min)

    if l.is_signed:
        lv = (l.min, 0, l.max - 1)
    else:
        lv = (0, l.max - 1)
    if r.is_signed:
        rv = (r.min, 0, r.max - 1)
    else:
        rv = (0, r.max - 1)
    seqP = tuple(range(minP, maxP))
    seqM = tuple([randrange(l.min, l.max - 1) for i in range(NRTESTS)])
    seqN = tuple([randrange(r.min, r.max - 1) for i in range(NRTESTS)])

    left = Signal(l)
    right = Signal(r)
    Bitand = Signal(l & r)
    Bitor = Signal(l | r)
    Bitxor = Signal(l ^ r)
    FloorDiv = Signal(l // r)
    LeftShift = Signal(l.resize(l.high * 8, l.low * 8))
    Modulo = Signal(l % r)
    Mul = Signal(l * r)
    Pow = Signal(l.resize(l.high * 8, l.low * 8))
    RightShift = Signal(l)
    Sub = Signal(l - r)
    Sum = Signal(l + r)
    EQ, NE, LT, GT, LE, GE = [Signal(bool()) for i in range(6)]
    Booland, Boolor = [Signal(bool()) for i in range(2)]

    high = max(left.high - left.low, right.high - right.low)
    low = 0

    binops = binaryOps(Bitand,
                       Bitor,
                       Bitxor,
                       FloorDiv,
                       # TrueDiv,
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
        left.next[:] = 1
        right.next[:] = 1
        yield delay(10)
        for i in range(len(lv)):
            for j in range(len(rv)):
                left.next[:] = lv[i]
                right.next[:] = rv[j]
                yield delay(10)
        for i in range(len(seqP)):
            tmpP = seqP[i]
            left.next[:] = tmpP
            right.next[:] = tmpP
            yield delay(10)
        for i in range(NRTESTS):
            tmpM = seqM[i]
            left.next[:] = tmpM
            tmpN = seqN[i]
            right.next[:] = tmpN
            yield delay(10)
        # raise StopSimulation


    @instance
    def check():
        count = 0
        while True:
            yield left, right
            yield delay(1)
            print("count: ", count)
            print("left: ", left)
            print("right: ", right)
            print("and: ", left, right, Bitand)
            print("or: ", left, right, Bitor)
            print("xor: ", left, right, Bitxor)
            print("<<: ", left, right, LeftShift)
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
    
            count = count + 1

    return binops, stimulus, check

def divOp(TrueDiv,
          left, right):

    @instance
    def logic():
        while 1:
            yield left, right
            if right != 0:
                TrueDiv.next = left / right
            else:
                TrueDiv.next = 0
    return logic


def divBench(l, r):
    maxP = min(l.max, r.max)
    minP = max(l.min, r.min)

    if l.is_signed:
        lv = (l.min, 0, l.max - 1)
    else:
        lv = (0, l.max - 1)
    if r.is_signed:
        rv = (r.min, -1, 1, r.max - 1)
    else:
        rv = (1, r.max - 1)
    seqP = tuple(range(minP, maxP))
    seqM = tuple([randrange(l.max - l.min) + l.min for i in range(NRTESTS)])
    seqN = tuple([randrange(r.max - r.min) + r.min for i in range(NRTESTS)])

    left = Signal(l)
    right = Signal(r)
    TrueDiv = Signal(l / r)

    high = max(left.high - left.low, right.high - right.low)
    low = 0

    divop = divOp(TrueDiv,
                       left, right)

    @instance
    def stimulus():
        left.next[:] = 1
        right.next[:] = 1
        yield delay(10)
        for i in range(len(lv)):
            for j in range(len(rv)):
                left.next[:] = lv[i]
                right.next[:] = rv[j]
                yield delay(10)
        yield delay(10)
        for i in range(len(seqP)):
            left.next[:] = seqP[i]
            right.next[:] = seqP[i]
            yield delay(10)
        for i in range(NRTESTS):
            left.next[:] = seqM[i]
            right.next[:] = seqN[i]
            yield delay(10)
        # raise StopSimulation


    @instance
    def check():
        count = 0
        while True:
            yield left, right
            yield delay(1)
            print("count: ", count)
            print("left: ", left)
            print("right: ", right)
            print("/:", left, right, TrueDiv)
            count = count + 1

    return divop, stimulus, check

def checkDiv(m, n):
    assert verify(divBench, m, n) == 0

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

    Q = min(m.max, n.max, p.max)
    seqQ = tuple(range(1, Q))
    seqM = tuple([randrange(m.min, m.max) for i in range(NRTESTS)])
    seqN = tuple([randrange(n.min, n.max) for i in range(NRTESTS)])
    seqP = tuple([randrange(p.min, p.max) for i in range(NRTESTS)])
    
    if m.is_signed:
        mv = (m.min, 0, m.max - 1)
    else:
        mv = (0, m.max - 1)
    if n.is_signed:
        nv = (n.min, 0, n.max - 1)
    else:
        nv = (0, n.max - 1)
    if p.is_signed:
        pv = (p.min, 0, p.max - 1)
    else:
        pv = (0, p.max - 1)

    argm = Signal(m)
    argn = Signal(n)
    argp = Signal(p)
    Bitand = Signal(m & n & p)
    Bitor = Signal(m | n | p)
    Bitxor = Signal(m ^ n ^ p)
    Booland, Boolor = [Signal(bool()) for i in range(2)]

    multiops = multiOps(Bitand,
                        Bitor,
                        Bitxor,
                        Booland,
                        Boolor,
                        argm, argn, argp)

    @instance
    def stimulus():
        argm.next[:] = 1
        argn.next[:] = 1
        argp.next[:] = 1
        yield delay(10)
        for j in range(len(mv)):
            for k in range(len(nv)):
                for l in range(len(pv)):
                    argm.next[:] = mv[j]
                    argn.next[:] = nv[k]
                    argp.next[:] = pv[l]
                    yield delay(10)
        for i in range(len(seqQ)):
            argm.next[:] = seqQ[i]
            argn.next[:] = seqQ[i]
            argp.next[:] = seqQ[i]
            yield delay(10)
        for i in range(NRTESTS):
            argm.next[:] = seqM[i]
            argn.next[:] = seqN[i]
            argp.next[:] = seqP[i]
            yield delay(10)

    @instance
    def check():
        while 1:
            yield argm, argn, argp
            yield delay(1)
            print("args: ", argm, argn, argp)
            print("&: ", Bitand)
            print("1: ", Bitor)
            print("^: ", Bitxor)
            print("and: ", int(Booland))
            print("or:", int(Boolor))

    return multiops, stimulus, check

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
            UnaryAdd.next = +arg
            if arg.is_signed:
                UnarySub.next = -arg
            else:
                UnarySub.next = 0
    return logic

def unaryBench(m):

    seqM = tuple([randrange(m.min, m.max) for i in range(NRTESTS)])

    arg = Signal(m)
    Not_kw = Signal(bool(0))
    Invert = Signal(m)
    UnaryAdd = Signal(m)
    UnarySub = Signal(m.unsigned())

    unaryops = unaryOps(Not_kw,
                        Invert,
                        UnaryAdd,
                        UnarySub,
                        arg)

    @instance
    def stimulus():
        for i in range(NRTESTS):
            arg.next[:] = seqM[i]
            yield delay(10)
        # raise StopSimulation

    @instance
    def check():
        while 1:
            yield arg
            yield delay(1)
            print("arg: ", arg)
            print("bool not: ", int(Not_kw))
            print("~: ", Invert)
            print("+: ", UnaryAdd)
            print("-: ", UnarySub)

    return unaryops, stimulus, check

def augmOps(Bitand,
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
        while True:
            yield left, right
            if left.min < 0 or right >= 0:
                var = left.val
                var &= right.val
                Bitand.next = var
                var = left.val
                var |= right.val
                Bitor.next = var
                var = left.val
                var ^= right.val
                Bitxor.next = var
                if right != 0:
                    var = left.val
                    var //= right.val
                    FloorDiv.next = var
                else:
                    FloorDiv.next = 0
                var = left.val
                var -= right.val
                Sub.next = var
                var = left.val
                var += right.val
                Sum.next = var
                if left >= left.min and left < left.max and right >= 0  and right < 26:
                    var = left.val
                    var <<= int(right.val)
                    LeftShift.next = var
                else:
                    LeftShift.next = 0
                if right != 0:
                    var = left.val
                    var %= right.val
                    Modulo.next = var
                else:
                    Modulo.next = 0
                var = left.val
                var *= right.val
                Mul.next = var
                if right >= 0  and right < 26:
                    var = left.val
                    var >>= int(right.val)
                    RightShift.next = var
                else:
                    RightShift.next = 0
    return logic


        

def augmBench(l, r):
    maxP = min(l.max, r.max)
    minP = max(l.min, r.min)

    if l.is_signed:
        lv = (l.min, 0, l.max - 1)
    else:
        lv = (0, l.max - 1)
    if r.is_signed:
        rv = (r.min, 0, r.max - 1)
    else:
        rv = (0, r.max - 1)
    seqM = tuple([randrange(l.min, l.max) for i in range(NRTESTS)])
    seqN = tuple([randrange(r.min, r.max) for i in range(NRTESTS)])

    left = Signal(l)
    right = Signal(r)
    Bitand = Signal(l)
    Bitor = Signal(l)
    Bitxor = Signal(l)
    FloorDiv = Signal(l)
    LeftShift = Signal(l)
    Modulo = Signal(l)
    Mul = Signal(l)
    RightShift = Signal(l)
    Sub = Signal(l)
    Sum = Signal(l)

    augmops = augmOps(Bitand,
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
        left.next[:] = 1
        right.next[:] = 1
        yield delay(10)
        for i in range(len(lv)):
            for j in range(len(rv)):
                left.next[:] = lv[i]
                right.next[:] = rv[j]
                yield delay(10)
        for i in range(NRTESTS):
            left.next[:] = seqM[i]
            tmpN = seqN[i]
            right.next[:] = seqN[i]
            yield delay(10)            

    @instance
    def check():
        count = 0
        while True:
            yield left, right
            yield delay(1)
            print("count: ", count)
            print("left: ", left)
            print("right: ", right)
            print("and: ", left, right, Bitand)
            print("or: ", left, right, Bitor)
            print("xor: ", left, right, Bitxor)
            print("<<: ", left, right, LeftShift)
            print(">>: ", left, right, RightShift)
            print("+: ", left, right, Sum)
            print("-: ", left, right, Sub)
            print("//: ", left, right, FloorDiv)
            print("%: ", left, right, Modulo)
            print("*: ", left, right, Mul)

            count = count + 1
            
    return augmops, stimulus, check



class Test(unittest.TestCase):
    select_test ={'augmented': True,
                  'binary': True,
                  'division': True,
                  'resize': True,
                  'multi': True,
                  'unary': True
                  }
    sim = False

    def vectors(self):
        self.lefts = (uintba(0, 8),
                      sintba(0, 6),
                      sintba(0, 3),
                      sfixba(0, 2, -4),
                      sfixba(0, 5, 2),
                      )
        self.rights = (uintba(1, 4),
                       sintba(1, 4),
                       sintba(1, 5),
                       sfixba(1, 4, 0),
                       sfixba(1, 7, 3),
                       )

    def div_vectors(self):
        self.lefts = (sfixba(0, 9, -4),
                      sfixba(0, 5, -3),
                      sfixba(0, 5, 1),
                      )
        self.rights = (sfixba(1, 4, 0),
                       sfixba(1, 7, 3),
                       sfixba(1, 3, -3),
                       )

    def multi_vectors(self):
        self.mv = (uintba(0, 3),
                   sintba(0, 3),
                   sfixba(0, 5, 2),
                   )
        self.nv = (uintba(0, 4),
                   sintba(0, 4),
                   sfixba(0, 3, -3),
                   )
        self.pv = (uintba(0, 3),
                   sintba(0, 4),
                   sfixba(0, 7, 4),
                   )

    if select_test['augmented']:
        if sim:
            def test_AugmentedSim(self):
                self.vectors()
                for left in self.lefts:
                    for right in self.rights:
                        #tb_fsm = traceSignals(delayBufferTestBench)
                        #sim = Simulation(tb_fsm)
                        toVHDL(augmBench, left, right)
                        sim = Simulation(augmBench(left, right))
                        sim.run()
        else:
            def test_AugmentedVer(self):
                self.vectors()
                for left in self.lefts:
                    for right in self.rights:
                        self.assertEqual(conversion.verify(augmBench,
                                                           left, right), 0,
                                         "Format: {0}, {1}".format(repr(left),
                                                                   repr(right)))

    if select_test['binary']:
        if sim:
            def test_BinarySim(self):
                self.vectors()
                for left in self.lefts:
                    for right in self.rights:
                        # tb_fsm = traceSignals(delayBufferTestBench)
                        # sim = Simulation(tb_fsm)
                        toVHDL(binaryBench, left, right)
                        sim = Simulation(binaryBench(left, right))
                        sim.run()
        else:
            def test_BinaryVer(self):
                self.vectors()
                for left in self.lefts:
                    for right in self.rights:
                        self.assertEqual(conversion.verify(binaryBench, left, right), 0)

    if select_test['division']:
        if sim:
            def test_DivisionSim(self):
                self.div_vectors()
                for left in self.lefts:
                    for right in self.rights:
                        # tb_fsm = traceSignals(divBench)
                        # sim = Simulation(tb_fsm)
                        toVHDL(divBench, left, right)
                        sim = Simulation(divBench(left, right))
                        sim.run()
        else:
            def test_DivisionVer(self):
                self.div_vectors()
                for left in self.lefts:
                    for right in self.rights:
                        self.assertEqual(conversion.verify(divBench, left, right), 0)

    if select_test['resize']:
        if sim:
            def testResizeSim(self):
                for delta in range(-5, 0):
                    for i in range(0, 8):
                        for j in range(delta, i - 1):
                            # tb_fsm = traceSignals(resizeCheck)
                            # sim = Simulation(tb_fsm)
                            toVHDL(resizeCheck, delta, i, j)
                            sim = Simulation(resizeCheck(delta, i, j))
                            sim.run()
        else:
            def testResizeVer(self):
                for delta in range(-5, 0):
                    for i in range(0, 8):
                        for j in range(delta, i - 1):
                            self.assertEqual(conversion.verify(resizeCheck,
                                                               delta, i, j), 0)

    if select_test['multi']:
        if sim:
            def testMultiSim(self):
                self.multi_vectors()
                for m in self.mv:
                    for n in self.mv:
                        for p in self.pv:
                            # tb_fsm = traceSignals(multiOpsBench)
                            # sim = Simulation(tb_fsm)
                            toVHDL(multiBench, m, n, p)
                            sim = Simulation(multiBench(m, n, p))
                            sim.run()
        else:
            def testMultiVer(self):
                self.multi_vectors()
                for m in self.mv:
                    for n in self.mv:
                        for p in self.pv:
                            self.assertEqual(conversion.verify(multiBench,
                                                               m, n, p), 0)
 
    if select_test['unary']:
        if sim:
            def testUnarySim(self):
                self.vectors()
                for m in self.lefts:
                    # tb_fsm = traceSignals(multiOpsBench)
                    # sim = Simulation(tb_fsm)
                    toVHDL(unaryBench, m)
                    sim = Simulation(unaryBench(m))
                    sim.run()
        else:
            def testUnaryVer(self):
                self.vectors()
                for m in self.lefts:
                    self.assertEqual(conversion.verify(unaryBench, m), 0)


if __name__ == "__main__":
    unittest.main()
