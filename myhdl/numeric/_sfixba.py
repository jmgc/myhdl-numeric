#  This file is part of the myhdl_numeric library, a Python package for using
#  Python as a Hardware Description Language with special care of number
#  properties. The type sfixba is fully based on the sfixed VHDL type code
#  written by David Bishop.
#
#  Copyright (C) 2015 Jase M. Gomez
#
#  The myhdl_numeric library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public License as
#  published by the Free Software Foundation; either version 2.1 of the
#  License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.

#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

from __future__ import absolute_import, division
from ._bitarray import bitarray
from ._sintba import sintba


from .._compat import long, integer_types, string_types, bit_length
from .._enum import enum
from .._intbv import intbv

from math import frexp, modf, ldexp, isinf, copysign
from copy import copy
import warnings


class fixmath(object):
    """Fixed Point math

    Attributes:
        overflow: overflow mode. It can be any of the
          py:const:`fixmath.overflows.saturate` or
          py:const:`fixmath.overflows.wrap`. The default value is the
          py:const:`fixmath.overflows` one.
        rounding: rounding mode. It can be any of the
          py:const:`fixmath.overflows.round` or
          py:const:`fixmath.overflows.truncate`. The default value is the
          py:class:`fixmath.overflows` one.
        guard_bits: guard bits. An integer that stores the number of guard
          bits. The default value is the
          py:class:`fixmath.guard_bits` one.
    """

    overflows = enum('saturate', 'wrap')
    roundings = enum('round', 'truncate')

    def __init__(self, overflow=None, rounding=None, guard_bits=None):
        if hasattr(fixmath.overflows, str(overflow)):
            self._overflow = overflow
        else:
            self._overflow = self.overflows.saturate

        if hasattr(fixmath.roundings, str(rounding)):
            self._rounding = rounding
        else:
            self._rounding = self.roundings.round

        if isinstance(guard_bits, integer_types):
            self._guard_bits = int(guard_bits)
        else:
            self._guard_bits = 3

    # support for the 'overflow', 'rounding' and 'guard_bits' attributes

    def _get_overflow(self):
        return self._overflow
    overflow = property(_get_overflow, None)

    def _get_rounding(self):
        return self._rounding
    rounding = property(_get_rounding, None)

    def _get_guard_bits(self):
        return self._guard_bits
    guard_bits = property(_get_guard_bits, None)


