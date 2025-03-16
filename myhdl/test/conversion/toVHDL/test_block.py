from myhdl._block import block
from myhdl import instance, delay, StopSimulation, Signal, uintba
from myhdl import conversion
from myhdl.test.conftest import bug

def module_third_level(value, time_delay):
    @instance
    def fsm():
        yield delay(time_delay)
        print("%d" % value)
    return fsm


def module_second_level(value, time_delay):
    dut = module_third_level(value, time_delay + 5)
    @instance
    def fsm():
        yield delay(time_delay)
        print(value)
    return fsm, dut


def module_test_bench():
    a = Signal(uintba(23, 8))
    b = Signal(uintba(62, 8))
    dut_a = module_second_level(a, 10)
    dut_b = module_second_level(b, 20)
    @instance
    def fsm():
        yield delay(100)
        raise StopSimulation
    return dut_a, dut_b, fsm


def test_module():
    from myhdl import Simulation
    sim = Simulation(module_test_bench())
    sim.run()


def test_module_analyze():
    assert conversion.analyze(module_test_bench) == 0


def test_module_verify():
    conversion.toVHDL.name = 'test_module_verify'
    assert conversion.verify(module_test_bench) == 0
    conversion.toVHDL.name = None


@block
def block_third_level(value, time_delay):
    @instance
    def fsm():
        yield delay(time_delay)
        print("%d" % value)
    return fsm


@block
def block_second_level(value, time_delay):

    dut = block_third_level(value, time_delay + 5)

    @instance
    def fsm():
        yield delay(time_delay)
        print(value)
    return fsm, dut


@block
def block_test_bench():
    a = Signal(uintba(23, 8))
    b = Signal(uintba(62, 8))
    dut_a = block_second_level(a, 10)
    dut_b = block_second_level(b, 20)

    @instance
    def fsm():
        yield delay(100)
        raise StopSimulation
    return dut_a, dut_b, fsm


def test_block():
    tb = block_test_bench()
    tb.run_sim()


def test_block_analyze():
    tb = block_test_bench()
    assert tb.analyze_convert() == 0

@bug("Block verification is not fully functional.", "vhdl")
def test_block_verify():
    tb = block_test_bench()
    assert tb.verify_convert() == 0
