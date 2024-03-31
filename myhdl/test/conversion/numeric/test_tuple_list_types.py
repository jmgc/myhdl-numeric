from myhdl import uintba, Signal, instance, delay, conversion, Simulation, StopSimulation
from myhdl._errors import ToVHDLError


def tuple_list_types(mem_in, mem_out):

    mem_idx = Signal(uintba(0, mem_out[0].val))

    @instance
    def bench():
        mem_idx.next = 0
        yield delay(10)
        while mem_idx < len(mem_in):
            mem_out[mem_idx].next = mem_in[mem_idx]
            print(f"{uintba(mem_in[mem_idx], mem_out[0].val):x}")
            yield delay(10)
            print(f"{mem_out[mem_idx]:x}")
            assert mem_out[mem_idx] == mem_in[mem_idx]
            mem_idx.next = mem_idx + 1
            yield delay(10)
        raise StopSimulation

    return bench


def test_tuple_list_types_sim():
    WORD_BITS = 32
    mem_in = tuple((1 << 31) + i for i in range(512))
    mem_out = [Signal(uintba(0, WORD_BITS)) for _ in range(512)]

    Simulation(tuple_list_types(mem_in, mem_out))


def test_tuple_list_types_verify():
    WORD_BITS = 32
    mem_in = tuple(uintba((1 << 31) + i, WORD_BITS) for i in range(512))
    mem_out = [Signal(uintba(0, WORD_BITS)) for _ in range(512)]

    assert conversion.verify(tuple_list_types, mem_in, mem_out) == 0


def test_tuple_list_types_verify_fail():
    WORD_BITS = 32
    mem_in = tuple((1 << 31) + i for i in range(512))
    mem_out = [Signal(uintba(0, WORD_BITS)) for _ in range(512)]
    try:
        assert conversion.verify(tuple_list_types, mem_in, mem_out) == 0
    except ToVHDLError as e:
        assert True
