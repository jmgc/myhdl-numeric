from math import floor, fmod, ldexp
from decimal import Decimal, ROUND_HALF_EVEN
from myhdl import fixmath
import hashlib


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
    lim = (1 << (value_format.high - value_format.low - 1))
    lim_neg = -ldexp(lim, value_format.low)
    lim_pos = ldexp(lim - 1, value_format.low)
    margin = ldexp(1.0, value_format.high)

    rounding = False

    if value_format.overflow == fixmath.overflows.saturate:
        if val > lim_pos:
            val = lim_pos
        elif val < lim_neg:
            val = lim_neg
        else:
            rounding = True
    elif value_format.overflow == fixmath.overflows.wrap:
        if val <= -lim_neg or val > lim_pos:
            val = fmod(val, margin)
        if val < -lim_neg:
            val += margin
        elif val > lim_pos:
            val -= margin
        rounding = True

    if rounding and value_format.rounding == fixmath.roundings.round:
        tmp = ldexp(val, -value_format.low)
        # str_tmp = '{0:.4f}'.format(tmp)
        d = Decimal(tmp).quantize(0, rounding=ROUND_HALF_EVEN)
        rtmp = float(d)
        # if (rtmp == 0.0) and tmp < 0 and tmp > -0.25:
        #    val = ldexp(-1.0, value_format.low)
        # else:
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


def gen_id(*values):
    h = hashlib.blake2b(digest_size=16)
    for value in values:
        h.update(str(value).encode('ascii'))
    return h.hexdigest()
