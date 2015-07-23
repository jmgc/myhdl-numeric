from __future__ import absolute_import, print_function

import os
path = os.path
import unittest

from myhdl import *

def ternary1(dout, clk, rst):

    @always(clk.posedge, rst.negedge)
    def logic():
        if rst == 0:
            dout.next = 0
        else:
            dout.next = (dout + 1) if dout < 127 else 0

    return logic


def ternary2(dout, clk, rst):

    dout_d = Signal(sfixba(0, len(dout), 0))

    @always(clk.posedge, rst.negedge)
    def logic():
        if rst == 0:
            dout.next = 0
        else:
            dout.next = dout_d

    @always_comb
    def comb():
        dout_d.next = (dout + 1) if dout < 127 else 0

    return logic, comb

def TernaryBench(ternary):

    dout = Signal(sfixba(0, 8))
    clk = Signal(False)
    rst = Signal(False)

    ternary_inst = ternary(dout, clk, rst)

    @instance
    def stimulus():
        rst.next = 1
        clk.next = 0
        yield delay(10)
        rst.next = 0
        yield delay(10)
        rst.next = 1
        yield delay(10)
        for i in range(1000):
            clk.next = 1
            yield delay(10)
            assert dout == (i + 1) % 128
            print(int(dout))
            clk.next = 0
            yield delay(10)

        raise StopSimulation()

    return stimulus, ternary_inst



# uncomment when we have a VHDL-2008 compliant simulator
def test_ternary1():
    toVHDL.name = 'ternary1'
    assert conversion.verify(TernaryBench, ternary1) == 0

def test_ternary2():
    toVHDL.name = 'ternary2'
    assert conversion.verify(TernaryBench, ternary2) == 0