class sfixba(bitarray):
    """Fixed Point bit array

    Arguments:
        value: value that will be stored, it can be an integer or a floating
          point value. If no more arguments are provided, the sfixba will be
          created with the minimum size needed to store the value.
        high: number of the integer part bits. The integer bits will start
          with the 0 index until high-1.
        low: number of fraction part bits. The fraction bits will start
          with the index -1 until low.
        overflow: overflow mode. It can be any of the
          py:const:`fixmath.overflows.saturate` or
          py:const:`fixmath.overflows.wrap`. The default value is the
          py:const:`fixmath.overflows` one.
        rounding: rounding mode. It can be any of the
          py:const:`fixmath.overflows.round` or
          py:const:`fixmath.overflows.truncate`. The default value is the
          py:class:`fixmath.overflows` one.
        guard_bits: guard bits. An integer that stores the number of guard
          bits. The default value is the
          py:class:`fixmath.guard_bits` one.

    Any of the previous arguments can be substituted by a fixmath object. In
    which case, the pending arguments will be substituted by the fixmath
    values.

    Also, any of the previous arguments can be substituted by a sfixba object.
    In this case, if a previous fixmath object has been provided, the pending
    sfixba arguments will be substituted by the fixmath object ones, and if
    they are not available, by the sfixba object ones. In any other case, the
    pending arguments will be substituted by the sfixba ones.
    """

    def __init__(self, *args, **kwargs):
        value = 0
        high = None
        low = None
        overflow = None
        rounding = None
        guard_bits = None
        maths = None
        value_format = None

        i = -1
        for i, arg in enumerate(args):
            if i > 0:
                if isinstance(arg, fixmath):
                    maths = arg
                    break
                elif isinstance(arg, sfixba):
                    value_format = arg
                    maths = arg
                    break
            if i == 0:
                value = arg
            elif i == 1:
                high = arg
            elif i == 2:
                low = arg
            elif i == 3:
                overflow = arg
            elif i == 4:
                rounding = arg
            elif i == 5:
                guard_bits = int(arg)
            else:
                raise TypeError("Too much positional arguments")

        if isinstance(value, bitarray):
            if not value.is_signed:
                value = value.signed()
            if value_format is None:
                value_format = value

        if 'maths' in kwargs:
            maths = kwargs['maths']
        elif maths is None:
            if isinstance(value_format, sfixba):
                maths = value_format
            else:
                maths = fixmath()

        length = len(args)
        if length != (i + 1):
                raise TypeError("No positional arguments allowed after "
                                "format or fixmath object")
        if (length == 0) and ('value' in kwargs):
            value = kwargs['value']

        if high is None:
            if ('high' in kwargs):
                high = kwargs['high']
            elif value_format is not None:
                high = value_format.high

        if low is None:
            if ('low' in kwargs):
                low = kwargs['low']
            elif value_format is not None:
                low = value_format.low

        if 'overflow' in kwargs:
            if overflow is None:
                overflow = kwargs['overflow']
            else:
                raise TypeError("Conflict of overflow definition")
        if overflow is None:
            self._overflow = maths.overflow
        else:
            if hasattr(fixmath.overflows, str(overflow)):
                self._overflow = overflow
            else:
                raise TypeError("Unknown overflow type")

        if 'rounding' in kwargs:
            if rounding is None:
                rounding = kwargs['rounding']
            else:
                raise TypeError("Conflict of rounding definition")
        if rounding is None:
            self._rounding = maths.rounding
        else:
            if hasattr(fixmath.roundings, str(rounding)):
                self._rounding = rounding
            else:
                raise TypeError("Unknown overflow type")

        if 'guard_bits' in kwargs:
            if guard_bits is None:
                guard_bits = kwargs['guard_bits']
            else:
                raise TypeError("Conflict of guard_bits definition")
        if guard_bits is None:
            self._guard_bits = maths.guard_bits
        else:
            if (not isinstance(guard_bits, integer_types)) or \
                    (guard_bits < 0):
                raise TypeError("Guard_bits must be a natural value")
            else:
                self._guard_bits = guard_bits

        if isinstance(value, integer_types):
            if value == 0:
                self._zero(value, high, low)
            else:
                self._from_int(value, high, low)
        elif isinstance(value, float):
            if value == 0.0:
                self._zero(value, high, low)
            else:
                self._from_float(value, high, low)
        elif isinstance(value, string_types):
            if ('1' in value) or ('-' in value):
                self._from_string(value, high, low)
            else:
                self._zero(value, high, low)
        elif isinstance(value, intbv):
            self._from_int(int(value), len(value), 0)
        elif isinstance(value, bitarray):
            if value._val == 0:
                self._zero(value, high, low)
            else:
                self._from_bitarray(value, high, low)
        else:
            raise TypeError("sfixba constructor val should be float, int, "
                            "string or bitarray child:"
                            " {0}".format(type(value)))

    _signed = True

    def _from_int(self, value, high, low):
        val = long(value)

        length = bit_length(val)

        if length == 0:
            val = long(0)
            length = 1

        length += 1  # Add the sign bit

        if low is None:
            low = 0

        self._handle_limits(high, low, length)

        if self._high >= 0:
            if (abs(val) >> self._high != 0):
                warnings.warn("Truncated int number {0}, "
                              "length: {1}".format(value, self._high),
                              RuntimeWarning, stacklevel=2)
            value = bitarray(val, length, 0)
            self._resize(value)
            self._wrap()
        else:
            self._val = 0

    def _convert_float_limits(self, arg, high, low,
                              overflow_style=None,
                              round_style=None,
                              guard_bits=None):
        left_index = high   # size of integer portion
        right_index = low   # size of fraction
        if not hasattr(fixmath.overflows, str(overflow_style)):
            overflow_style = self._overflow
        if not hasattr(fixmath.roundings, str(round_style)):
            round_style = self._rounding
        if guard_bits is not integer_types:
            guard_bits = self._guard_bits
        fw = right_index   # catch literals
        result = bitarray(0, left_index, fw)
        Xresult = bitarray(0, left_index+1, fw-guard_bits)
        presult = 0.0

        if (arg >= ldexp(1.0, left_index - 1)) or \
                (arg < ldexp(-1.0, left_index - 1)):
            if overflow_style == fixmath.overflows.saturate:
                if arg < 0.0:   # saturate
                    self._saturate(result, True)  # underflow
                else:
                    self._saturate(result, False)      # overflow
                return result
            else:
                presult = abs(arg) % ldexp(1.0, left_index + 1)  # wrap
        else:
            presult = abs(arg)

        for i in range(Xresult.high-1, Xresult.low-1, -1):
            if presult >= ldexp(1.0, i):
                Xresult[i] = 1
                presult = presult - ldexp(1.0, i)
            else:
                Xresult[i] = 0

        if arg < 0.0:
            Xresult._val = -Xresult._val
            Xresult._wrap()

        if guard_bits > 0 and round_style == fixmath.roundings.round:
            result = self._round_fixed(Xresult[left_index:right_index],
                                       Xresult[right_index:
                                               right_index-guard_bits],
                                       overflow_style)
        else:
            result[:] = Xresult[result.high:result.low]
        return result

    def _convert_float(self, arg):
        (mantisa, f_high) = frexp(arg)

        fract = abs(mantisa)
        f_low = f_high
        while fract > 0.0:
            fract *= 2.0
            (fract, _) = modf(fract)
            f_low -= 1

        f_high += 1  # Sign bit

        mask = ((1 << (f_high - f_low)) - 1)
        if isinf(arg):
            if arg > 0.0:
                i_value = 1
            else:
                i_value = -1
            return (True, bitarray(i_value, f_high, f_low))
        else:
            i_value = long(ldexp(arg, -f_low)) & mask
            return (False, bitarray(i_value, f_high, f_low))

    def _from_float(self, value, high, low):
        if high is None or low is None:
            inf, ba_value = self._convert_float(value)
            if high is None:
                high = ba_value.high
            if low is None:
                low = ba_value.low
            self._handle_limits(high, low, len(ba_value))

            if ba_value.high > self._high:
                warnings.warn("Truncated floating "
                              "point number {0}".format(value),
                              RuntimeWarning, stacklevel=2)

            if inf:
                if value > 0.0:
                    self._val = self.max - 1
                else:
                    self._val = self.min
            else:
                self._resize(ba_value, self.overflow, self.rounding)
        else:
            inf, ba_value = self._convert_float(value)
            self._handle_limits(high, low, len(ba_value))
            if inf:
                if value > 0.0:
                    self._val = self.max - 1
                else:
                    self._val = self.min
            else:
                self._resize(ba_value, self.overflow, self.rounding)

        self._wrap()

    def _convert_string(self, value):
        dec_point = False
        mval = value
        if '__' in mval:
            warnings.warn("At least two __ in the string: " + mval,
                          RuntimeWarning, stacklevel=2)
            raise ValueError("")
        if mval[0] in ('+', '-'):
            warnings.warn("No sign point allowed in sfixba "
                          "binary representation: " + mval,
                          RuntimeWarning, stacklevel=2)
        mval = mval.replace('_', '')
        low = 0
        high = len(mval)
        if '.' in mval:
            dec_point = True
            dec = mval.index('.')
            mval = mval[:dec] + mval[dec+1:]
            high -= 1
            low = dec - high
            high += low
            if '.' in mval:
                warnings.warn("Two binary points: " + mval,
                              RuntimeWarning, stacklevel=2)
        i_value = long(mval, 2)

        return (bitarray(i_value, high, low), dec_point)

    def _from_string(self, value, high, low):
        (ba_value, dec_point) = self._convert_string(value)

        length = len(ba_value)

        if dec_point:
            if high is None:
                high = ba_value.high
            if low is None:
                low = ba_value.low

        self._handle_limits(high, low, length)

        if dec_point and (self._low != ba_value.low):
            warnings.warn("Decimal point place in the string is "
                          "different from the one requested: "
                          "{}, ".fomat(self._low) + value,
                          RuntimeWarning, stacklevel=2)

        ba_length = self._high - self._low

        if (length > ba_length):
            warnings.warn("String is truncated" + value,
                          RuntimeWarning, stacklevel=2)

        self._val = ba_value._val

        self._wrap()

