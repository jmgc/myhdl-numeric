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
from copy import copy
from ._bitarray import bitarray

from myhdl._compat import long, integer_types

import warnings


class uintba(bitarray):
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

    def _from_int(self, value, high, low):
        if value < 0:
            warnings.warn("Only natural values are allowed: " \
                          "{}".format(value), RuntimeWarning)
        val = long(value)

        length = val.bit_length()

        if length == 0:
            self._val = long(0)
            length = 1
        else:
            self._val = long(val)

        self._handle_limits(high, low, length)

        self_length = self._high - self._low
        
        if (self._val >> self_length != 0):
            warnings.warn("Integer truncated: {}". format(self._val),
                          RuntimeWarning)
        self._wrap()

    def _resize(self, value):
        if self._low != 0:
            raise TypeError("The low parameter must be 0")

        data = value[:0]
        result = data._val & (1 << self._high) - 1

        if (abs(result) >> data.high) != 0:
            warnings.warn("Number truncated: {}".format(result),
                          RuntimeWarning)

        self._val = result

    def _get_max(self):
        return (1 << (self._high - self._low))
    
    def _get_min(self):
        return 0

    def __abs__(self):
        return type(self)(self)

    def __neg__(self):
        raise TypeError(type(self).__name__ +
                      " cannot generate/store negative values")

    def __add__(self, other):
        length = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, uintba):
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
            value = type(self)(other, self._high)
        else:
            return NotImplemented
        return value + self

    def __sub__(self, other):
        length = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, uintba):
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
            value = type(self)(other, self._high)
        else:
            return NotImplemented
        return value - self

    def __mul__(self, other):
        length = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, uintba):
            value = other._val
            length = other._high
        else:
            return NotImplemented
        
        size = self._high + length
        
        result = type(self)(0, high=size)
        result._val = self._val * value
        result._wrap()
        return result

    def __rmul__(self, other):
        if isinstance(other, integer_types):
            value = type(self)(other, self._high)
        else:
            return NotImplemented
        return value * self

    def __floordiv__(self, other):
        if isinstance(other, integer_types):
            other_value = other
        elif isinstance(other, uintba):
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
            value = type(self)(other, self._high)
        else:
            return NotImplemented
        return value // self

    def __mod__(self, other):
        length = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, uintba):
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
            value = type(self)(other, self._high)
        else:
            return NotImplemented
        return value % self

    def __lshift__(self, other):
        if isinstance(other, (integer_types, uintba)):
            result = copy(self)
            result._val = self._val << int(other)
            result._wrap()
            return result
        else:
            return NotImplemented

    def __rlshift__(self, other):
        if isinstance(other, integer_types):
            result = copy(self)
            result._val = other << self._val
            result._wrap()
            return result
        else:
            return NotImplemented

    def __rshift__(self, other):
        if isinstance(other, (integer_types, uintba)):
            result = copy(self)
            result._val = self._val >> int(other)
            result._wrap()
            return result
        else:
            return NotImplemented

    def __rrshift__(self, other):
        if isinstance(other, integer_types):
            result = copy(self)
            result._val = other >> self._val
            result._wrap()
            return result
        else:
            return NotImplemented
           
    def __and__(self, other):
        if isinstance(other, uintba):
            value = other
        else:
            return NotImplemented

        return bitarray.__and__(self, value)            

    __rand__ = __and__

    def __or__(self, other):
        if isinstance(other, uintba):
            value = other
        else:
            return NotImplemented

        return bitarray.__or__(self, value)            

    __ror__ = __or__

    def __xor__(self, other):
        if isinstance(other, uintba):
            value = other
        else:
            return NotImplemented

        return bitarray.__xor__(self, value)            

    __rxor__ = __xor__

    def __iadd__(self, other):
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, uintba):
            value = other._val
        else:
            return NotImplemented
        
        self._val += value
        self._wrap()
        return self

    def __isub__(self, other):
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, uintba):
            value = other._val
        else:
            return NotImplemented
        
        self._val -= value
        self._wrap()
        return self

    def __imul__(self, other):
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, uintba):
            value = other._val
        else:
            return NotImplemented
        
        self._val *= value
        self._wrap()
        return self

    def __ifloordiv__(self, other):
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, uintba):
            value = other._val
        else:
            return NotImplemented
        
        self._val //= value
        self._wrap()
        return self

    def __imod__(self, other):
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, uintba):
            value = other._val
        else:
            return NotImplemented
        
        self._val %= value
        self._wrap()
        return self

    def __pos__(self):
        return type(self)(self)

    def __int__(self):
        return int(self._val)

    def __long__(self):
        return long(self._val)

    def __float__(self):
        return float(self._val)

    # XXX __complex__ seems redundant ??? (complex() works as such?)

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
        result = type(value)(0, high, low)
        result._resize(value)
        result._wrap()
        return result
