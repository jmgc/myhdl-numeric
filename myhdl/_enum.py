#  This file is part of the myhdl library, a Python package for using
#  Python as a Hardware Description Language.
#
#  Copyright (C) 2003-2008 Jan Decaluwe
#
#  The myhdl library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public License as
#  published by the Free Software Foundation; either version 2.1 of the
#  License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

""" Module that implements enum.

"""
from __future__ import absolute_import

from myhdl._bin import bin


class EnumType(object):
    def __init__(self):
        raise TypeError("class EnumType is only intended for type"
                        " checking on subclasses")


class EnumItemType(object):
    def __init__(self):
        raise TypeError("class EnumItemType is only intended for type"
                        " checking on subclasses")

supported_encodings = ("binary", "one_hot", "one_cold")


def enum(*names, **kwargs):

    # args = args
    encoding = kwargs.get('encoding', None)
    if encoding is not None and encoding not in supported_encodings:
        raise ValueError("Unsupported enum encoding: %s\n"
                         "    Supported encodings: %s" %
                         (encoding, supported_encodings))
    if encoding in ("one_hot", "one_cold"):
        nrbits = len(names)
    else:  # binary as default
        nrbits = len(bin(len(names)-1))

    codedict = {}
    i = 0
    for name in names:
        if not isinstance(name, str):
            raise TypeError()
        if name in codedict:
            raise ValueError("enum literals should be unique")
        if encoding == "one_hot":
            code = bin(1 << i, nrbits)
        elif encoding == "one_cold":
            code = bin(~(1 << i), nrbits)
        else:  # binary as default
            code = bin(i, nrbits)
        if len(code) > nrbits:
            code = code[-nrbits:]
        codedict[name] = code
        i += 1

    class EnumItem(EnumItemType):

        def __init__(self, index, name, val, tipe):
            self._index = index
            self._name = name
            self._val = val
            self._nrbits = tipe._nrbits
            self._nritems = tipe._nritems
            self._type = tipe

        def __hash__(self):
            return hash((self._type, self._index))

        def __repr__(self):
            return self._name

        __str__ = __repr__

        def __int__(self):
            return self.__index__()

        def __hex__(self):
            return hex(self.__index__())

        __str__ = __repr__

        def _toVerilog(self, dontcare=False):
            val = self._val
            if dontcare:
                if encoding == "one_hot":
                    val = val.replace('0', '?')
                elif encoding == "one_cold":
                    val = val.replace('1', '?')
            return "%d'b%s" % (self._nrbits, val)

        def _toVHDL(self):
            return self._name

        def __copy__(self):
            return self

        def __deepcopy__(self, memo=None):
            return self

        def _notImplementedCompare(self, other):
            raise NotImplementedError

        __le__ = __ge__ = __lt__ = __gt__ = _notImplementedCompare

        def __eq__(self, other):
            if not isinstance(other, EnumItemType) or \
                    type(self) is not type(other):
                return NotImplemented
            else:
                return self is other

        def __ne__(self, other):
            if not isinstance(other, EnumItemType) or \
                    type(self) is not type(other):
                return NotImplemented
            else:
                return self is not other

        def __index__(self):
            return int(self._val, 2)

    class Enum(EnumType):
        def __init__(self, names, codedict, nrbits, encoding):
            self.__dict__['_names'] = names
            self.__dict__['_nrbits'] = nrbits
            self.__dict__['_nritems'] = len(names)
            self.__dict__['_codedict'] = codedict
            self.__dict__['_encoding'] = encoding
            self.__dict__['_name'] = None
            for index, name in enumerate(names):
                val = codedict[name]
                self.__dict__[name] = EnumItem(index, name, val, self)

        def __setattr__(self, attr, val):
            raise AttributeError("Cannot assign to enum attributes")

        def __len__(self):
            return len(self._names)

        def __repr__(self):
            return "<Enum: %s>" % ", ".join(names)

        __str__ = __repr__

        def _setName(self, name):
            typename = "t_enum_%s" % name
            self.__dict__['_name'] = typename

        def _toVHDL(self):
            typename = self.__dict__['_name']
            type_str = "type %s is (\n        " % typename
            type_str += ",\n        ".join(self._names)
            type_str += "\n    );"
            if self._encoding is not None:
                codes = " ".join([self._codedict[name]
                                  for name in self._names])
                type_str += '\nattribute enum_encoding of %s:' \
                    ' type is "%s";' % (typename, codes)
            return type_str

    return Enum(names, codedict, nrbits, encoding)
