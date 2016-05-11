#  This file is part of the myhdl_numeric library, a Python package for using
#  Python as a Hardware Description Language.
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
from myhdl._compat import long, integer_types
from copy import copy


class sintba(bitarray):
    def __init__(self, *args, **kwargs):
        if 'low' in kwargs:
            if kwargs['low'] != 0:
                raise TypeError("The low parameter must be 0 or None")
        else:
            kwargs['low'] = 0

        bitarray.__init__(self, *args, **kwargs)

    _signed = True

    def unsigned(self):
        return copy(self)

    def signed(self):
        return copy(self)

    def _get_max(self):
        return (long(1) << (self._high - self._low - 1))

    def _get_min(self):
        return -(long(1) << (self._high - self._low - 1))

    def _wrap(self):
        val = self._val
        lim = long(1) << (self._high - 1)
        if val & lim:
            tmp = long(-1)
        else:
            tmp = long(0)
        wrap = lim - 1
        val &= wrap
        tmp &= ~wrap
        self._val = tmp | val

    def __abs__(self):
        val = self._val
        if val < 0:
            val = -val
        return type(self)(val, self)

    def __neg__(self):
        result = type(self)(0, self)
        result._val = -self._val
        result._wrap()
        return result

    def __pos__(self):
        return type(self)(self)
        # if self._val < 0:
        #     value = -self._val
        # else:
        #     value = self._val
        # return type(self)(value, self)

    def __add__(self, other):
        length = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
            if self.is_signed and not other.is_signed:
                other = other.signed()
            value = other._val
            length = other._high
        else:
            return NotImplemented

        size = max(self._high, length)

        result = type(self)(0, high=size)
        result._val = self._val + value
        result._wrap()
        return result

    def __radd__(self, other):
        if isinstance(other, integer_types):
            return type(self)(other, self) + self
        elif isinstance(other, sintba):
            return type(self)(other) + self
        else:
            return NotImplemented

    def __sub__(self, other):
        length = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
            if self.is_signed and not other.is_signed:
                other = other.signed()
            value = other._val
            length = other._high
        else:
            return NotImplemented

        size = max(self._high, length)

        result = type(self)(0, high=size)
        result._val = self._val - value
        result._wrap()
        return result

    def __rsub__(self, other):
        if isinstance(other, integer_types):
            return type(self)(other, self) - self
        elif isinstance(other, sintba):
            return type(self)(other) - self
        else:
            return NotImplemented

    def __mul__(self, other):
        length = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
            if self.is_signed and not other.is_signed:
                other = other.signed()
            value = other._val
            length = other._high
        else:
            return NotImplemented

        size = self._high + length

        result = type(self)(0, self)
        result._high = size
        result._val = self._val * value
        result._wrap()
        return result

    def __rmul__(self, other):
        if isinstance(other, integer_types):
            return type(self)(other, self) * self
        elif isinstance(other, sintba):
            return type(self)(other) * self
        else:
            return NotImplemented

    def __floordiv__(self, other):
        if isinstance(other, integer_types):
            other_value = other
        elif isinstance(other, sintba):
            if self.is_signed and not other.is_signed:
                other = other.signed()
            other_value = other._val
        else:
            return NotImplemented
        division = self._divide(self._val, other_value)
        result = type(self)(0, self)
        result._val = division
        result._wrap()
        return result

    def __rfloordiv__(self, other):
        if isinstance(other, integer_types):
            return type(self)(other, self) // self
        elif isinstance(other, sintba):
            return type(self)(other) // self
        else:
            return NotImplemented

    def __mod__(self, other):
        size = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
            if self.is_signed and not other.is_signed:
                other = other.signed()
            value = other._val
            size = other._high
        else:
            return NotImplemented

        module = self._module(self._val, value)
        result = type(self)(0, high=size)
        result._val = module
        result._wrap()
        return result

    def __rmod__(self, other):
        if isinstance(other, integer_types):
            return type(self)(other, self) % self
        elif isinstance(other, sintba):
            return type(self)(other) % self
        else:
            return NotImplemented

    def __lshift__(self, other):
        if isinstance(other, integer_types):
            if other < 0:
                return NotImplemented
            else:
                value = other
        elif isinstance(other, sintba):
            if other._val < 0:
                return NotImplemented
            else:
                value = other._val
        else:
            return NotImplemented

        result = copy(self)
        result._val = self._val << value
        result._wrap()
        return result

    def __rlshift__(self, other):
        if isinstance(other, integer_types):
            if self._val < 0:
                return NotImplemented
            else:
                result = copy(self)
                result._val = other << self._val
                result._wrap()
                return result
        else:
            return NotImplemented

    def __rshift__(self, other):
        if isinstance(other, integer_types):
            if other < 0:
                return NotImplemented
            else:
                value = other
        elif isinstance(other, sintba):
            if other._val < 0:
                return NotImplemented
            else:
                value = other._val
        else:
            return NotImplemented

        result = copy(self)
        result._val = self._val >> value
        result._wrap()
        return result

    def __rrshift__(self, other):
        if isinstance(other, integer_types):
            if self._val < 0:
                return NotImplemented
            else:
                result = copy(self)
                result._val = other >> self._val
                result._wrap()
                return result
        else:
            return NotImplemented

    def __and__(self, other):
        if isinstance(other, sintba):
            return bitarray.__and__(self, other)
        else:
            return NotImplemented

    __rand__ = __and__

    def __or__(self, other):
        if isinstance(other, sintba):
            return bitarray.__or__(self, other)
        else:
            return NotImplemented

    __ror__ = __or__

    def __xor__(self, other):
        if isinstance(other, sintba):
            return bitarray.__xor__(self, other)
        else:
            return NotImplemented

    __rxor__ = __xor__

    def __iadd__(self, other):
        result = self + other
        if self.is_signed:
            value = result.resize(self.high, self.low)
        else:
            result = result.unsigned()
            value = result.resize(self.high + 1, self.low)
        self._val = value._val
        self._wrap()
        return self

    def __isub__(self, other):
        result = self - other
        if self.is_signed:
            value = result.resize(self.high, self.low)
        else:
            result = result.unsigned()
            value = result.resize(self.high + 1, self.low)
        self._val = value._val
        self._wrap()
        return self

    def __imul__(self, other):
        result = self * other
        if self.is_signed:
            value = result.resize(self.high, self.low)
        else:
            result = result.unsigned()
            value = result.resize(self.high + 1, self.low)
        self._val = value._val
        self._wrap()
        return self

    def __ifloordiv__(self, other):
        result = self // other
        if self.is_signed:
            value = result.resize(self.high, self.low)
        else:
            result = result.unsigned()
            value = result.resize(self.high + 1, self.low)
        self._val = value._val
        self._wrap()
        return self

    def __imod__(self, other):
        result = self % other
        if self.is_signed:
            value = result.resize(self.high, self.low)
        else:
            result = result.unsigned()
            value = result.resize(self.high + 1, self.low)
        self._val = value._val
        self._wrap()
        return self

    def __int__(self):
        return int(self._val)

    def __long__(self):
        return long(self._val)

    def __float__(self):
        return float(self._val)

    def __oct__(self):
        return oct(long(self._val))

    def __hex__(self):
        return hex(long(self._val))

    def __index__(self):
        return long(self._val)

    # comparisons
    def __eq__(self, other):
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
            value = other._val
        else:
            return NotImplemented
        return self._val == value

    def __ne__(self, other):
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
            value = other._val
        else:
            return NotImplemented
        return self._val != value

    def __lt__(self, other):
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
            value = other._val
        else:
            return NotImplemented
        return self._val < value

    def __le__(self, other):
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
            value = other._val
        else:
            return NotImplemented
        return self._val <= value

    def __gt__(self, other):
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
            value = other._val
        else:
            return NotImplemented
        return self._val > value

    def __ge__(self, other):
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
            value = other._val
        else:
            return NotImplemented
        return self._val >= value

    # representation
    def __repr__(self):
        return type(self).__name__ + \
                "({0:#x}, high={1})".format(self._val, self._high)

    def resize(self, *args):
        length = len(args)
        value = self
        if length == 1:
            value_format = args[0]
            if isinstance(value_format, integer_types):
                high = value_format
                low = 0
            else:
                high = value_format.high
                low = value_format.low
        elif length == 2:
            high = args[0]
            low = args[1]
        else:
            raise TypeError("Incorrect number of arguments")
        result = copy(value)
        result._high = high
        result._low = low
        result._resize(value)
        result._wrap()
        return result