#    def _from_bitarray(self, value, high, low):
#        self._handle_limits(high, low, len(value))
#        self._resize(value)
#        self._handle_bounds()

    def _saturate(self, arg, sign=False):
        val = (1 << (arg.high - arg.low - 1)) - 1
        if sign:
            arg._val = ~val
        else:
            arg._val = val

    def _resize(self, val, overflow=None, rounding=None):
        if overflow is None or not hasattr(fixmath.overflows, str(overflow)):
            overflow_style = self._overflow
        else:
            overflow_style = overflow
        if rounding is None or not hasattr(fixmath.roundings, str(rounding)):
            rounding_style = self._rounding
        else:
            rounding_style = rounding

        arghigh = val._high
        arglow = val._low
        left_index = self._high
        right_index = self._low

        needs_rounding = False
        result = bitarray(0, left_index, right_index)

        if left_index <= right_index:
            raise TypeError('The result value must have a size')
        else:
            invec = bitarray(val)
            if right_index >= arghigh:  # return sign expansion
                if val[arghigh - 1]:
                    result[:] = -1
                if rounding_style == fixmath.roundings.round:
                    if right_index == arghigh:
                        needs_rounding = True
                    else:
                        needs_rounding = False
                        result[:] = 0
                else:
                    needs_rounding = False
            elif left_index <= arglow:  # return overflow
                if overflow_style == fixmath.overflows.saturate:
                    reduced = (invec.or_reduce())
                    if reduced:
                        self._saturate(result, invec[arghigh - 1])
                    # else return 0 (input was 0)
                # else return 0 (wrap)
            elif arghigh > left_index:
                if not invec[arghigh - 1]:
                    reduced = (invec[arghigh - 1:left_index-1].or_reduce())
                    if (overflow_style == fixmath.overflows.saturate) and \
                            reduced:
                        # saturate positive
                        self._saturate(result)
                    else:
                        if right_index > arglow:
                            result[:] = invec[left_index:right_index]
                            needs_rounding = (rounding_style ==
                                              fixmath.roundings.round)
                        else:
                            result[left_index:arglow] = \
                                    invec[left_index:arglow]
                else:
                    reduced = invec[arghigh - 1:left_index - 1].and_reduce()
                    if (overflow_style == fixmath.overflows.saturate) and \
                            not reduced:
                        self._saturate(result, True)
                    else:
                        if right_index > arglow:
                            result[:] = invec[left_index:right_index]
                            needs_rounding = (rounding_style ==
                                              fixmath.roundings.round)
                        else:
                            result[left_index:arglow] = \
                                    invec[left_index:arglow]
            else:  # arghigh <= integer width
                if (arglow >= right_index):
                    result[arghigh:arglow] = invec
                else:
                    result[arghigh:right_index] = \
                            invec[arghigh:right_index]
                    needs_rounding = (rounding_style ==
                                      fixmath.roundings.round)
                if (left_index > arghigh):  # sign extend
                    if invec[arghigh - 1]:
                        value = (long(1) << (left_index - arghigh)) - 1
                    else:
                        value = 0
                    result[left_index:arghigh] = value
            # Round result
            if (needs_rounding):
                result[:] = self._round_fixed(result,
                                              invec[right_index:arglow],
                                              overflow_style)
            self._val = result._val

    # Rounding - Performs a "round_nearest" (IEEE 754) which rounds up
    # when the remainder is > 0.5.  If the remainder IS 0.5 then if the
    # bottom bit is a "1" it is rounded, otherwise it remains the same.

    def _round_fixed(self, arg, remainder, overflow_style=None):
        if not hasattr(fixmath.overflows, str(overflow_style)):
            overflow_style = self._overflow
        rounds = False
        round_overflow = False
        if len(remainder) > 1:
            if remainder[remainder.high - 1]:
                rounds = arg[arg.low] or \
                        remainder[remainder.high-1:remainder.low].or_reduce()
        else:
            rounds = arg[arg.low] and remainder[remainder.high - 1]
        if rounds:
            result, round_overflow = self._round_up(arg)
        else:
            result = arg
        if round_overflow:
            if overflow_style == fixmath.overflows.saturate:
                self._saturate(result, arg[arg.high - 1])
                # Sign bit not fixed when wrapping
        return result

    def _round_up(self, arg):
        args = sintba(arg._val, len(arg) + 1)
        ress = args + 1
        result = bitarray(0, arg)
        result[:] = ress[ress.high-1:0]
        overflowx = ((arg[arg.high - 1] != ress[ress.high - 2]) and
                     ress.or_reduce())
        return (result, overflowx)

    def _get_max(self):
        return (long(1) << (self._high - self._low - 1))

    def _get_min(self):
        return -(long(1) << (self._high - self._low - 1))

    def _get_overflow(self):
        return self._overflow
    overflow = property(_get_overflow, None)

    def _get_rounding(self):
        return self._rounding
    rounding = property(_get_rounding, None)

    def _get_guard_bits(self):
        return self._guard_bits
    guard_bits = property(_get_guard_bits, None)

    def _wrap(self):
        length = self._high - self._low

        lim = long(1) << (length - 1)
        if self._val & lim:
            tmp = long(-1)
        else:
            tmp = long(0)
        wrap = lim - 1
        self._val &= wrap
        tmp &= ~wrap
        self._val = tmp | self._val

    def __abs__(self):
        if self._val < 0:
            val = -self._val
        else:
            val = self._val
        result = type(self)(0, self, high=self._high + 1)
        result._val = val
        return result

    def __neg__(self):
        result = type(self)(0, self, high=self._high + 1)
        result._val = -self._val
        return result

    def __pos__(self):
        return type(self)(self)

    def __add__(self, other):
        if isinstance(other, integer_types):
            value = sfixba(other, self)
        elif isinstance(other, float):
            value = sfixba(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = sfixba(other, maths=self)
        else:
            return NotImplemented
        high = max(self._high, value._high) + 1
        low = min(self._low, value._low)
        l = self.resize(high, low)
        r = value.resize(high, low)
        result = type(self)(0, high=high, low=low)
        result._val = l._val + r._val
        return result

    def __radd__(self, other):
        if isinstance(other, integer_types):
            value = sfixba(other, self)
        elif isinstance(other, float):
            value = sfixba(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = sfixba(other, maths=self)
        else:
            return NotImplemented
        return value + self

    def __sub__(self, other):
        if isinstance(other, integer_types):
            value = sfixba(other, self)
        elif isinstance(other, float):
            value = sfixba(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = sfixba(other, maths=self)
        else:
            return NotImplemented
        high = max(self._high, value._high) + 1
        low = min(self._low, value._low)
        l = self.resize(high, low)
        r = value.resize(high, low)
        result = type(self)(0, high=high, low=low)
        result._val = l._val - r._val
        return result

    def __rsub__(self, other):
        if isinstance(other, integer_types):
            value = sfixba(other, self)
        elif isinstance(other, float):
            value = sfixba(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = sfixba(other, maths=self)
        else:
            return NotImplemented
        return value - self

    def __mul__(self, other):
        if isinstance(other, integer_types):
            value = sfixba(other, self)
        elif isinstance(other, float):
            value = sfixba(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = sfixba(other, maths=self)
        else:
            return NotImplemented
        high = self._high + value._high + 1
        low = self._low + value._low
        l = self
        r = value
        result = type(self)(0, high=high, low=low)
        result._val = l._val * r._val
        return result

    def __rmul__(self, other):
        if isinstance(other, integer_types):
            value = sfixba(other, self)
        elif isinstance(other, float):
            value = sfixba(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = sfixba(other, maths=self)
        else:
            return NotImplemented
        return value * self

    def __truediv__(self, other):
        if isinstance(other, integer_types):
            value = sfixba(other, self)
        elif isinstance(other, float):
            value = sfixba(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = sfixba(other, maths=self)
        else:
            return NotImplemented
        high = self._high - value._low + 1
        low = self._low - value._high + 1
        if value._val == 0:
            result = sfixba(0, high, low)
            if self._val >= 0:
                result._val = result.max - 1
            else:
                result._val = result.min
        else:
            l = self.resize(self._high + 1,
                            self._high - (high - low + self._guard_bits) + 1,
                            fixmath(overflow=fixmath.overflows.wrap,
                                    rounding=fixmath.roundings.truncate))
            division = self._divide(l._val, value._val)
            dresult = sfixba(0, high, low - self._guard_bits)
            dresult._val = division
            result = dresult.resize(high, low, self)
        return result

    def __rtruediv__(self, other):
        if isinstance(other, integer_types):
            value = sfixba(other, self)
        elif isinstance(other, float):
            value = sfixba(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = sfixba(other, maths=self)
        else:
            return NotImplemented
        return value / self

    def __floordiv__(self, other):
        if isinstance(other, integer_types):
            value = sfixba(other, self)
        elif isinstance(other, float):
            value = sfixba(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = sfixba(other, maths=self)
        else:
            return NotImplemented
        dresult = self / value
        result = dresult.floor()
        return result

    def __rfloordiv__(self, other):
        if isinstance(other, integer_types):
            value = sfixba(other, self)
        elif isinstance(other, float):
            value = sfixba(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = sfixba(other, maths=self)
        else:
            return NotImplemented
        return value // self

    def __mod__(self, other):
        if isinstance(other, integer_types):
            value = sfixba(other, self)
        elif isinstance(other, float):
            value = sfixba(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = sfixba(other, maths=self)
        else:
            return NotImplemented
        l_abs = abs(self)
        r_abs = abs(value)
        l_resize = l_abs.resize(max(l_abs._high, r_abs._low + 1),
                                r_abs._low - self._guard_bits,
                                fixmath(overflow=fixmath.overflows.wrap,
                                        rounding=fixmath.roundings.truncate))
        r_resize = r_abs.resize(r_abs._high,
                                r_abs._low - self._guard_bits,
                                fixmath(overflow=fixmath.overflows.wrap,
                                        rounding=fixmath.roundings.truncate))
        rem_result = sfixba(0, r_resize)

        high = value._high
        low = min(value._low, self._low)
        result = sfixba(0, high, low)
        if r_resize._val == 0:
            if l_resize._val >= 0:
                result._val = result.max
            else:
                result._val = result.min
            return result

        dresult = sfixba(0, min(self._high, value._high) + 1,
                         min(self._low, value._low))
        if r_abs._low < l_abs._high:
            rem_result._val = l_resize._val % r_resize._val
            dresult = rem_result.resize(dresult.high, dresult.low,
                                        fixmath(overflow=fixmath
                                                .overflows.wrap,
                                                rounding=self.rounding))
        if l_abs._low < r_abs._low:
            dhigh = min(r_abs._low, l_abs._high)
            dresult[dhigh:l_abs._low] = l_abs[dhigh:l_abs._low]

        if dresult._val == 0:
            dresult_not_zero = False
        else:
            dresult_not_zero = True

        if (self._val < 0) and (value._val >= 0) and \
                dresult_not_zero:
            result._resize(value - dresult)
        elif (self._val < 0) and (value._val < 0):
            result._resize(-dresult)
        elif (self._val >= 0) and (value._val < 0) and \
                dresult_not_zero:
            result._resize(dresult + value)
        else:
            result._resize(dresult)
        result._wrap()
        return result

    def __rmod__(self, other):
        if isinstance(other, integer_types):
            value = sfixba(other, self)
        elif isinstance(other, float):
            value = sfixba(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = sfixba(other, maths=self)
        else:
            return NotImplemented
        return value % self

    def __pow__(self, other):
        return NotImplemented

    def __rpow__(self, other):
        return NotImplemented

    def __and__(self, other):
        if isinstance(other, (sintba, sfixba)):
            return bitarray.__and__(self, other)
        else:
            return NotImplemented

    __rand__ = __and__

    def __or__(self, other):
        if isinstance(other, (sintba, sfixba)):
            return bitarray.__or__(self, other)
        else:
            return NotImplemented

    __ror__ = __or__

    def __xor__(self, other):
        if isinstance(other, (sintba, sfixba)):
            return bitarray.__xor__(self, other)
        else:
            return NotImplemented

    __rxor__ = __xor__

    def __iadd__(self, other):
        if isinstance(other, bitarray) and \
                self.is_signed and not other.is_signed:
            other = other.signed()
        result = self + other
        if not self.is_signed:
            result = result.unsigned()
        value = result.resize(self.high, self.low)
        self._val = value._val
        self._wrap()
        return self

    def __isub__(self, other):
        if isinstance(other, bitarray) and \
                self.is_signed and not other.is_signed:
            other = other.signed()
        result = self - other
        if not self.is_signed:
            result = result.unsigned()
        value = result.resize(self.high, self.low)
        self._val = value._val
        self._wrap()
        return self

    def __imul__(self, other):
        if isinstance(other, bitarray) and \
                self.is_signed and not other.is_signed:
            other = other.signed()
        result = self * other
        if not self.is_signed:
            result = result.unsigned()
        value = result.resize(self.high, self.low)
        self._val = value._val
        self._wrap()
        return self

    def __ifloordiv__(self, other):
        if isinstance(other, bitarray) and \
                self.is_signed and not other.is_signed:
            other = other.signed()
        result = self // other
        if not self.is_signed:
            result = result.unsigned()
        value = result.resize(self.high, self.low)
        self._val = value._val
        self._wrap()
        return self

    def __imod__(self, other):
        if isinstance(other, bitarray) and \
                self.is_signed and not other.is_signed:
            other = other.signed()
        result = self % other
        if not self.is_signed:
            result = result.unsigned()
        value = result.resize(self.high, self.low)
        self._val = value._val
        self._wrap()
        return self

    def __ipow__(self, other, modulo=None):
        return NotImplemented

    def __invert__(self):
        result = type(self)(0, self)
        result._val = ~self._val
        return result

    def __int__(self):
        result = self.resize(self._high, 0)
        return int(result._val)

    def __long__(self):
        result = self.resize(self._high, 0)
        return long(result._val)

    def __float__(self):
        return ldexp(self._val, self._low)

    # XXX __complex__ seems redundant ??? (complex() works as such?)

    def _abs(self):
        length = self._high-self._low

        if length > 1:
            return abs(self._val)
        else:
            return 0

    def bin(self):
        val = self._abs()

        if self._high != 1 or self._low != 0:
            if self._low >= 0:
                val <<= self._low
                length = self._high - 1
                format_str = '{{0:0{0}b}}.'.format(length)
                result = format_str.format(val)
            elif self._high < 1:
                length = 1 - self._low
                format_str = '{{0:0{0}b}}'.format(length)
                result = format_str.format(val)
                result = '.' + result[1:]
            else:
                length = self._high - self._low - 1
                format_str = '{{0:0{0}b}}'.format(length)
                result = format_str.format(val)
                result = result[:self._high - 1] + '.' + \
                    result[self._high - 1:]
        else:
            result = '.'

        if self._val < 0:
            return "-0b" + result
        else:
            return "+0b" + result

    def oct(self):
        bits = 3
        if self._low < 0:
            delta = -self._low % bits

            if delta > 0:
                delta = bits - delta
                dec = 1 + (-self._low // bits)

            value = self._val << delta
            msg = oct(value)
            dec = len(msg) - dec
            msg = msg[:dec] + '.' + msg[dec:]
        else:
            value = self._val << self._low
            msg = oct(value)
        return msg

    def hex(self):
        bits = 4

        if self._high != 1 or self._low != 0:
            if self._low >= 0:
                val = self._abs() << self._low
                length = self._high - 1
                h_length = length // bits
                h_rem = length % bits
                if h_rem > 0:
                    h_length += 1
                result = '{0:x}.'.format(val)
            elif self._high < 1:
                length_ = self._low
                h_length = length_ // bits
                h_rem = length_ % bits
                val = self._abs() << h_rem
                format_str = '.{{0:0{0}x}}'.format(-h_length)
                result = format_str.format(val)
            else:
                h_low = self._low // bits
                h_rem = self._low % bits
                val = self._abs() << h_rem
                h_high = (self._high - 1) // bits
                h_rem = (self._high - 1) % bits
                if h_rem > 0:
                    h_high += 1
                format_str = '{{0:0{0}x}}'.format(h_high - h_low)
                result = format_str.format(val)
                result = result[:h_high] + '.' + result[h_high:]
        else:
            result = '.'

        if self._val < 0:
            result = '-' + "0x" + result
        else:
            result = '+' + "0x" + result

        return result

    __oct__ = __hex__ = __index__ = bitarray._not_implemented_unary

    # comparisons
    def __eq__(self, other):
        if isinstance(other, integer_types):
            value = type(self)(other, self)
        elif isinstance(other, float):
            value = type(self)(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = type(self)(other, maths=self)
        else:
            return NotImplemented
        high = max(self._high, value._high)
        low = min(self._low, value._low)
        l = self.resize(high, low)
        r = value.resize(high, low)
        return l._val == r._val

    def __ne__(self, other):
        if isinstance(other, integer_types):
            value = type(self)(other, self)
        elif isinstance(other, float):
            value = type(self)(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = type(self)(other, maths=self)
        else:
            return NotImplemented
        high = max(self._high, value._high)
        low = min(self._low, value._low)
        l = self.resize(high, low)
        r = value.resize(high, low)
        return l._val != r._val

    def __lt__(self, other):
        if isinstance(other, integer_types):
            value = type(self)(other, self)
        elif isinstance(other, float):
            value = type(self)(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = type(self)(other, maths=self)
        else:
            return NotImplemented
        high = max(self._high, value._high)
        low = min(self._low, value._low)
        l = self.resize(high, low)
        r = value.resize(high, low)
        return l._val < r._val

    def __le__(self, other):
        if isinstance(other, integer_types):
            value = type(self)(other, self)
        elif isinstance(other, float):
            value = type(self)(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = type(self)(other, maths=self)
        else:
            return NotImplemented
        high = max(self._high, value._high)
        low = min(self._low, value._low)
        l = self.resize(high, low)
        r = value.resize(high, low)
        return l._val <= r._val

    def __gt__(self, other):
        if isinstance(other, integer_types):
            value = type(self)(other, self)
        elif isinstance(other, float):
            value = type(self)(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = type(self)(other, maths=self)
        else:
            return NotImplemented
        high = max(self._high, value._high)
        low = min(self._low, value._low)
        l = self.resize(high, low)
        r = value.resize(high, low)
        return l._val > r._val

    def __ge__(self, other):
        if isinstance(other, integer_types):
            value = type(self)(other, self)
        elif isinstance(other, float):
            value = type(self)(other, self)
        elif isinstance(other, sfixba):
            value = other
        elif isinstance(other, bitarray):
            value = type(self)(other, maths=self)
        else:
            return NotImplemented
        high = max(self._high, value._high)
        low = min(self._low, value._low)
        l = self.resize(high, low)
        r = value.resize(high, low)
        return l._val >= r._val

    # representation

    def __str__(self):
        length = self._high - self._low
        val = self._val & ((1 << length) - 1)

        if self._high != 1 or self._low != 0:
            if self._low >= 0:
                format_str = '{{0:0{0}b}}'.format(length)
                result = format_str.format(val)
            elif self._high <= 0:
                format_str = '{{0:0{0}b}}'.format(length)
                result = format_str.format(val)
                if self._high == 0:
                    result = '.' + result
            else:
                format_str = '{{0:0{0}b}}'.format(length)
                result = format_str.format(val)
                result = result[:self._high] + '.' + \
                    result[self._high:]
        else:
            result = '.'

        return result

    def __repr__(self):
        return "{0}({1}, high={2}, low={3})".format(type(self).__name__,
                                                    self.hex(),
                                                    self._high,
                                                    self._low)

    def resize(self, *args):
        length = len(args)
        value = self
        if length == 1:
            value_format = args[0]
            high = value_format.high
            low = value_format.low
            maths = value_format
        elif length > 1:
            high = args[0]
            low = args[1]
            maths = value
        if length > 2:
            maths = args[2]
        if length > 3 or length < 1:
            raise TypeError("Incorrect number of arguments")
        if not isinstance(maths, (fixmath, sfixba)):
            maths = fixmath()
        result = copy(value)
        result._high = high
        result._low = low
        result._resize(value, maths.overflow, maths.rounding)
        result._wrap()
        return result

    def scalb(self, n):
        '''Scales the result by a power of 2.  Width of input = width of
        output with the binary point moved.'''
        if isinstance(n, (integer_types, sintba)):
            value = int(n)
            result = sfixba(0, self._high + value, self._low + value)
            result._val = self._val
            return result
        else:
            raise TypeError("The scale factor must be integer or sintba")

    def floor(self):
        high = max(self.high, 2)
        result = sfixba(self).resize(high, 0, fixmath(
                                     rounding=fixmath.roundings.truncate))
        return result

    def abs(self):
        return self.__abs__()

    def unsigned(self):
        return self.__abs__()

    def signed(self):
        return copy(self)
