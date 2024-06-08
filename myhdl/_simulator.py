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

#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

""" Simulator internals and the now function

This module provides the following objects:
now -- function that returns the current simulation time

"""


class __simulator:
    def __init__(self):
        self._blocks = []
        self._cosim = 0
        self._futureEvents = []
        self._siglist = []
        self._signals = []
        self._tf = None
        self._time = 0
        self._tracing = 0

    def clear(self):
        self._blocks.clear()
        self._cosim = 0
        self._futureEvents.clear()
        self._siglist.clear()
        self._signals.clear()
        self._tf = None
        self._time = 0
        self._tracing = 0


_simulator = __simulator()


def now():
    """ Return the current simulation time """
    return _simulator._time
