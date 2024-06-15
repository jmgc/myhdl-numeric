from myhdl._block import block
from myhdl import instance, delay, StopSimulation, Signal, uintba
from myhdl import conversion


def slice_test():
    SLICE_BITS = slice(4, 2)

    @instance
    def testbench():
        value = uintba(0x3F, 8)
        print(value[5:2])
        print(value[SLICE_BITS])
        yield delay(10)
        raise StopSimulation

    return testbench


def test_slice_analyze():
    assert conversion.analyze(slice_test) == 0


def test_slice_verify():
    conversion.toVHDL.name = 'test_slice_verify'
    assert conversion.verify(slice_test) == 0
    conversion.toVHDL.name = None
