import pytest

from myhdl import Signal, ResetSignal, instance, now, StopSimulation, always_seq, uintba, delay, Simulation, downrange, toVHDL, conversion


CRC16_INIT = 0xffff
CRC16_POLY = 0x1021
CRC16_WIDTH = 16

CRC24_INIT = 0xb704ce
CRC24_POLY = 0x1864cfb
CRC24_WIDTH = 24


cases = [(CRC16_POLY, CRC16_INIT, CRC16_WIDTH, 0x0000, 16, 0x1D0F),
         (CRC16_POLY, CRC16_INIT, CRC16_WIDTH, 0x000000, 24, 0xCC9C),
         (CRC16_POLY, CRC16_INIT, CRC16_WIDTH, 0xABCDEF01, 32, 0x04A2),
         (CRC16_POLY, CRC16_INIT, CRC16_WIDTH, 0x1456F89A0001, 48, 0x7FD5),
         (CRC16_POLY, CRC16_INIT, CRC16_WIDTH, 0x0403014012340006000000005678000000001b69, 160, 0x0000),
         (CRC24_POLY, CRC24_INIT, CRC24_WIDTH, 0x0000, 16, 0xFAEDC0),
         (CRC24_POLY, CRC24_INIT, CRC24_WIDTH, 0x000000, 24, 0x25EF22),
         (CRC24_POLY, CRC24_INIT, CRC24_WIDTH, 0xABCDEF01, 32, 0x5C6390),
         (CRC24_POLY, CRC24_INIT, CRC24_WIDTH, 0x1456F89A0001, 48, 0x345DC0)]


def crc_func_test_bench(data: int, data_width: int, poly: int, initial: int, width: int, expected: int):
    reset = ResetSignal(True, True, False)
    clk = Signal(False)
    period = 8
    in_buffer = uintba(data, data_width)

    lfsr_reg = Signal(uintba(initial, width))
    crc = uintba(poly, width)
    expected_crc = uintba(expected, width)
    check_bit = Signal(False)

    @instance
    def clock_gen():
        clk.next = False
        while True:
            yield delay(period // 2)
            clk.next = not clk

    @instance
    def logic():
        lfsr = lfsr_reg.val
        reset.next = True
        for _ in range(10):
            yield clk.posedge
        reset.next = False
        yield clk.posedge
        for i in downrange(in_buffer.high):
            bit = lfsr[lfsr.high - 1] ^ in_buffer[i]
            for j in downrange(lfsr.high - 1):
                if crc[j + 1]:
                    lfsr[j + 1] = lfsr[j] ^ bit
                else:
                    lfsr[j + 1] = lfsr[j]
            lfsr[0] = bit
            check_bit.next = bit
            lfsr_reg.next = lfsr
            yield clk.posedge

        yield clk.posedge
        assert expected_crc == lfsr_reg
        yield clk.negedge
        raise StopSimulation

    @always_seq(clk.posedge, reset)
    def check():
        print(now(), in_buffer, crc, check_bit, lfsr_reg)

    return clock_gen, logic, check


@pytest.mark.parametrize("poly, initial, width, data, data_width, expected", cases)
@pytest.mark.simulation
def test_crc_func_simulation(poly: int, initial: int, width: int, data: int, data_width: int, expected: int):
    sim = Simulation(crc_func_test_bench(data, data_width, poly, initial, width, expected))
    sim.run()


@pytest.mark.parametrize("poly, initial, width, data, data_width, expected", cases)
@pytest.mark.vhdl_test
@pytest.mark.verify
def test_crc_func_verification(poly: int, initial: int, width: int, data: int, data_width: int, expected: int):
    toVHDL.name = f"crc_func_test_bench_{data:x}_{data_width:d}_{poly:x}_{initial:x}_{width:d}"
    assert conversion.verify(crc_func_test_bench, data, data_width, poly, initial, width, expected) == 0
    toVHDL.name = None
