#  This file is part of the myhdl library, a Python package for using
#  Python as a Hardware Description Language.
#
#  Copyright (C) 2003-2015 Jan Decaluwe
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



import sys
import warnings


class StopSimulation(Exception):
    """ Basic exception to stop a Simulation """
    pass


class _SuspendSimulation(Exception):
    """ Basic exception to suspend a Simulation """
    pass


class Error(Exception):
    def __init__(self, kind, msg="", info=""):
        self.kind = kind
        self.msg = msg
        self.info = info

    def __str__(self):
        s = "%s%s" % (self.info, self.kind)
        if self.msg:
            s += ": %s" % self.msg
        return s


class AlwaysError(Error):
    pass


class AlwaysCombError(Error):
    pass


class InstanceError(Error):
    pass


class CosimulationError(Error):
    pass


class ExtractHierarchyError(Error):
    pass


class SimulationError(Error):
    pass


class TraceSignalsError(Error):
    pass


class ConversionError(Error):
    pass


class ToVerilogError(ConversionError):
    pass


class ToVHDLError(ConversionError):
    pass


class ConversionWarning(UserWarning):
    pass


class ToVerilogWarning(ConversionWarning):
    pass


class ToVHDLWarning(ConversionWarning):
    pass
# warnings.filterwarnings('always', r".*", ToVerilogWarning)


def showwarning(message, category, filename, lineno, *args):
    print("** %s: %s" % (category.__name__, message), file=sys.stderr)

warnings.showwarning = showwarning
