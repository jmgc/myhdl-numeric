
from myhdl import enum, intbv, always_comb, Signal, instance, delay, \
    instances, StopSimulation, conversion, ConversionError
from myhdl.conversion._misc import _error as errors

bitwise_op = enum('BW_AND', 'BW_ANDN', 'BW_OR', 'BW_XOR')


def bitwise(a, b, op):
    r = intbv(0)[8:]
    if op == bitwise_op.BW_AND:
        r[:] = a & b
    elif op == bitwise_op.BW_ANDN:
        r[:] = (~a) & b
    elif op == bitwise_op.BW_OR:
        r[:] = a | b
    elif op == bitwise_op.BW_XOR:
        r[:] = a ^ b
    return r


def LogicUnit(a, b, c, op):
    @always_comb
    def operate():
        c.next = bitwise(a, b, op)
    return operate


def bench_enum():
    clock = Signal(False)
    a, b, c = [Signal(intbv(0)[8:]) for _ in range(3)]
    op = Signal(bitwise_op.BW_AND)
    logic_unit = LogicUnit(a=a, b=b, c=c, op=op)

    @instance
    def clockgen():
        clock.next = 1
        while 1:
            yield delay(10)
            clock.next = not clock

    @instance
    def stimulus():
        a.next = 0xaa
        b.next = 0x55
        yield clock.posedge
        print('a=%s b=%s' % (int(a), int(b)))

        op.next = bitwise_op.BW_AND
        yield clock.posedge
        print(int(op))
        print(int(c))

        op.next = bitwise_op.BW_ANDN
        yield clock.posedge
        print(int(op))
        print(int(c))

        op.next = bitwise_op.BW_OR
        yield clock.posedge
        print(int(op))
        print(int(c))

        op.next = bitwise_op.BW_XOR
        yield clock.posedge
        print(int(op))
        print(int(c))

        raise StopSimulation

    return instances()


def test_enum():
    assert conversion.verify(bench_enum) == 0


def bench_bad_enum_var():
    t_state = enum('IDLE', 'RUNNING', 'STOPPED', 'PAUSED')

    idle = Signal(False)

    @instance
    def check():
        running = 0
        value = t_state.RUNNING
        data = t_state.IDLE
        yield delay(10)

    return check


def bench_bad_enum_sig():
    t_state = enum('IDLE', 'RUNNING', 'STOPPED', 'PAUSED')

    idle = Signal(False)

    @instance
    def check():
        idle.next = True
        data = t_state.IDLE
        yield delay(10)

    return check


def bench_bad_enum_keyword():
    t_state = enum('IDLE', 'RUNNING', 'STOPPED', 'CASE')

    idle = Signal(False)

    @instance
    def check():
        idle.next = True
        data = t_state.CASE
        yield delay(10)

    return check


def test_bad_enum_var():
    try:
        assert conversion.analyze(bench_bad_enum_var) == 0
    except ConversionError as e:
        assert e.kind == errors.ShadowingEnum


def test_bad_enum_sig():
    try:
        assert conversion.analyze(bench_bad_enum_sig) == 0
    except ConversionError as e:
        assert e.kind == errors.ShadowingEnum


def test_bad_enum_keyword():
    try:
        assert conversion.analyze(bench_bad_enum_keyword) == 0
    except ConversionError as e:
        assert e.kind == errors.ReservedWord
