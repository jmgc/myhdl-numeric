from myhdl import uintba, Simulation, instance, conversion, delay, StopSimulation
from myhdl.test.conftest import bug
from collections import namedtuple

CHECK_BIT = 3

_ROM_DATA = namedtuple("_ROM_DATA",
                       ["VALUE_0",
                        "VALUE_1", ])
ROM_DATA = _ROM_DATA(VALUE_0=0x35,
                     VALUE_1=0x43, )


def check_function(value):
    result = uintba(0, 8)
    if value == ROM_DATA.VALUE_0:
        result = uintba(1, 8)
    elif value == ROM_DATA.VALUE_1:
        result = uintba(2, 8)
    return result


def check_function_test_bench():
    @instance
    def check():
        for i in range(256):
            value = uintba(i, 8)
            result = check_function(value)
            yield delay(10)
            print(value, result)
        raise StopSimulation

    return check


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


def test_check_function_sim():
    sim = Simulation(check_function_test_bench())
    sim.run()


def test_check_function_analyze():
    assert conversion.analyze(check_function_test_bench) == 0


def test_check_function_verify():
    conversion.toVHDL.name = "check_function_test_bench_verify"
    assert conversion.verify(check_function_test_bench) == 0
    conversion.toVHDL.name = None


def test_function_sim():
    sim = Simulation(function_test_bench())
    sim.run()


@bug("Unable to convert a call in a function", "VHDL")
def test_function_analyze():
    assert conversion.analyze(function_test_bench) == 0


@bug("Unable to convert a call in a function", "VHDL")
def test_function_verify():
    conversion.toVHDL.name = "function_test_bench_verify"
    assert conversion.verify(function_test_bench) == 0
    conversion.toVHDL.name = None
