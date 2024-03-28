import pytest
from myhdl import uintba, sintba, Signal, instance, delay, conversion, ExtractHierarchyError
from myhdl.conversion._misc import _error as errors


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
