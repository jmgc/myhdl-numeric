from __future__ import absolute_import, print_function

from tempfile import mkdtemp
from shutil import rmtree
import os

from myhdl import Signal, uintba, \
    instance, delay, conversion, always_seq, now, ResetSignal, \
    StopSimulation

def array_input_1(reset, clk, value=None):
    if value is None:
        value = [Signal(uintba(7)),]

    @always_seq(clk.posedge, reset)
    def fsm():
        print(value[0])
        print(now())

    return fsm


def array_input_2(reset, clk, value=None):
    if value is None:
        value = [Signal(uintba(2)), Signal(uintba(3))]

    @always_seq(clk.posedge, reset)
    def fsm():
        pass

    return fsm


def array_testbench():
    clk = Signal(True)
    reset = ResetSignal(True, True, False)
    value = 10

    @instance
    def clockGen():
        reset.next = True
        clk.next = False
        yield delay(value)
        reset.next = False
        clk.next = not clk
        yield delay(value)
        clk.next = not clk
        yield delay(value)
        clk.next = not clk
        yield delay(value)
        clk.next = not clk
        raise StopSimulation

    dut1 = array_input_1(reset, clk, None)

    dut2 = array_input_2(reset, clk, None)

    return clockGen, dut1, dut2


def test_array_input():
    tmp_dir = mkdtemp()
    conversion.toVHDL.directory = tmp_dir
    one_file = conversion.toVHDL.one_file
    conversion.toVHDL.one_file = False
    assert conversion.verify(array_testbench) == 0
    assert os.path.exists(os.path.join(tmp_dir, 'array_testbench.vhd'))
    conversion.toVHDL.one_file = one_file
    conversion.toVHDL.directory = None
    rmtree(tmp_dir)
