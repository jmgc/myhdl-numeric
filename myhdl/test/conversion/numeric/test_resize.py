from pytest import mark
from myhdl import Signal, uintba, sintba, sfixba, bitarray, \
    instance, delay, conversion, fixmath, toVHDL, StopSimulation
from ... import gen_id


def sfixba_resize_sfixba():
    fmath = fixmath(fixmath.overflows.saturate, fixmath.roundings.round)
    v = Signal(sfixba(-0.00048828125, 17, -16, fmath))
    w = Signal(sfixba(-0.00048828125, fmath))
    h = Signal(sfixba(0, 8, -8, fmath))
    i = Signal(uintba(3, 2))
    j = Signal(sfixba(-1.5, 2, -2))
    k = Signal(sintba(-1, 4))
    t = Signal(i & j)
    u = Signal(t & j)
    s = Signal(i & j & k)

    @instance
    def logic():
        yield delay(10)
        h.next = w.resize(v)
        yield delay(10)
        assert h == 0
        print("%s, %s" % (h, v))
        yield delay(10)
        h.next = w
        yield delay(10)
        assert h == 0
        print("%s, %s" % (h, w))
        yield delay(10)
        t.next = i & j
        yield delay(10)
        assert t == -2
        u.next = t & j
        s.next = i & j & k
        yield delay(10)
        assert u == -2
        print("%s, %s, %s, %s, %s, %s" % (i, j, t, k, u, s))

    return logic


def test_sfixba_resize_sfixba():
    assert conversion.verify(sfixba_resize_sfixba) == 0


def resize_vectors():
    return [(delta, i, j)
            for delta in range(-4, 1)
            for i in range(0, 5, 2)
            for j in range(delta, i - 1, 2)]


def sfixba_resize(delta, i, j):
    k = 128
    value = Signal(sfixba(k))
    scaled = Signal(sfixba(k).scalb(delta))
    data = Signal(sfixba(0, i, j))

    @instance
    def logic():
        for k in range(-128, 128):
            value.next = sfixba(k)
            yield delay(10)
            scaled.next = value.scalb(delta)
            yield delay(10)
            data.next = scaled.resize(i, j)
            yield delay(10)
            print("k: ", k)
            print("value: ", value)
            print("i: ", i)
            print("j: ", j)
            print("data: ", data)

    return logic


@mark.parametrize("delta, i, j", resize_vectors())
def test_resize(delta, i, j):
    toVHDL.name = "sfixba_resize_" + gen_id(delta, i, j)
    assert conversion.verify(sfixba_resize, delta, i, j) == 0
    toVHDL.name = None


def assign_boolean():
    c = True
    @instance
    def logic():
        a = bitarray(0, 8, 0)
        yield delay(10)
        a[7] = True
        a[6:5] = False
        a[4:3] = c
        print('a:', a)
        yield delay(10)
        raise StopSimulation

    return logic


def test_assign_boolean():
    assert conversion.verify(assign_boolean) == 0, f"{conversion.filename}"
