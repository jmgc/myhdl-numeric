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

""" myhdl package initialization.

This module provides the following myhdl objects:
Simulation -- simulation class
StopStimulation -- exception that stops a simulation
now -- function that returns the current time
Signal -- factory function to model hardware signals
SignalType -- Signal base class
ConcatSignal --  factory function that models a concatenation shadow signal
TristateSignal -- factory function that models a tristate shadow signal
delay -- callable to model delay in a yield statement
posedge -- callable to model a rising edge on a signal in a yield statement
negedge -- callable to model a falling edge on a signal in a yield statement
join -- callable to join clauses in a yield statement
intbv -- mutable integer class with bit vector facilities
modbv -- modular bit vector class
downrange -- function that returns a downward range
bin -- returns a binary string representation.
       The optional width specifies the desired string
       width: padding of the sign-bit is used.
concat -- function to concat ints, bitstrings, bools, intbvs, Signals
       -- returns an intbv
instances -- function that returns all instances defined in a function
always --
always_comb -- decorator that returns an input-sensitive generator
always_seq --
ResetSignal --
enum -- function that returns an enumeration type
traceSignals -- function that enables signal tracing in a VCD file
toVerilog -- function that converts a design to Verilog

"""
from ._bin import bin
from ._concat import concat
from ._intbv import intbv
from ._modbv import modbv
from ._join import join
from ._Signal import posedge, negedge, Signal, SignalType
from ._ShadowSignal import ConcatSignal
from ._ShadowSignal import TristateSignal
from ._simulator import now
from ._delay import delay
from ._Cosimulation import Cosimulation
from ._Simulation import Simulation
from ._misc import instances, downrange
from ._always_comb import always_comb
from ._always_seq import always_seq, ResetSignal
from ._always import always
from ._instance import instance
from ._enum import enum, EnumType, EnumItemType
from ._traceSignals import traceSignals
from . import conversion
from .conversion import toVerilog
from .conversion import toVHDL

from . import numeric
from .numeric._bitarray import bitarray
from .numeric._sintba import sintba
from .numeric._uintba import uintba
from .numeric._sfixba import fixmath, sfixba

from ._tristate import Tristate

from ._errors import StopSimulation
from ._errors import ConversionError
from ._errors import SimulationError
from ._errors import AlwaysError
from ._errors import AlwaysCombError
from ._errors import InstanceError
from ._errors import ExtractHierarchyError

from ._version import __version__

__all__ = ["bin",
           "concat",
           "intbv",
           "modbv",
           "join",
           "posedge",
           "negedge",
           "Signal",
           "SignalType",
           "ConcatSignal",
           "TristateSignal",
           "now",
           "delay",
           "downrange",
           "StopSimulation",
           "Cosimulation",
           "Simulation",
           "instances",
           "instance",
           "always_comb",
           "always_seq",
           "ResetSignal",
           "always",
           "enum",
           "EnumType",
           "EnumItemType",
           "traceSignals",
           "toVerilog",
           "toVHDL",
           "conversion",
           "bitarray",
           "uintba",
           "sintba",
           "sfixba",
           "fixmath",
           "numeric",
           "Tristate",
           ]
