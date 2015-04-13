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

import warnings


class sintba(bitarray):
    def __init__(self, *args, **kwargs):
        value, high, low = self._get_arguments(*args, **kwargs)

        if low is None:
            if (high is not None):
                low = getattr(high, 'low', 0)
                high = getattr(high, 'high', high)
            else:
                low = 0

        if low != 0:
            raise TypeError("The low parameter must be 0 or None " \
                            "{}".format(low))

        bitarray.__init__(self, value, high, low)

    def _from_int(self, value, high, low=0):
        val = long(value)

        length = val.bit_length()

        if length == 0:
            self._val = long(0)
            length = 1
        else:
            self._val = long(val)

        length += 1  # Add the sign bit

        self._handle_limits(high, low, length)

        self_length = self._high - self._low
        
        if (abs(self._val) >> self_length != 0):
            warnings.warn("Integer truncated: val, len = " \
                          "{}, {}". format(self._val, len(self)),
                          RuntimeWarning)

        self._wrap()

    def _resize(self, value):
        if value < 0:
            result = type(self)(-1, self)
        else:
            result = type(self)(0, self)
        bound = min(value.high, result.high)-1
        if bound > 0:
            result[bound:] = value[bound:]
        self._val = result._val

    def _get_max(self):
        return (long(1) << (self._high - self._low - 1))

    def _get_min(self):
        return -(long(1) << (self._high - self._low - 1))

    def _wrap(self):
        val = self._val
        length = self._high - self._low
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

    def __add__(self, other):
        length = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
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
        else:
            return NotImplemented

    def __sub__(self, other):
        length = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
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
        else:
            return NotImplemented

    def __mul__(self, other):
        length = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
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
        else:
            return NotImplemented

    def __floordiv__(self, other):
        if isinstance(other, integer_types):
            other_value = other
        elif isinstance(other, sintba):
            other_value = other._val
        else:
            return NotImplemented
        
        self_value = self._val
        
        neg_quot = False
        
        if other_value < 0:
            other_value = -other_value
            neg_quot = True
        if self_value < 0:
            self_value = -self_value
            neg_quot = not neg_quot

        division = self_value // other_value
        
        if neg_quot:
            division = -division
            
        result = type(self)(0, self)
        result._val = division
        result._wrap()
        return result

    def __rfloordiv__(self, other):
        if isinstance(other, integer_types):
            return type(self)(other, self) // self
        else:
            return NotImplemented

    def __mod__(self, other):
        length = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
            value = other._val
            length = other._high
        else:
            return NotImplemented
        
        size = length
        
        result = type(self)(0, high=size)
        result._val = self._val % value
        result._wrap()
        return result

    def __rmod__(self, other):
        if isinstance(other, integer_types):
            return type(self)(other, self) % self
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
            value = other
        else:
            return NotImplemented

        return bitarray.__and__(self, value)            

    __rand__ = __and__

    def __or__(self, other):
        if isinstance(other, sintba):
            value = other
        else:
            return NotImplemented

        return bitarray.__or__(self, value)            

    __ror__ = __or__

    def __xor__(self, other):
        if isinstance(other, sintba):
            value = other
        else:
            return NotImplemented

        return bitarray.__xor__(self, value)            

    __rxor__ = __xor__

    def __iadd__(self, other):
        if not isinstance(other, (integer_types, sintba)):
            return NotImplemented
        
        result = self + other
        if result.high < self._high or result.low > self._low:
            result = result.resize(self._high, self._low)
        elif result.high < self._high:
            result = result.resize(self._high, result.low)
        elif result.low > self._low:
            result = result.resize(result.high, self._low)
        value = result[self._high:self._low]
        self._val = value._val
        self._wrap()
        return self

    def __isub__(self, other):
        if not isinstance(other, (integer_types, sintba)):
            return NotImplemented
        
        result = self - other
        if result.high < self._high or result.low > self._low:
            result = result.resize(self._high, self._low)
        elif result.high < self._high:
            result = result.resize(self._high, result.low)
        elif result.low > self._low:
            result = result.resize(result.high, self._low)
        value = result[self._high:self._low]
        self._val = value._val
        self._wrap()
        return self

    def __imul__(self, other):
        if not isinstance(other, (integer_types, sintba)):
            return NotImplemented
        
        result = self * other
        if result.high < self._high or result.low > self._low:
            result = result.resize(self._high, self._low)
        elif result.high < self._high:
            result = result.resize(self._high, result.low)
        elif result.low > self._low:
            result = result.resize(result.high, self._low)
        value = result[self._high:self._low]
        self._val = value._val
        self._wrap()
        return self

    def __ifloordiv__(self, other):
        if not isinstance(other, (integer_types, sintba)):
            return NotImplemented
        
        result = self // other
        if result.high < self._high or result.low > self._low:
            result = result.resize(self._high, self._low)
        elif result.high < self._high:
            result = result.resize(self._high, result.low)
        elif result.low > self._low:
            result = result.resize(result.high, self._low)
        value = result[self._high:self._low]
        self._val = value._val
        self._wrap()
        return self

    def __imod__(self, other):
        if not isinstance(other, (integer_types, sintba)):
            return NotImplemented
        
        result = self % other
        if result.high < self._high or result.low > self._low:
            result = result.resize(self._high, self._low)
        elif result.high < self._high:
            result = result.resize(self._high, result.low)
        elif result.low > self._low:
            result = result.resize(result.high, self._low)
        value = result[self._high:self._low]
        self._val = value._val
        self._wrap()
        return self

    def __ilshift__(self, other):
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

        self._val = self._val << value
        self._wrap()
        return self

    def __irshift__(self, other):
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

        self._val = self._val >> value
        self._wrap()
        return self

    def __iand__(self, other):
        if isinstance(other, sintba):
            value = other.resize(self)
        else:
            return NotImplemented

        return bitarray.__iand__(self, value)            

    def __ior__(self, other):
        if isinstance(other, sintba):
            value = other.resize(self)
        else:
            return NotImplemented

        return bitarray.__ior__(self, value)            

    def __ixor__(self, other):
        if isinstance(other, sintba):
            value = other.resize(self)
        else:
            return NotImplemented

        return bitarray.__ixor__(self, value)            

    def __pos__(self):
        if self._val < 0:
            value = -self._val
        else:
            value = self._val
        return type(self)(value, self)

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
            return self._val == other
        elif isinstance(other, bitarray):
            if ((self._low >= other.high) or \
                    (self._high <= other.low)):
                return (self._val == 0) and (other.__index__() == 0)
            else:
                if other.low < 0:
                    check = self._val << -other.low
                    return check == other.__index__()
                else:
                    check = other.__index__() << other.low
                    return check == self._val
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, integer_types):
            return self._val != other
        elif isinstance(other, bitarray):
            if ((self._low >= other.high) or \
                    (self._high <= other.low)):
                return (self._val != 0) or (other.__index__() != 0)
            else:
                if other.low < 0:
                    check = self._val << -other.low
                    return check != other.__index__()
                else:
                    check = other.__index__() << other.low
                    return check != self._val
        else:
            return NotImplemented


    def __lt__(self, other):
        if isinstance(other, integer_types):
            return self._val < other
        elif isinstance(other, bitarray):
            if self._low >= other.high:
                return self._val < 0
            elif self._high <= other.low:
                return 0 < other.__index__()
            else:
                if other.low < 0:
                    check = self._val << -other.low
                    return check < other.__index__()
                else:
                    check = other.__index__() << other.low
                    return self._val < check
        else:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, integer_types):
            return self._val <= other
        elif isinstance(other, bitarray):
            if self._low >= other.high:
                return self._val <= 0
            elif self._high <= other.low:
                return 0 <= other.__index__()
            else:
                if other.low < 0:
                    check = self._val << -other.low
                    return check <= other.__index__()
                else:
                    check = other.__index__() << other.low
                    return self._val <= check
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, integer_types):
            return self._val > other
        elif isinstance(other, bitarray):
            if self._low >= other.high:
                return self._val > 0
            elif self._high <= other.low:
                return 0 > other.__index__()
            else:
                if other.low < 0:
                    check = self._val << -other.low
                    return check > other.__index__()
                else:
                    check = other.__index__() << other.low
                    return self._val > check
        else:
            return NotImplemented

    def __ge__(self, other):
        if isinstance(other, integer_types):
            return self._val >= other
        elif isinstance(other, bitarray):
            if self._low >= other.high:
                return self._val >= 0
            elif self._high <= other.low:
                return 0 >= other.__index__()
            else:
                if other.low < 0:
                    check = self._val << -other.low
                    return check >= other.__index__()
                else:
                    check = other.__index__() << other.low
                    return self._val >= check
        else:
            return NotImplemented


    # representation
    def __str__(self):
        return str(self._val)

    def __repr__(self):
        return type(self).__name__ + \
                "({}, high={})".format(self._val, self._high)

    def resize(*args):
        length = len(args)
        if length == 2:
            value = args[0]
            format = args[1]
            if isinstance(format, integer_types):
                high = format
                low = 0
            else:
                high = format.high
                low = format.low
        elif length == 3:
            value = args[0]
            high = args[1]
            low = args[2]
        else:
            raise TypeError("Incorrect number of arguments")
        result = copy(value)
        result._high = high
        result._low = low
        result._resize(value)
        result._wrap()
        return result
