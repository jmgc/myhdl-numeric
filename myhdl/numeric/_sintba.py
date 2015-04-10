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
from ._uintba import uintba
from myhdl._compat import long, integer_types

import warnings


class sintba(uintba):
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
        return type(self)(val, high=self)

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
        elif isinstance(other, uintba):
            value = type(self)(other)._val
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
        elif isinstance(other, uintba):
            value = type(self)(other)
        else:
            return NotImplemented
        return value + self

    def __sub__(self, other):
        length = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
            value = other._val
            length = other._high
        elif isinstance(other, uintba):
            value = type(self)(other)._val
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
        elif isinstance(other, uintba):
            value = type(self)(other)
        else:
            return NotImplemented
        return value - self

    def __mul__(self, other):
        length = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
            value = other._val
            length = other._high
        elif isinstance(other, uintba):
            value = type(self)(other)._val
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
        elif isinstance(other, uintba):
            value = type(self)(other, other._high)
        else:
            return NotImplemented
        return value * self

    def __floordiv__(self, other):
        if isinstance(other, integer_types):
            other_value = other
        elif isinstance(other, sintba):
            other_value = other._val
        elif isinstance(other, uintba):
            other_value = type(self)(other)._val
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
        elif isinstance(other, uintba):
            value = type(self)(other)
        else:
            return NotImplemented
        return value // self

    def __mod__(self, other):
        length = self._high
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, sintba):
            value = other._val
            length = other._high
        elif isinstance(other, uintba):
            value = type(self)(other)._val
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
        elif isinstance(other, uintba):
            value = type(self)(other)
        else:
            return NotImplemented
        return value % self
