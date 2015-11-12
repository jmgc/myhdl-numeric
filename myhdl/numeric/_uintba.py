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


class uintba(sintba):
    def _from_int(self, value, high, low=0):
        if value < 0:
            raise TypeError("Only natural values are allowed: "
                            "{}".format(value))
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

    _wrap = bitarray._wrap

    _signed = False

    def unsigned(self):
        return copy(self)

    def signed(self):
        return type(self)(self, high=self.high + 1)
