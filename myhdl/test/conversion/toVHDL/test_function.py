from myhdl import uintba, Simulation, instance, conversion, delay, StopSimulation
from myhdl.test.conftest import bug

CHECK_BIT = 3


def is_valid(value):
    value_u = uintba(value, 8)
    result = value_u[CHECK_BIT] != 0
    return result


def is_not_valid(cmd):
    check = is_valid(cmd)
    result = not check
    return result


def function_test_bench():
    @instance
    def check():
        for i in range(256):
            value = uintba(i, 8)
            result = is_valid(value)
            not_result = is_not_valid(value)
            yield delay(10)
            print(value, result, not_result)
            assert result != not_result, f"Error: {result} != {not_result}"
        raise StopSimulation

    return check


def test_sim():
    sim = Simulation(function_test_bench())
    sim.run()


@bug("Unable to convert a call in a function", "VHDL")
def test_analyze():
    assert conversion.analyze(function_test_bench) == 0


@bug("Unable to convert a call in a function", "VHDL")
def test_verify():
    conversion.toVHDL.name = "function_test_bench_verify"
    assert conversion.verify(function_test_bench) == 0
    conversion.toVHDL.name = None
