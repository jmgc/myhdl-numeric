import pytest
from myhdl import instance, Signal, intbv, delay, enum, conversion
from myhdl import ConversionError
from myhdl.conversion._misc import _error

t_State = enum("START", "RUN", "STOP")


def print_check(si1):
    @instance
    def logic():
        yield delay(5)
        print("Hello World!", int(si1))
        yield delay(5)
        print("Hello World, another time!")

    return logic


def print_bench():
    si1 = Signal(intbv(0)[8:])
    si2 = Signal(intbv(0, min=-10, max=12))
    sb = Signal(bool(0))

    check = print_check(si1)

    @instance
    def logic():
        i1 = intbv(0)[8:]
        i2 = intbv(0, min=-10, max=12)
        b = bool(1)
        state = t_State.START
        i1[:] = 10
        si1.next = 11
        i2[:] = -7
        si2.next = -5
        yield delay(10)
        print('')
        print(int(i1))
        print(int(i2))
        print("%d %d" % (int(i1), int(i2)))
        print(int(si1))
        print(int(si2))

        yield delay(10)
        print("This is a test")

        yield delay(10)
        print(int(b))
        print(int(sb))

        yield delay(10)
        print("i1 is %s" % int(i1))

        yield delay(10)
        print("i1 is %s, i2 is %s" % (int(i1), int(i2)))
        print("i1 %s i2 %s b %s si1 %s si2 %s" %
              (int(i1), int(i2), b, int(si1), int(si2)))
        print("i1 %d i2 %d b %d si1 %d si2 %d" %
              (int(i1), int(i2), b, int(si1), int(si2)))
        print(b)
        # print "%% %s" % i1

        yield delay(10)
        print(state)
        print("the state is %s" % state)
        print("the state is %s" % (state,))
        print("i1 is %s and the state is %s" % (int(i1), state))

        # ord test
        yield delay(10)
        print(ord('y'))
        print(ord('2'))

        # signed
        yield delay(10)
        print(int(i1.signed()))
        print(int(i2.signed()))
        print(int(si1.signed()))
        print(int(si2.signed()))

    return logic, check


def test_print():
    assert conversion.verify(print_bench) == 0


# format string errors and unsupported features

def print_error1():
    @instance
    def logic():
        i1 = intbv(12)[8:]
        yield delay(10)
        print("floating point %f end" % i1)

    return logic


def testPrintError1():
    try:
        conversion.verify(print_error1)
    except ConversionError as e:
        assert e.kind == _error.UnsupportedFormatString
    else:
        assert False


def print_error2():
    @instance
    def logic():
        i1 = intbv(12)[8:]
        yield delay(10)
        print("begin %s %s end" % i1)

    return logic


def test_print_error2():
    try:
        conversion.verify(print_error2)
    except ConversionError as e:
        assert e.kind == _error.FormatString
    else:
        assert False


def print_error3():
    @instance
    def logic():
        i1 = intbv(12)[8:]
        i2 = intbv(13)[8:]
        yield delay(10)
        print("begin %s end" % (i1, i2))

    return logic


def test_print_error3():
    try:
        conversion.verify(print_error3)
    except ConversionError as e:
        assert e.kind == _error.FormatString
    else:
        assert False


def print_error4():
    @instance
    def logic():
        i1 = intbv(12)[8:]
        yield delay(10)
        print("%10s" % i1)

    return logic


def test_print_error4():
    try:
        conversion.verify(print_error4)
    except ConversionError as e:
        assert e.kind == _error.UnsupportedFormatString
    else:
        assert False


def print_error5():
    @instance
    def logic():
        i1 = intbv(12)[8:]
        yield delay(10)
        print("%-10s" % i1)

    return logic


def test_print_error5():
    try:
        conversion.verify(print_error5)
    except ConversionError as e:
        assert e.kind == _error.UnsupportedFormatString
    else:
        assert False


def print_error6():
    @instance
    def logic():
        output = intbv(12)[8:]
        yield delay(10)
        print("%s" % output)

    return logic


def test_print_error6():
    try:
        conversion.verify(print_error6)
    except ConversionError as e:
        assert e.kind == _error.ReservedWord
    else:
        assert False
