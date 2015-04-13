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
from ._sintba import sintba

from myhdl._compat import long, integer_types

import warnings


class uintba(sintba):
    def _from_int(self, value, high, low=0):
        if value < 0:
            raise TypeError("Only natural values are allowed: " \
                          "{}".format(value), RuntimeWarning)
        sintba._from_int(self, value, high, low)

    def _resize(self, value):
        if self._low != 0:
            raise TypeError("The low parameter must be 0")

        bitarray._resize(self, value)

    def _get_max(self):
        return (1 << (self._high - self._low))
    
    def _get_min(self):
        return 0

    def __neg__(self):
        raise TypeError(type(self).__name__ +
                      " cannot generate/store negative values")

    def __add__(self, other):
        if isinstance(other, uintba):
            return sintba.__add__(self, other)
        elif isinstance(other, (integer_types)):
            if other < 0:
                return sintba(self) + other
            else:
                return sintba.__add__(self, other)
        else:
            return NotImplemented

    def __radd__(self, other):
        if isinstance(other, integer_types):
            if other < 0:
                return sintba(other, self).__add__(self)
            else:
                return sintba.__add__(uintba(other, self), self)
        else:
            return NotImplemented

    def __sub__(self, other):
        if isinstance(other, uintba):
            return sintba.__sub__(self, other)
        elif isinstance(other, (integer_types)):
            if other < 0:
                return sintba(self) - other
            else:
                return sintba.__sub__(self, other)
        else:
            return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, integer_types):
            if other < 0:
                return sintba(other, self).__sub__(self)
            else:
                return sintba.__sub__(uintba(other, self), self)
        else:
            return NotImplemented

    def __mul__(self, other):
        if isinstance(other, uintba):
            return sintba.__mul__(self, other)
        elif isinstance(other, (integer_types)):
            if other < 0:
                return sintba(self) * other
            else:
                return sintba.__mul__(self, other)
        else:
            return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, integer_types):
            if other < 0:
                return sintba(other, self).__mul__(self)
            else:
                return sintba.__mul__(uintba(other, self), self)
        else:
            return NotImplemented

    def __floordiv__(self, other):
        if isinstance(other, uintba):
            return sintba.__floordiv__(self, other)
        elif isinstance(other, (integer_types)):
            if other < 0:
                return sintba(self) // other
            else:
                return sintba.__floordiv__(self, other)
        else:
            return NotImplemented

    def __rfloordiv__(self, other):
        if isinstance(other, integer_types):
            if other < 0:
                return sintba(other, self).__floordiv__(self)
            else:
                return sintba.__floordiv__(uintba(other, self), self)
        else:
            return NotImplemented

    def __mod__(self, other):
        if isinstance(other, uintba):
            return sintba.__mod__(self, other)
        elif isinstance(other, (integer_types)):
            if other < 0:
                return sintba(self) % other
            else:
                return sintba.__mod__(self, other)
        else:
            return NotImplemented

    def __rmod__(self, other):
        if isinstance(other, integer_types):
            if other < 0:
                return sintba(other, self).__mod__(self)
            else:
                return sintba.__mod__(uintba(other, self), self)
        else:
            return NotImplemented

    def __iadd__(self, other):
        if isinstance(other, integer_types) and other < 0:
            raise TypeError("Only natural values allowed")
        else:
            return uintba.__iadd__(self, other)

    def __isub__(self, other):
        if isinstance(other, integer_types) and other < 0:
            return NotImplemented
        else:
            return uintba.__isub__(self, other)

    def __imul__(self, other):
        if isinstance(other, integer_types) and other < 0:
            return NotImplemented
        else:
            return sintba.__imul__(self, other)

    def __ifloordiv__(self, other):
        if isinstance(other, integer_types) and other < 0:
            return NotImplemented
        else:
            return sintba.__ifloordiv__(self, other)

    def __imod__(self, other):
        if isinstance(other, integer_types) and other < 0:
            return NotImplemented
        else:
            return sintba.__imod__(self, other)
