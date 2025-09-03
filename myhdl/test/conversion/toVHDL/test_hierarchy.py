from myhdl import Signal, intbv, always_seq, instance, delay, StopSimulation, \
    ResetSignal, conversion
import shutil
import os

def hierarchy_level(clk, reset, z, a):
    @always_seq(clk.posedge, reset)
    def logic():
        if a == 1:
            z.next = 0
        elif a in (2, 3):
            z.next = 1
        else:
            z.next = 3

    return logic

def hierarchy_level_2(clk, reset, z, a):
    y = Signal(intbv(0)[3:])
    comp1 = hierarchy_level(clk, reset, y, a)
    comp2 = hierarchy_level(clk, reset, z, y)
    return comp1, comp2

def hierarchy_level_1(clk, reset, z, a):
    y = Signal(intbv(0)[4:])
    comp1 = hierarchy_level_2(clk, reset, y, a)
    comp2 = hierarchy_level_2(clk, reset, z, y)
    return comp1, comp2


def test_hierarchy_analyse():
    clk = Signal(False)
    reset = ResetSignal(True, True, False)
    a = Signal(intbv(0)[3:])
    z = Signal(intbv(0)[4:])

    assert conversion.analyze(hierarchy_level_1, clk, reset, z, a) == 0

def test_hierarchy_analyse_multiple_files():
    clk = Signal(False)
    reset = ResetSignal(True, True, False)
    a = Signal(intbv(0)[3:])
    z = Signal(intbv(0)[4:])

    one_file = conversion.toVHDL.one_file
    conversion.toVHDL.one_file = False
    conversion.toVHDL.directory = "hierarchy_multiple_files"
    shutil.rmtree(conversion.toVHDL.directory, ignore_errors=True)
    os.mkdir(conversion.toVHDL.directory)
    assert conversion.analyze(hierarchy_level_1, clk, reset, z, a) == 0
    instance_entity = conversion.toVHDL.instance_entity
    conversion.toVHDL.directory = None
    conversion.toVHDL.one_file = one_file

def test_hierarchy_analyse_equal():
    clk = Signal(False)
    reset = ResetSignal(True, True, False)
    a = Signal(intbv(0)[3:])
    z = Signal(intbv(0)[3:])

    assert conversion.analyze(hierarchy_level_2, clk, reset, z, a) == 0

def test_hierarchy_analyse_multiple_files_equal():
    clk = Signal(False)
    reset = ResetSignal(True, True, False)
    a = Signal(intbv(0)[3:])
    z = Signal(intbv(0)[3:])

    one_file = conversion.toVHDL.one_file
    conversion.toVHDL.one_file = False
    conversion.toVHDL.directory = "hierarchy_multiple_files_equal"
    shutil.rmtree(conversion.toVHDL.directory, ignore_errors=True)
    os.mkdir(conversion.toVHDL.directory)
    assert conversion.analyze(hierarchy_level_2, clk, reset, z, a) == 0
    instance_entity = conversion.toVHDL.instance_entity
    conversion.toVHDL.directory = None
    conversion.toVHDL.one_file = one_file

def hierarchy_case(hierarchy_dut):
    clk = Signal(False)
    reset = ResetSignal(True, True, False)
    a = Signal(intbv(0)[3:])
    z = Signal(intbv(0)[4:])

    dut = hierarchy_dut(clk, reset, z, a)

    PERIOD = 10

    @instance
    def clockgen():
        clk.next = False
        while True:
            yield delay(PERIOD // 2 + 1)
            clk.next = not clk

    @instance
    def stimulus():
        reset.next = True
        yield delay(10)
        reset.next = False
        for i in range(10):
            a.next = i % 5
            yield clk.posedge
            print(f"a={int(a)}, z={int(z)}")
        raise StopSimulation

    return dut, clockgen, stimulus

def test_hierarchy_verify():

    assert conversion.verify(hierarchy_case, hierarchy_level_1) == 0
