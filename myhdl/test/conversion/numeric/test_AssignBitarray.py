'''
Created on 17/3/2015

@author: chema
'''
import unittest

from myhdl import uintba, sintba, sfixba, Signal, toVHDL, instance, delay, \
        StopSimulation, conversion
import warnings

#warnings.filterwarnings('error')

def bench_AssignSignal():
    a = Signal(uintba(0, 8))
    p = Signal(uintba(0, a))
    b = Signal(sintba(0, 8))
    q = Signal(sintba(0, b))
    c = Signal(sfixba(0, 4, -4))
    r = Signal(sfixba(0, c))
    d = Signal(sfixba(0, 8, 0))
    s = Signal(sfixba(0, d))
    e = Signal(sfixba(0, 0, -8))
    t = Signal(sfixba(0, e))

    p.assign(a)
    q.assign(b)
    r.assign(c)
    s.assign(d)
    t.assign(e)

    @instance
    def stimulus():
        a.next = 0
        b.next = 0
        c.next = 0
        d.next = 0
        e.next = 0
        yield delay(10)
        for i in range(len(c)):
            a.next = i
            b.next = i
            c.next = i
            d.next = i
            e.next = i
            yield delay(10)
            print(p)
            print(q)
            print(r)
            print(s)
            print(t)

    return stimulus

class Test(unittest.TestCase):


    def testName(self):
        self.assertEqual(conversion.verify(bench_AssignSignal), 0)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()