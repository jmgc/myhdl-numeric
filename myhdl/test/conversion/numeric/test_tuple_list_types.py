from myhdl import uintba, Signal, instance, delay, conversion, Simulation, StopSimulation


def tuple_list_types(mem_in, mem_out):

    mem_idx = Signal(uintba(len(mem_in)))

    @instance
    def bench():
        mem_idx.next = 0
        yield delay(10)
        while mem_idx < len(mem_in):
            mem_out[mem_idx].next = mem_in[mem_idx]
            print(f"{mem_in[mem_idx]:d}")
            yield delay(10)
            print(f"{mem_out[mem_idx]:d}")
            assert mem_out[mem_idx] == mem_in[mem_idx]
            mem_idx.next = mem_idx + 1
            yield delay(10)
        raise StopSimulation

    return bench


def test_tuple_list_types_sim():
    WORD_BITS = 16
    mem_in = tuple(uintba(i, WORD_BITS) for i in range(512))
    mem_out = [Signal(uintba(0, WORD_BITS)) for _ in range(512)]

    Simulation(tuple_list_types(mem_in, mem_out))


def test_tuple_list_types_verify():
    WORD_BITS = 16
    mem_in = tuple(uintba(0, WORD_BITS) for _ in range(512))
    mem_out = [Signal(uintba(0, WORD_BITS)) for _ in range(512)]

    assert conversion.verify(tuple_list_types, mem_in, mem_out) == 0
