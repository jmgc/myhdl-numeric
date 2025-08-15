from myhdl import uintba, sintba, sfixba, Signal, instance, delay, conversion, ExtractHierarchyError, always_comb


def check_no_instances():
    a = Signal(uintba(23, 8))

    @instance
    def bench():
        yield delay(10)
        print(f"str: a={a}")

    @instance
    def returned():
        yield delay(10)
        print(f"str: a={a}")

    return returned


def check_second_order():
    a = Signal(uintba(23, 8))

    @instance
    def bench():
        yield delay(10)
        print(f"str: a={a}")
        yield delay(10)
        print(f"dec: a={a:d}")

    return bench


def first_order():
    second = check_second_order()


def std_logic_ports_component(check: Signal, input_port_c: Signal, output_port_c: Signal,
                              input_port_not_used: Signal, output_port_not_used: Signal):
    @always_comb
    def logic_loop():
        if check:
            output_port_c.next = input_port_c
            output_port_not_used.next = input_port_not_used

    return logic_loop


def std_logic_ports_entity(check: Signal, input_port_e: Signal, output_port_e: Signal):
    input_signal = Signal(uintba(0, 16))
    output_signal = Signal(uintba(0, 16))
    component = std_logic_ports_component(check, input_port_e, output_port_e, input_signal, output_signal)
    return component


def std_logic_ports_test_sfixba_bench():
    check_signal = Signal(False)
    input_signal = Signal(sfixba(0, 16, -16))
    output_signal = Signal(sfixba(0, 16, -16))

    entity = std_logic_ports_entity(check_signal, input_signal, output_signal)

    @instance
    def stimulus():
        for i in range(5):
            check_signal.next = not check_signal
            input_signal.next = i / 10.0
            yield delay(20)
            assert (check_signal and (input_signal == output_signal)) or (
                        not check_signal and (output_signal != input_signal))
            print(f"Input: {input_signal}, Output: {output_signal}")

    return entity, stimulus


def test_std_logic_ports_sfixba():
    tmp_val = conversion.toVHDL.std_logic_ports
    conversion.toVHDL.std_logic_ports = True
    assert conversion.verify(std_logic_ports_test_sfixba_bench) == 0
    conversion.toVHDL.std_logic_ports = tmp_val


def std_logic_ports_test_intba_bench():
    check_signal = Signal(False)
    input_signal = Signal(uintba(0, 16))
    output_signal = Signal(sintba(0, 16))

    entity = std_logic_ports_entity(check_signal, input_signal, output_signal)

    @instance
    def stimulus():
        for i in range(5):
            check_signal.next = not check_signal
            input_signal.next = i
            yield delay(20)
            assert (check_signal and (input_signal == output_signal)) or (
                        not check_signal and (output_signal != input_signal))
            print(f"Input: {input_signal}, Output: {output_signal}")

    return entity, stimulus


def test_std_logic_ports_intba():
    tmp_val = conversion.toVHDL.std_logic_ports
    conversion.toVHDL.std_logic_ports = True
    assert conversion.verify(std_logic_ports_test_intba_bench) == 0
    conversion.toVHDL.std_logic_ports = tmp_val


def std_logic_ports_component_array(check: Signal, input_port_c: list, output_port_c: list,
                                    input_port_not_used: Signal, output_port_not_used: Signal):
    @always_comb
    def logic_loop():
        if check:
            for i in range(len(input_port_c)):
                output_port_c[i].next = input_port_c[i]
            output_port_not_used.next = input_port_not_used

    return logic_loop


def std_logic_ports_entity_array(check: Signal, input_port_e: list, output_port_e: list):
    input_signal = Signal(uintba(0, 16))
    output_signal = Signal(uintba(0, 16))
    components = [std_logic_ports_component(check, input_port_e[idx], output_port_e[idx], input_signal, output_signal)
                  for idx in range(len(input_port_e))]
    return components


def std_logic_ports_test_sfixba_array_bench():
    PORTS = 2
    check_signal = Signal(False)
    input_signal = [Signal(sfixba(0, 16, -16)) for _ in range(PORTS)]
    output_signal = [Signal(sfixba(0, 16, -16)) for _ in range(PORTS)]

    entity = std_logic_ports_entity_array(check_signal, input_signal, output_signal)

    @instance
    def stimulus():
        for i in range(5):
            check_signal.next = not check_signal
            for idx in range(PORTS):
                input_signal[idx].next = i / 10.0
            yield delay(20)
            for idx in range(PORTS):
                assert (check_signal and (input_signal[idx] == output_signal[idx])) or (
                            not check_signal and (output_signal[idx] != input_signal[idx]))
            a = input_signal[0]
            b = output_signal[0]
            print(f"Input: {a}, Output: {b}")

    return entity, stimulus


def test_std_logic_ports_sfixba_array():
    tmp_val = conversion.toVHDL.std_logic_ports
    conversion.toVHDL.std_logic_ports = True
    assert conversion.verify(std_logic_ports_test_sfixba_array_bench) == 0
    conversion.toVHDL.std_logic_ports = tmp_val


def std_logic_ports_test_intba_array_bench():
    PORTS = 2
    check_signal = Signal(False)
    input_signal = [Signal(sintba(0, 16)) for _ in range(PORTS)]
    output_signal = [Signal(uintba(0, 16)) for _ in range(PORTS)]

    entity = std_logic_ports_entity_array(check_signal, input_signal, output_signal)

    @instance
    def stimulus():
        for i in range(5):
            check_signal.next = not check_signal
            for idx in range(PORTS):
                input_signal[idx].next = i
            yield delay(20)
            for idx in range(PORTS):
                assert (check_signal and (input_signal[idx] == output_signal[idx])) or (
                            not check_signal and (output_signal[idx] != input_signal[idx]))
            a = input_signal[0]
            b = output_signal[0]
            print(f"Input: {a}, Output: {b}")

    return entity, stimulus


def test_std_logic_ports_intba_array():
    tmp_val = conversion.toVHDL.std_logic_ports
    conversion.toVHDL.std_logic_ports = True
    assert conversion.verify(std_logic_ports_test_intba_array_bench) == 0
    conversion.toVHDL.std_logic_ports = tmp_val


def test_no_instances():
    try:
        assert conversion.verify(check_no_instances) == 0
    except ExtractHierarchyError as e:
        assert "bench" in e.args[0]


def test_second_odrder():
    try:
        assert conversion.verify(first_order) == 0
    except ExtractHierarchyError as e:
        assert "bench" in e.args[1]
