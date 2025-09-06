from myhdl import Signal, intbv, always_seq, instance, delay, StopSimulation, \
    ResetSignal, conversion
import shutil
import os

def hierarchy_level(clk, reset, z, a, value):
    y = Signal(z.val)
    @always_seq(clk.posedge, reset)
    def logic():
        if a == 1:
            y.next = 0
        elif a == value:
            y.next = 1
        else:
            y.next = 3

    @always_seq(clk.posedge, reset)
    def Logic():
        z.next = y + 1

    return logic, Logic

def hierarchy_level_2(clk, reset, z, a, value):
    y = Signal(intbv(0)[3:])
    comp = hierarchy_level(clk, reset, y, a, value*5)
    Comp = hierarchy_level(clk, reset, z, y, value*3)
    return comp, Comp

def hierarchy_level_1(clk, reset, z, a, value=2):
    y = Signal(intbv(0)[4:])
    comp1 = hierarchy_level_2(clk, reset, y, a, value=value)
    comp2 = hierarchy_level_2(clk, reset, z, y, value=value*2)
    return comp1, comp2


def test_hierarchy_analyse():
    clk = Signal(False)
    reset = ResetSignal(True, True, False)
    a = Signal(intbv(0)[3:])
    z = Signal(intbv(0)[4:])

    assert conversion.analyze(hierarchy_level_1, clk, reset, z, a, 2) == 0

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
    assert conversion.analyze(hierarchy_level_1, clk, reset, z, a, 3) == 0
    instance_entity = conversion.toVHDL.instance_entity
    conversion.toVHDL.directory = None
    conversion.toVHDL.one_file = one_file

def test_hierarchy_analyse_equal():
    clk = Signal(False)
    reset = ResetSignal(True, True, False)
    a = Signal(intbv(0)[3:])
    z = Signal(intbv(0)[3:])

    assert conversion.analyze(hierarchy_level_2, clk, reset, z, a, 5) == 0

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
    assert conversion.analyze(hierarchy_level_2, clk, reset, z, a, 2) == 0
    instance_entity = conversion.toVHDL.instance_entity
    conversion.toVHDL.directory = None
    conversion.toVHDL.one_file = one_file

def clock_gen(clk, period):
    @instance
    def clockgen():
        clk.next = False
        while True:
            yield delay(period // 2 + 1)
            clk.next = not clk

    return clockgen

def hierarchy_case(hierarchy_dut):
    clk1 = Signal(False)
    reset1 = ResetSignal(True, True, False)
    a1 = Signal(intbv(0)[3:])
    z1 = Signal(intbv(0)[4:])
    clk2 = Signal(False)
    reset2 = ResetSignal(True, True, False)
    a2 = Signal(intbv(0)[3:])
    z2 = Signal(intbv(0)[4:])

    dut1 = hierarchy_dut(clk1, reset1, z1, a1, 2)
    dut2 = hierarchy_dut(clk2, reset2, z2, a2, 2*2)

    PERIOD = 10

    clk_gen1 = clock_gen(clk1, PERIOD)
    clk_gen2 = clock_gen(clk2, PERIOD * 2)

    values = tuple(range(10))

    @instance
    def stimulus1():
        a1.next = 0
        reset1.next = True
        yield delay(9)
        reset1.next = False
        yield clk1.posedge
        for i in range(10):
            value = values[i]
            a1.next = value % 5
            yield clk1.posedge
        raise StopSimulation

    mem_data = (3, 1, 4, 1, 5, 9, 2, 6, 5, 3)

    @instance
    def stimulus2():
        a2.next = 0
        reset2.next = True
        yield delay(2)
        reset2.next = False
        yield clk2.posedge
        for i in range(len(values)):
            assert 0 not in mem_data
            value = mem_data[i]
            print(f"value={value}")
            if value < a2.max:
                a2.next = value
            else:
                a2.next = a2.max - 1
            yield clk2.posedge

        raise StopSimulation

    return dut1, dut2, clk_gen1, clk_gen2, stimulus1, stimulus2

def test_hierarchy_verify():

    assert conversion.verify(hierarchy_case, hierarchy_level_1) == 0

def test_hierarchy_name_verify():

    conversion.toVHDL.name = "my_hierarchy"
    ports = conversion.toVHDL.std_logic_ports
    conversion.toVHDL.std_logic_ports = True
    assert conversion.verify(hierarchy_case, hierarchy_level_1) == 0
    conversion.toVHDL.std_logic_ports = ports
    conversion.toVHDL.name = None
