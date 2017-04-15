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

""" Module with the conversion dicts """

from ._bitarray import bitarray
from ._sintba import sintba
from ._uintba import uintba
from ._sfixba import sfixba

numeric_types = (bitarray, sintba, uintba, sfixba)

numeric_functions_dict = {bitarray.resize: 'resize',
                          sintba.resize: 'resize',
                          sfixba.scalb: 'scalb',
                          sfixba.floor: 'floor',
                          sfixba.abs: 'abs',
                          sfixba.resize: 'my_resize',
                          }

numeric_attributes_dict = {'max': int,
                           'min': int,
                           'high': int,
                           'low': int,
                           'is_signed': bool
                           }
