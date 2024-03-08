

from random import randrange
from myhdl import instance, downrange, intbv, Signal, delay
from myhdl.conversion import verify, analyze
from myhdl import ConversionError
from myhdl.conversion._misc import _error

import os
path = os.path


def ForLoopError1(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            for i in (1, 2, 3):
                if a[i] == 1:
                    var += 1
            result.next = var
    return logic


def ForLoopError2(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            for i in list((1, 2, 3)):
                if a[i] == 1:
                    var += 1
            result.next = var
    return logic


def ForLoop1(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            for i in downrange(len(a)):
                if a[i] == 1:
                    var += 1
            result.next = var
    return logic


def ForLoop2(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            for i in downrange(len(a), 5):
                if a[i] == 1:
                    var += 1
            result.next = var
    return logic


def ForLoop3(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            for i in downrange(len(a), 3, 2):
                if a[i] == 1:
                    var += 1
            result.next = var
    return logic


def ForLoop4(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            for i in range(len(a)):
                if a[i] == 1:
                    var += 1
            result.next = var
    return logic


def ForLoop5(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            for i in range(6, len(a)):
                if a[i] == 1:
                    var += 1
            result.next = var
    return logic


def ForLoop6(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            for i in range(5, len(a), 3):
                if a[i] == 1:
                    var += 1
            result.next = var
    return logic


def ForContinueLoop(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            for i in downrange(len(a)):
                if a[i] == 0:
                    continue
                var += 1
            result.next = var
    return logic


def ForBreakLoop(a, result):
    @instance
    def logic():
        while 1:
            yield a
            result.next = 0
            for i in downrange(len(a)):
                if a[i] == 1:
                    result.next = i
                    break
    return logic


def ForBreakContinueLoop(a, result):
    @instance
    def logic():
        while 1:
            yield a
            result.next = 0
            for i in downrange(len(a)):
                if a[i] == 0:
                    continue
                result.next = i
                break
    return logic


def NestedForLoop1(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            for i in downrange(len(a)):
                if a[i] == 0:
                    continue
                else:
                    for j in downrange(i):
                        if a[j] == 0:
                            var += 1
                    break
            result.next = var
    return logic


def NestedForLoop2(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            result.next = 0
            for i in downrange(len(a)):
                if a[i] == 0:
                    continue
                else:
                    for j in downrange(i-1):
                        if a[j] == 0:
                            pass
                        else:
                            result.next = j
                            break
                    break
    return logic


def ReturnFromFunction(a):
    for i in downrange(len(a)):
        if a[i] == 1:
            return i
    return 0


def FunctionCall(a, result):
    @instance
    def logic():
        while 1:
            yield a
            result.next = ReturnFromFunction(a)
    return logic


# During the following check, I noticed that non-blocking assignments
# are not scheduled when a task is disabled in Icarus. Apparently
# this is one of the many vague areas in the Verilog standard.
def ReturnFromTask(a, result):
    for i in downrange(len(a)):
        if a[i] == 1:
            result[:] = i
            return
    result[:] = 23  # to notice it


def TaskCall(a, result):
    @instance
    def logic():
        var = intbv(0)[8:]
        while 1:
            yield a
            ReturnFromTask(a, var)
            result.next = var
    return logic


def WhileLoop(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            i = len(a)-1
            while i >= 0:
                if a[i] == 1:
                    var += 1
                i -= 1
            result.next = var
    return logic


def WhileContinueLoop(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            i = len(a)-1
            while i >= 0:
                if a[i] == 0:
                    i -= 1
                    continue
                var += 1
                i -= 1
            result.next = var
    return logic


def WhileBreakLoop(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            i = len(a)-1
            result.next = 0
            while i >= 0:
                if a[i] == 1:
                    result.next = i
                    break
                i -= 1
    return logic


def WhileBreakContinueLoop(a, result):
    @instance
    def logic():
        while 1:
            yield a
            var = 0
            i = len(a)-1
            result.next = 0
            while i >= 0:
                if a[i] == 0:
                    i -= 1
                    continue
                result.next = i
                break
    return logic


def LoopBench(LoopTest):

    a = Signal(intbv(-1)[16:])
    z = Signal(intbv(0)[16:])

    looptest_inst = LoopTest(a, z)
    data = tuple([randrange(2**min(i, 16)) for i in range(100)])

    @instance
    def stimulus():
        for i in range(100):
            a.next = data[i]
            yield delay(10)
            print(int(z))

    return stimulus, looptest_inst


def testForLoop1():
    assert verify(LoopBench, ForLoop1) == 0


def testForLoop2():
    assert verify(LoopBench, ForLoop2) == 0


def testForLoop4():
    assert verify(LoopBench, ForLoop4) == 0


def testForLoop5():
    assert verify(LoopBench, ForLoop5) == 0


# for loop 3 and 6 can't work in vhdl
def testForContinueLoop():
    assert verify(LoopBench, ForContinueLoop) == 0


def testForBreakLoop():
    assert verify(LoopBench, ForBreakLoop) == 0


def testForBreakContinueLoop():
    assert verify(LoopBench, ForBreakContinueLoop) == 0


def testNestedForLoop1():
    assert verify(LoopBench, NestedForLoop1) == 0


def testNestedForLoop2():
    assert verify(LoopBench, NestedForLoop2) == 0


def testFunctionCall():
    assert verify(LoopBench, FunctionCall) == 0

## def testTaskCall(self):
##     sim = self.bench(TaskCall)
##     Simulation(sim).run()


def testWhileLoop():
    assert verify(LoopBench, WhileLoop) == 0


def testWhileContinueLoop():
    assert verify(LoopBench, WhileContinueLoop) == 0


def testWhileBreakLoop():
    assert verify(LoopBench, WhileBreakLoop) == 0


def testWhileBreakContinueLoop():
    assert verify(LoopBench, WhileBreakContinueLoop) == 0


def testForLoopError1():
    try:
        analyze(LoopBench, ForLoopError1)
    except ConversionError as e:
        assert e.kind == _error.Requirement
    else:
        assert False


def testForLoopError2():
    try:
        analyze(LoopBench, ForLoopError2)
    except ConversionError as e:
        assert e.kind == _error.Requirement
    else:
        assert False
