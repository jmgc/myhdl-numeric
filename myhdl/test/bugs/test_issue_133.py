from __future__ import absolute_import
from myhdl import instance, Signal, intbv, delay
from myhdl.conversion import verify


def issue_133():
    z = Signal(False)
    large_signal = Signal(intbv(123456789123456, min=0, max=2**256))

    @instance
    def check():
        z.next = large_signal[10]
        yield delay(10)
        print(int(large_signal[31:]))
        print(int(large_signal[62:31]))
        print(int(large_signal[93:62]))

    return check


def test_issue_133():
    assert verify(issue_133) == 0
