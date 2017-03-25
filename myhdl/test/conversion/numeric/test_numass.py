from __future__ import absolute_import, print_function

from random import randrange

from myhdl import Signal, uintba, sintba, sfixba, \
    instance, delay, conversion, always_seq, now, ResetSignal, \
    StopSimulation


def NumassBench():
    p = Signal(uintba(1, 8))
    q = Signal(uintba(1, 40))
    r = Signal(sintba(1, 9))
    s = Signal(sintba(1, 41))
    t = Signal(sfixba(1, 5, -4))
    u = Signal(sfixba(1, 31, -10))
    PBIGINT = Signal(uintba(randrange(2**34, 2**40)))
    NBIGINT = Signal(sintba(-randrange(2**34, 2**40)))

    @instance
    def check():
        p.next = 0
        q.next = 0
        r.next = 0
        s.next = 0
        t.next[:] = 0
        u.next[:] = 0
        yield delay(10)
        print("%d %d %d %d %s %s" % (p, q, r, s, t, u))
        p.next = 1
        q.next = 1
        r.next = 1
        s.next = 1
        t.next[:] = 1
        u.next[:] = 1
        yield delay(10)
        print("%d %d %d %d %s %s" % (p, q, r, s, t, u))
        p.next = 2
        q.next = 2
        r.next = -2
        s.next = -2
        t.next[:] = -2
        u.next[:] = -2
        yield delay(10)
        print("%d %d %d %d %s %s" % (p, q, r, s, t, u))
        p.next = 255
        q.next = 246836311517
        r.next = 255
        s.next = -246836311517
        t.next[:] = 255
        u.next[:] = -246836311517
        yield delay(10)
        print("%d %d %d %d %d %d %s %s %s" %
              (p, q[40:20], q[20:0], r,
               s[41:20], s[20:0], t, u[31:10], u[10:-10]))
        print("%s %s" % (s[41:20] >= s[20:0],
                         u[31:10] >= u[10:-10]))
        p.next = 254
        q.next = PBIGINT
        r.next = -256
        s.next = NBIGINT
        t.next[:] = -256
        u.next[:] = NBIGINT
        yield delay(10)
        print("%d %d %d %d %d %d %s %s %s" %
              (p, q[40:20], q[20:0], r,
               s[41:20], s[20:0], t, u[31:10], u[10:-10]))
        print("%s %s" % (s[41:20] >= s[20:0],
                         u[31:10] >= u[10:-10]))

    return check


def test_numass():
    assert conversion.verify(NumassBench) == 0


def array_input_1(reset, clk, value=None):
    if value is None:
        value = [Signal(uintba(7)),]

    @always_seq(clk.posedge, reset)
    def fsm():
        print(value[0])
        print(now())

    return fsm


def array_input_2(reset, clk, value=None):
    if value is None:
        value = [Signal(uintba(2)), Signal(uintba(3))]

    @always_seq(clk.posedge, reset)
    def fsm():
        pass

    return fsm


def array_testbench():
    clk = Signal(True)
    reset = ResetSignal(True, True, False)
    value = 10

    @instance
    def clockGen():
        reset.next = True
        clk.next = False
        yield delay(value)
        reset.next = False
        clk.next = not clk
        yield delay(value)
        clk.next = not clk
        yield delay(value)
        clk.next = not clk
        yield delay(value)
        clk.next = not clk
        raise StopSimulation

    dut1 = array_input_1(reset, clk, None)

    dut2 = array_input_2(reset, clk, None)

    return clockGen, dut1, dut2


def test_array_input():
    assert conversion.verify(array_testbench) == 0


