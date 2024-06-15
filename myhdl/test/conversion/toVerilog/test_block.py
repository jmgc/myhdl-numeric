from myhdl._block import block
from myhdl import instance, delay, StopSimulation, Signal, intbv
from myhdl import conversion
from myhdl.test.conftest import bug


def second_level(value, delta):
    @instance
    def fsm():
        yield delay(delta)
        print("%d" % value)
        raise StopSimulation
    return fsm


def module_test_bench():
    a = Signal(intbv(23)[8:])
    b = Signal(intbv(62)[8:])
    dut_a = second_level(a, 10)
    dut_b = second_level(b, 20)
    return dut_a, dut_b


def test_module():
    from myhdl import Simulation
    sim = Simulation(module_test_bench())
    sim.run()


def test_module_analyze():
    conversion.analyze.simulator = 'iverilog'
    assert conversion.analyze(module_test_bench) == 0
    conversion.analyze.simulator = None


def test_module_verify():
    conversion.verify.simulator = 'iverilog'
    conversion.toVerilog.name = 'test_module_verify'
    assert conversion.verify(module_test_bench) == 0
    conversion.toVerilog.name = None


@block
def block_second_level(value, delta):

    @instance
    def fsm():
        yield delay(delta)
        print("%d" % value)
        raise StopSimulation
    return fsm


@block
def block_test_bench():
    a = Signal(intbv(23)[8:])
    b = Signal(intbv(62)[8:])
    dut_a = block_second_level(a, 10)
    dut_b = block_second_level(b, 20)
    return dut_a, dut_b


def test_block():
    tb = block_test_bench()
    tb.run_sim()
    tb.quit_sim()
    assert True


@bug("Block analysis is not fully functional.", "Verilog")
def test_block_analyze():
    tb = block_test_bench()
    assert tb.analyze_convert() == 0


@bug("Block analysis is not fully functional.", "Verilog")
def test_block_verify():
    tb = block_test_bench()
    conversion.toVerilog.name = 'test_block_verify'
    assert tb.verify_convert() == 0
