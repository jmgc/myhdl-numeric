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

from myhdl._compat import integer_types, string_types, long

from copy import copy
import warnings


class bitarray(object):

    def __init__(self, *args, **kwargs):
        value, high, low = self._get_arguments(*args, **kwargs)

        if (high != None) and (low != None) and (high == low):
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
        elif isinstance(value, bitarray):
            if value._val == 0:
                self._zero(value, high, low)
            else:
                self._from_bitarray(value, high, low)
        else:
            warnings.warn("bitarray constructor val should be int, string " \
                            "or bitarray child: {}".format(type(value)),
                          RuntimeWarning)

    def _get_arguments(*args, **kwargs):
        if len(args) > 1:
            value = args[1]
        else:
            value = 0
        if len(args) > 2:
            high = args[2]
        else:
            high = None
        if len(args) > 3:
            low = args[3]
        else:
            low = None
        if len(args) > 4:
            raise TypeError("Too much positional arguments")
        if (len(args) <= 1) and ('value' in kwargs):
            value = kwargs['value']
        if (len(args) <= 2) and ('high' in kwargs):
            high = kwargs['high']
        if (len(args) <= 3) and ('low' in kwargs):
            low = kwargs['low']
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
        self._val = 0

    def _convert_string(self, value):
        if '__' in value:
            warnings.warn("At least two join underscores in the string: "  +
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
            warnings.warn("String has different length than vector: " \
                          "{}, {}".format(length, ba_length),
                          RuntimeWarning)

        self._wrap()

    def _from_int(self, value, high, low):
        val = long(value)

        if val < 0:
            warnings.warn("Only natural values allowed: {}".format(val),
                          RuntimeWarning)

        length = val.bit_length()

        if length == 0:
            self._val = long(0)
            length = 1
        else:
            self._val = val

        self._handle_limits(high, low, length)

        self_length = self._high - self._low

        if (abs(self._val) >> self_length != 0):
            warnings.warn("Vector truncated: " \
                          "{}, {}".format(length, self_length), RuntimeWarning)

        self._wrap()

    def _from_bitarray(self, value, high, low):
        ba_length = len(value)
        
        if high is None and low is None:
            self._high = value.high
            self._low = value.low
        else:
            self._handle_limits(high, low, ba_length)

        if (self._high != value._high) or (self._low != value._low) or \
                (type(self) != type(value)):
            self._resize(value)
            self._wrap()
        else:
            self._val = value._val

    def _resize(self, value):
        if (self._high == value._high) and (self._low == value._low):
            self._val = value._val
        else:
            raise TypeError("Different limits: " \
                            "{}({}, {}), " \
                            "{}({}, {})".format(type(value).__name__,
                                                value._high,
                                                value._low,
                                                type(self).__name__, 
                                                self._high,
                                                self._low))
                
    def _handle_limits(self, high, low, length):
        if (high == None) and (low == None):
            self._low = 0
            self._high = length
        elif (high == None):
            self._low = int(low)
            self._high = length + self._low
        elif (low == None):
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
            warnings.warn("High must be greater than low: " \
                          "{}, {}".format(self._high, self._low),
                          RuntimeWarning)

    def _wrap(self):
        length = self._high-self._low
        mask = (1 << length) - 1
        self._val &= mask

    def _get_nrbits(self):
        return self._high - self._low
    _nrbits = property(_get_nrbits, None)

    # support for the 'high' and 'low' attributes

    def _get_high(self):
        return self._high
    high = property(_get_high, None)

    def _get_low(self):
        return self._low
    low = property(_get_low, None)

    def _get_max(self):
        raise TypeError(type(self).__name__ + " does not have a max value")
    max = property(lambda self: self._get_max(), None)

    def _get_min(self):
        raise TypeError(type(self).__name__ + " does not have a min value")
    min = property(lambda self: self._get_min(), None)

    # hash
    def __hash__(self):
        warnings.warn("bitarray objects are unhashable", RuntimeWarning)

    # copy methods
    def __copy__(self):
        result = type(self)(0, high=self._high, low=self._low)
        result._val = self._val
        return result

    def __deepcopy__(self, visit):
        result = type(self)(0, high=self._high, low=self._low)
        result._val = self._val
        return result

    # iterator method
    def __iter__(self):
        return iter([self[i] for i in range(self._high - 1, self._low - 1, -1)])

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
                warnings.warn("bitarray[i:j] requires i > j: " \
                              "i, j = {}, {}".format(i, j),
                              RuntimeWarning)
            if (i > self._high) or (j < self._low):
                raise IndexError("bitarray[i:j] requires i and j between " \
                                 "the margins: high, i, j, low = " \
                                 "{}, {}, {}, {}".format(self._high,
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
                raise IndexError("bitarray[i] requires i between " \
                                 "the margins: high, i, low = " \
                                 "{}, {}, {}".format(self._high,
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
                raise IndexError("bitarray[i:j] = v requires i > j: " \
                                 "i, j, v = {}, {}, {}".format(i, j, val))
            if (i > self._high) or (j < self._low):
                raise IndexError("bitarray[i:j] = v requires i and j " \
                                 "between the margins: high, i, j, low = " \
                                 "{}, {}, {}, {}".format(self._high,
                                                         i, j, self._low))

            if not isinstance(val, bitarray):
                data = type(self)(val, i - j, 0)
            else:
                data = val
            
            length = len(data)
            ba_length = i  - j
            if length != ba_length:
                warnings.warn("Argument does not fit inside the range: " \
                              "{}, {}".format(length, ba_length),
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
                val = bool(val.__index__())
            else:
                warnings.warn("bitarray[i] = v requires v in (0, 1), " \
                              "i: {}, v: {}".format(i, val),
                              RuntimeWarning)
            if (i >= self._high) or (i < self._low):
                raise IndexError("bitarray[i] = v requires i between " \
                                 "the margins: high, i, low = " \
                                 "{}, {}, {}".format(self._high,
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
            high = max(self._high, other._high)
            low = min(self._low, other._low)
            try:
                left = self.resize(high, low)
                result = type(self)(0, high, low)
                right = type(self)(other, high, low)
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
            high = max(self._high, other._high)
            low = min(self._low, other._low)
            try:
                left = self.resize(high, low)
                result = type(self)(0, high, low)
                right = type(self)(other, high, low)
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
            high = max(self._high, other._high)
            low = min(self._low, other._low)
            try:
                left = self.resize(high, low)
                result = type(self)(0, high, low)
                right = type(self)(other, high, low)
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
    __itruediv__ = __idiv__ = __imod__ = __ipow__ = _not_implemented_in_place

    def __iand__(self, other):
        if isinstance(other, bitarray):
            if (self._high != other.high) or (self._low != other.low):
                raise TypeError("Different argument sizes " \
                                "{}!={}, {}!={}".format(self._high,
                                                        other.high,
                                                        self._low,
                                                        other.low))
            self._val &= other._val
            self._wrap()
            return self
        else:
            return NotImplemented

    def __ior__(self, other):
        if isinstance(other, bitarray):
            if (self._high != other.high) or (self._low != other.low):
                raise TypeError("Different argument sizes " \
                                "{}!={}, {}!={}".format(self._high,
                                                        other.high,
                                                        self._low,
                                                        other.low))
            self._val |= other._val
            self._wrap()
            return self
        else:
            return NotImplemented

    def __ixor__(self, other):
        if isinstance(other, bitarray):
            if (self._high != other.high) or (self._low != other.low):
                raise TypeError("Different argument sizes " \
                                "{}!={}, {}!={}".format(self._high,
                                                        other.high,
                                                        self._low,
                                                        other.low))
            self._val ^= other._val
            self._wrap()
            return self
        else:
            return NotImplemented

    def __ilshift__(self, other):
        if isinstance(other, (integer_types, bitarray)):
            self._val <<= int(other)
            self._wrap()
            return self
        else:
            return NotImplemented

    def __irshift__(self, other):
        if isinstance(other, (integer_types, bitarray)):
            self._val >>= int(other)
            self._wrap()
            return self
        else:
            return NotImplemented

    def _not_implemented_unary(self):
        return NotImplemented

    __neg__ = __pos__ = __abs__ = \
    __int__ = __long__ = __float__ = _not_implemented_unary

    def __invert__(self):
        val = ~self._val

        result = type(self)(0, self._high, self._low)
        result._val = val
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
                    (self._val == other.__index__())
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, bitarray):
            return (self._high != other.high) or \
                    (self._low != other.low) or \
                    (self._val != other.__index__())
        else:
            return NotImplemented

    __lt__ = __le__ = __gt__ = __ge__ = _not_implemented_binary

    # representation
    def __str__(self):
        length = self._high - self.low
        format_str = '{{:0{}b}}'.format(length)
        result_str = format_str.format(self._val)
        return result_str

    def __repr__(self):
        return "bitarray('%s', high=%d, low=%d)" % \
            (self.__str__(), self._high, self._low)

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

    def resize(*args):
        length = len(args)
        if length == 2:
            value = args[0]
            format = args[1]
            if isinstance(format, bitarray):
                high = format.high
                low = format.low
            else:
                raise TypeError("If only one arguments is given, " \
                                "it must be the format.")
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
