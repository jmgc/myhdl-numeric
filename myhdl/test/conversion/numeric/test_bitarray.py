'''
Created on 17/3/2015

@author: chema
'''
import unittest

from myhdl import uintba, intbv, Signal, toVHDL, instance, delay, \
        StopSimulation


def vhdlBitArrayTestBench():

    clk = Signal(False)

    n = 3

    inp_address = Signal(uintba(0, n))
    inp_data = Signal(intbv(0)[n:])

    @instance
    def clockGen():
        clk.next = True
        while True:
            yield delay(10)
            clk.next = not clk

    @instance
    def stimulus():
        inp_address.next = 0
        inp_data.next = 0
        yield clk.negedge
        v_address = inp_address + n
        inp_address.next = ~uintba(v_address)
        #inp_data.next = ~intbv(v_address)
        raise StopSimulation

    return clockGen, stimulus


class Test(unittest.TestCase):


    def testName(self):
        toVHDL(vhdlBitArrayTestBench)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()