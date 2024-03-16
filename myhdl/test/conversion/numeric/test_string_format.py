from myhdl import uintba, sintba, Signal, instance, delay, conversion, ConversionError
from myhdl.conversion._misc import _error as errors


def string_format():
    a = Signal(uintba(23, 8))
    b = Signal(sintba(-53, 8))

    @instance
    def bench():
        print(f"str: a={a}")
        print(f"str: b={b}")
        yield delay(10)
        print(f"dec: a={a:d}")
        print(f"dec: b={b:d}")
        yield delay(10)
        print(f"oct: a={a:o}")
        print(f"oct: b={b:o}")
        yield delay(10)
        print(f"hex: a={a:x}")
        print(f"hex: b={b:x}")
        yield delay(10)
        print(f"a={a}\nb={b}")
        print("a,\n")
        print("c")
        print("\na\n")
        print(f"{1}")
        print(f"{-1}")
        print("end")

    return bench


def test_string_format():
    assert conversion.verify(string_format) == 0


def string_format_error_bin():

    @instance
    def bench():
        print(f"{1:b}")
        yield delay(10)

    return bench


def test_string_error_bin():
    try:
        assert conversion.verify(string_format_error_bin) == 0
    except ConversionError as e:
        assert e.kind == errors.UnsupportedType


def string_format_error_hex():

    @instance
    def bench():
        print(f"{1:h}")
        yield delay(10)

    return bench


def test_string_error_hex():
    try:
        assert conversion.verify(string_format_error_hex) == 0
    except ConversionError as e:
        assert e.kind == errors.UnsupportedType


def string_format_error_oct():

    @instance
    def bench():
        print(f"{1:o}")
        yield delay(10)

    return bench


def test_string_error_oct():
    try:
        assert conversion.verify(string_format_error_oct) == 0
    except ConversionError as e:
        assert e.kind == errors.UnsupportedType
