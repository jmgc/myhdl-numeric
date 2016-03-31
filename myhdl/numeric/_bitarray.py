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

""" Module with the bitarray class """

from myhdl._compat import integer_types, string_types, long, bit_length
from myhdl._intbv import intbv

from copy import copy
import warnings


class bitarray(object):

    def __init__(self, *args, **kwargs):
        value, high, low = self._get_arguments(*args, **kwargs)

        if (high is not None) and (low is not None) and (high == low):
            raise TypeError(type(self).__name__ + " must have a size.")

        if isinstance(value, integer_types):
            if value == 0:
                self._zero(value, high, low)
            else:
                self._from_int(value, high, low)
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
                if (value.is_signed is True) and (self.is_signed is False):
                    value = value.unsigned()

                self._from_bitarray(value, high, low)
        else:
            raise TypeError("bitarray constructor val should be int, string "
                            "or bitarray child: {}".format(type(value)))

    _signed = None

    @property
    def is_signed(self):
        return self._signed

    @staticmethod
    def _get_arguments(*args, **kwargs):
        value = 0
        high = None
        low = None
        value_format = None

        i = -1
        for i, arg in enumerate(args):
            if i > 0 and isinstance(arg, bitarray):
                value_format = arg
                break
            if i == 0:
                value = arg
            elif i == 1:
                high = arg
            elif i == 2:
                low = arg
            else:
                raise TypeError("Too much positional arguments")
        else:
            if value_format is None:
                if isinstance(value, bitarray):
                    value_format = value
        length = len(args)
        if length != (i + 1):
                raise TypeError("No positional arguments allowed after "
                                "value_format object")
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
        return (value, high, low)

    def _zero(self, val, high, low):
        if isinstance(val, bitarray):
            if (high is None) and (low is None):
                self._high = val.high
                self._low = val.low
            else:
                self._handle_limits(high, low, len(val))
        elif isinstance(val, string_types):
            self._handle_limits(high, low, len(val))
        else:
            self._handle_limits(high, low, 1)
        self._val = long(0)

    def _convert_string(self, value):
        if '__' in value:
            warnings.warn("At least two join underscores in the string: " +
                          value, RuntimeWarning)

        if value[0] in ('+', '-', '_'):
            warnings.warn("Only 0 or 1 allowed in the leftmost character: " +
                          value, RuntimeWarning)

        value = value.replace('_', '')

        self._val = long(value, 2)

        return len(value)

    def _from_string(self, value, high, low):
        length = self._convert_string(value)

        self._handle_limits(high, low, length)

        ba_length = self._high - self._low
        if (length != ba_length):
            warnings.warn("String has different length than vector: "
                          "{0}, {1}".format(length, ba_length),
                          RuntimeWarning)

        self._wrap()

    def _from_int(self, value, high, low):
        val = long(value)

        length = bit_length(val)

        if length == 0:
            self._val = long(0)
            length = 1
        else:
            self._val = val

        if self._signed:
            length += 1  # Add the sign bit

        self._handle_limits(high, low, length)

        self_length = self._high - self._low

        if (abs(self._val) >> self_length != 0):
            warnings.warn("Vector truncated: "
                          "{0}, {1}".format(length, self_length),
                          RuntimeWarning)

        self._wrap()

    def _from_bitarray(self, value, high, low):
        ba_length = len(value)

        if high is None and low is None:
            self._high = value.high
            self._low = value.low
        else:
            self._handle_limits(high, low, ba_length)

        if (self._high != value.high) or (self._low != value.low):
            if type(self) == type(value):
                self._resize(value)
            else:
                if value.is_signed and not self.is_signed:
                    high = self._high + 1
                else:
                    high = self._high
                if value._low <= 0:
                    if self._low < value._low:
                        low = value._low
                    else:
                        low = self._low
                else:
                    low = self._low
                origin_resize = type(value)(0, high, low)
                origin_resize._resize(value)
                destination_resize = type(self)(0, self)
                destination_resize._resize(origin_resize)
                self._val = destination_resize._val
        else:
            self._val = value._val
        self._wrap()

    def _resize(self, value):
        """Just truncate and/or zeropadding"""
        tmp = value._val
        dlow = self._low - value._low
        if dlow < 0:
            tmp &= ((1 << (self._high - self._low)) - 1) >> -dlow
            self._val = tmp << -dlow
        elif dlow >= 0:
            tmp &= ((1 << (self._high - self._low)) - 1) << dlow
            self._val = tmp >> dlow

    def _handle_limits(self, high, low, length):
        if (high is None) and (low is None):
            self._low = 0
            self._high = length
        elif (high is None):
            self._low = int(low)
            self._high = length + self._low
        elif (low is None):
            if hasattr(high, 'high') and hasattr(high, 'low'):
                self._high = high.high
                self._low = high.low
            else:
                self._high = int(high)
                self._low = self._high - length
        else:
            self._high = int(high)
            self._low = int(low)

        if self._high <= self._low:
            warnings.warn("High must be greater than low: "
                          "{0}, {1}".format(self._high, self._low),
                          RuntimeWarning)

    def _wrap(self):
        length = self._high-self._low
        mask = (1 << length) - 1
        self._val &= mask

    @property
    def _nrbits(self):
        return self._high - self._low

    # support for the 'val' attribute
    @property
    def val(self):
        return copy(self)

    # support for the 'high' and 'low' attributes
    @property
    def high(self):
        return self._high

    @property
    def low(self):
        return self._low

    def _get_max(self):
        raise TypeError(type(self).__name__ + " does not have a max value")
    max = property(lambda self: self._get_max(), None)

    def _get_min(self):
        raise TypeError(type(self).__name__ + " does not have a min value")
    min = property(lambda self: self._get_min(), None)

    # math utility functions
    @staticmethod
    def _divide(l, r):
        neg_quot = False

        if r < 0:
            r = -r
            neg_quot = True
        if l < 0:
            l = -l
            neg_quot = not neg_quot

        division = l // r

        if neg_quot:
            division = -division

        return division

    @staticmethod
    def _module(l, r):
        xnum = abs(l)

        if r < 0:
            xdenom = -r
            rneg = True
        else:
            xdenom = r
            rneg = False
        module = xnum % xdenom
        if rneg and (l < 0):
            module = -module
        elif rneg and (module != 0):
            module -= xdenom
        elif (l < 0) and (module != 0):
            module = xdenom - module
        return module

    # hash
    def __hash__(self):
        warnings.warn("bitarray objects are unhashable", RuntimeWarning)

    # copy methods
    def __copy__(self):
        result = type(self)(self)
        return result

    def __deepcopy__(self, visit):
        result = type(self)(self)
        return result

    # iterator method
    def __iter__(self):
        return iter([self[i]
                     for i in range(self._high - 1, self._low - 1, -1)])

    # logical testing
    def __bool__(self):
        return bool(self._val)

    __nonzero__ = __bool__

    # length
    def __len__(self):
        return self._high - self._low

    # indexing and slicing methods

    def __getitem__(self, key):
        if isinstance(key, slice):
            i, j = key.start, key.stop
            if j is None:  # default
                j = self._low
            else:
                j = j.__index__()
            if i is None:  # default
                i = self._high
            else:
                i = i.__index__()
            if i <= j:
                warnings.warn("bitarray[i:j] requires i > j: "
                              "i, j = {0}, {1}".format(i, j),
                              RuntimeWarning)
            if (i > self._high) or (j < self._low):
                raise IndexError("bitarray[i:j] requires i and j between "
                                 "the margins: high, i, j, low = "
                                 "{0}, {1}, {2}, {3}".format(self._high,
                                                             i, j, self._low))

            res = type(self)(high=i - j, low=0)

            disp = j - self._low

            if disp > 0:
                val = self._val >> disp
            else:
                val = self._val << -disp
            res._val = val
            res._wrap()

            return res
        else:
            i = key.__index__()
            if (i >= self._high) or (i < self._low):
                raise IndexError("bitarray[i] requires i between "
                                 "the margins: high, i, low = "
                                 "{0}, {1}, {2}".format(self._high,
                                                        i, self._low))
            i -= self._low
            res = bool((self._val >> i) & 0x1)

            return res

    def __setitem__(self, key, val):
        # convert val to int to avoid confusion with bitarray or Signals

        if isinstance(key, slice):
            i, j = key.start, key.stop
            if j is None:  # default
                j = self._low
            else:
                j = j.__index__()
            if i is None:  # default
                i = self._high
            else:
                i = i.__index__()
            if i <= j:
                raise IndexError("bitarray[i:j] = v requires i > j: "
                                 "i, j, v = {0}, {1}, {2}".format(i, j, val))
            if (i > self._high) or (j < self._low):
                raise IndexError("bitarray[i:j] = v requires i and j "
                                 "between the margins: high, i, j, low = "
                                 "{0}, {1}, {2}, {3}".format(self._high,
                                                             i, j, self._low))

            if not isinstance(val, bitarray):
                if hasattr(val, 'val'):
                    tmp = val.val
                    if isinstance(tmp, bitarray):
                        data = tmp
                    else:
                        data = bitarray(tmp, i - j, 0)
                else:
                    data = bitarray(val, i - j, 0)
            else:
                data = val

            length = len(data)
            ba_length = i - j
            if length != ba_length:
                warnings.warn("Argument does not fit inside the range: "
                              "{0}, {1}".format(length, ba_length),
                              RuntimeWarning)

            value = data._val

            mask = (long(1) << (i - j)) - 1
            self._val &= ~(mask << (j - self._low))
            self._val |= ((value & mask) << (j - self._low))
        else:
            i = key.__index__()
            if (val in (0, 1)) or (val is bool):
                val = bool(val)
            elif isinstance(val, bitarray) and (len(val) == 1):
                val = bool(val)
            else:
                warnings.warn("bitarray[i] = v requires v in (0, 1), "
                              "i: {0}, v: {1}".format(i, val),
                              RuntimeWarning)
            if (i >= self._high) or (i < self._low):
                raise IndexError("bitarray[i] = v requires i between "
                                 "the margins: high, i, low = "
                                 "{0}, {1}, {2}".format(self._high,
                                                        i, self._low))
            if val:
                self._val |= (long(1) << (i - self._low))
            else:
                self._val &= ~(long(1) << (i - self._low))

        self._wrap()

    def _not_implemented_binary(self, arg):
        return NotImplemented

    # integer-like methods
    __add__ = __radd__ = __sub__ = __rsub__ = \
        __mul__ = __rmul__ = __div__ = __rdiv__ = \
        __truediv__ = __rtruediv__ = __floordiv__ = __rfloordiv__ = \
        __mod__ = __rmod__ = __pow__ = __rpow__ = \
        __rlshift__ = __rrshift__ = _not_implemented_binary

    def __lshift__(self, other):
        if isinstance(other, integer_types):
            result = copy(self)
            result._val = self._val << other
            result._wrap()
            return result
        else:
            return NotImplemented

    def __rshift__(self, other):
        if isinstance(other, integer_types):
            result = copy(self)
            result._val = self._val >> other
            result._wrap()
            return result
        else:
            return NotImplemented

    def __and__(self, other):
        if isinstance(other, bitarray):
            high = max(self._high, other.high)
            low = min(self._low, other.low)
            try:
                left = self.signed().resize(high + 1, low)
                result = type(self)(0, high, low)
                right = type(self)(other.signed(), high + 1, low)
            except:
                return NotImplemented
            result._val = left._val & right._val
            result._wrap()
            return result
        else:
            return NotImplemented

    __rand__ = __and__

    def __or__(self, other):
        if isinstance(other, bitarray):
            high = max(self._high, other.high)
            low = min(self._low, other.low)
            try:
                left = self.signed().resize(high + 1, low)
                result = type(self)(0, high, low)
                right = type(self)(other.signed(), high + 1, low)
            except:
                return NotImplemented
            result._val = left._val | right._val
            result._wrap()
            return result
        else:
            return NotImplemented

    __ror__ = __or__

    def __xor__(self, other):
        if isinstance(other, bitarray):
            high = max(self._high, other.high)
            low = min(self._low, other.low)
            try:
                left = self.signed().resize(high + 1, low)
                result = type(self)(0, high, low)
                right = type(self)(other.signed(), high + 1, low)
            except:
                return NotImplemented
            result._val = left._val ^ right._val
            result._wrap()
            return result
        else:
            return NotImplemented

    __rxor__ = __xor__

    def _not_implemented_in_place(self, arg):
        return NotImplemented

    __iadd__ = __isub__ = __imul__ = __ifloordiv__ = \
        __itruediv__ = __idiv__ = __imod__ = __ipow__ = \
        _not_implemented_in_place

    def __iand__(self, other):
        value = self & other
        value = value[self._high:self._low]
        self._val = value._val
        self._wrap()
        return self

    def __ior__(self, other):
        value = self | other
        value = value[self._high:self._low]
        self._val = value._val
        self._wrap()
        return self

    def __ixor__(self, other):
        value = self ^ other
        value = value[self._high:self._low]
        self._val = value._val
        self._wrap()
        return self

    def __ilshift__(self, other):
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, bitarray) and (other.low == 0):
            value = other
        else:
            return NotImplemented
        self._val <<= int(value)
        self._wrap()
        return self

    def __irshift__(self, other):
        if isinstance(other, integer_types):
            value = other
        elif isinstance(other, bitarray) and (other.low == 0):
            value = other
        else:
            return NotImplemented
        self._val >>= int(value)
        self._wrap()
        return self

    def _not_implemented_unary(self):
        return NotImplemented

    __neg__ = __pos__ = __abs__ = \
        __int__ = __long__ = __float__ = _not_implemented_unary

    def __invert__(self):
        result = type(self)(0, self._high, self._low)
        result._val = ~self._val
        result._wrap()
        return result

    # XXX __complex__ seems redundant ??? (complex() works as such?)

    def __oct__(self):
        return oct(self._val)

    def __hex__(self):
        return hex(self._val)

    def __index__(self):
        return self._val

    # comparisons
    def __eq__(self, other):
        if isinstance(other, bitarray):
            return (self._high == other.high) and \
                    (self._low == other.low) and \
                    (self._val == other._val)
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, bitarray):
            return (self._high != other.high) or \
                    (self._low != other.low) or \
                    (self._val != other._val)
        else:
            return NotImplemented

    __lt__ = __le__ = __gt__ = __ge__ = _not_implemented_binary

    # representation
    def __str__(self):
        length = self._high - self._low
        format_str = '{{0:0{0}b}}'.format(length)
        result_str = format_str.format(self._val & ((1 << length) - 1))
        return result_str

    def __repr__(self):
        return "bitarray('%s', high=%d, low=%d)" % \
            (self.__str__(), self._high, self._low)

    def unsigned(self):
        return copy(self)

    def signed(self):
        return copy(self)

    def and_reduce(self):
        length = self._high - self._low
        if length == 0:
            return True
        else:
            return self._val == ((1 << (length)) - 1)

    def or_reduce(self):
        length = self._high - self._low
        if length == 0:
            return False
        else:
            return self._val > 0

    def xor_reduce(self):
        length = self._high - self._low
        val = self._val & ((1 << (length)) - 1)

        while length > 8:
            length >>= 1

            val ^= val >> length

        val &= 0xf

        return ((0x6996 >> val) & 1) == 1

    def resize(self, *args):
        length = len(args)
        value = self
        if length == 1:
            value_format = args[0]
            if isinstance(value_format, bitarray):
                high = value_format.high
                low = value_format.low
            else:
                raise TypeError("If only one arguments is given, "
                                "it must be the format.")
        elif length == 2:
            high = args[0]
            low = args[1]
        else:
            raise TypeError("Incorrect number of arguments")
        result = type(value)(0, high, low)
        result._resize(value)
        result._wrap()
        return result

    @property
    def internal(self):
        return self._val
