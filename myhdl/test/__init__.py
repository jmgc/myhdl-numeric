from math import floor, fmod, ldexp
from decimal import Decimal, ROUND_HALF_EVEN
from myhdl import fixmath


def truediv_round(value, value_format):
    if value < 0:
        neg = True
        tmp = -value
    else:
        neg = False
        tmp = value

    tmp = ldexp(floor(ldexp(tmp, -value_format.low + value_format.guard_bits)),
                -value_format.guard_bits)
    str_tmp = '{0:.4f}'.format(tmp)
    d = Decimal(str_tmp).quantize(0, rounding=ROUND_HALF_EVEN)
    tmp = ldexp(float(d), value_format.low)
    if neg:
        return -tmp
    else:
        return tmp


def wrap(val, value_format):
    length = value_format._high - value_format._low
    lim = int(1) << (length - 1)
    if val & lim:
        tmp = int(-1)
    else:
        tmp = int(0)
    wrap = lim - 1
    val &= wrap
    tmp &= ~wrap
    return tmp | val


def resize(value, value_format):
    val = float(value)
    lim = ldexp(1.0, value_format.high - 1)
    margin = ldexp(1.0, value_format.high)

    rounding = False

    if value_format.overflow == fixmath.overflows.saturate:
        if val >= lim:
            val = lim - ldexp(1.0, value_format.low)
        elif val < -lim:
            val = -lim
        else:
            rounding = True
    elif value_format.overflow == fixmath.overflows.wrap:
        if val < -lim or val >= lim:
            val = fmod(val, margin)
        if val < -lim:
            val += margin
        elif val > lim:
            val -= margin
        rounding = True

    if rounding and value_format.rounding == fixmath.roundings.round:
        tmp = ldexp(val, -value_format.low)
        #str_tmp = '{0:.4f}'.format(tmp)
        d = Decimal(tmp).quantize(0, rounding=ROUND_HALF_EVEN)
        rtmp = float(d)
        #if (rtmp == 0.0) and tmp < 0 and tmp > -0.25:
        #    val = ldexp(-1.0, value_format.low)
        #else:
        #    val = ldexp(rtmp, value_format.low)
        val = ldexp(rtmp, value_format.low)
    elif value_format.rounding == fixmath.roundings.truncate:
        tmp = ldexp(val, -value_format.low)
        tmp = float(floor(tmp))
        val = ldexp(tmp, value_format.low)

    if isinstance(value, int):
        return int(val)
    else:
        return val

class _GenId(object):
    _id = 0

    def __call__(self):
        newId, self._id = self._id, self._id + 1
        return str(newId)


genId = _GenId()
