
from myhdl import uintba, sintba, Signal, instance, delay, conversion


def string_format():
    a = Signal(uintba(23, 8))
    b = Signal(sintba(-53, 8))
    @instance
    def bench():
        print(f"a={a}")
        print(f"b={b}")
        yield delay(10)
        print(f"a={a:d}")
        print(f"b={b:d}")
        yield delay(10)
        print(f"a={a:x}")
        print(f"b={b:x}")

    return bench


def test_string_format():
    assert conversion.verify(string_format) == 0
