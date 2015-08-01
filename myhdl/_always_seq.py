#  This file is part of the myhdl library, a Python package for using
#  Python as a Hardware Description Language.
#
#  Copyright (C) 2003-2012 Jan Decaluwe
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

""" Module with the always_seq decorator. """
from __future__ import absolute_import


import sys
import inspect
from types import FunctionType
import ast

from myhdl import AlwaysError, intbv
from myhdl._util import _isGenFunc, _dedent
from myhdl._cell_deref import _cell_deref
from myhdl._delay import delay
from myhdl._Signal import _Signal, _WaiterList,_isListOfSigs
from myhdl._Waiter import _Waiter, _EdgeWaiter, _EdgeTupleWaiter
from myhdl._always import _Always
from myhdl._resolverefs import _AttrRefTransformer
from myhdl._visitors import _SigNameVisitor

# evacuate this later
AlwaysSeqError = AlwaysError

class _error:
    pass
_error.EdgeType = "first argument should be an edge"
_error.ResetType = "reset argument should be a ResetSignal"
_error.ArgType = "decorated object should be a classic (non-generator) function"
_error.NrOfArgs = "decorated function should not have arguments"
_error.SigAugAssign = "signal assignment does not support augmented assignment"
_error.EmbeddedFunction = "embedded functions in always_seq function not supported"

class ResetSignal(_Signal):
    def __init__(self, val, active, async):
        """ Construct a ResetSignal.

        This is to be used in conjunction with the always_seq decorator,
        as the reset argument.
        """
        _Signal.__init__(self, bool(val))
        self.active = bool(active)
        self.async = async



def always_seq(edge, reset):
    if not isinstance(edge, _WaiterList):
        raise AlwaysSeqError(_error.EdgeType)
    edge.sig._read = True
    edge.sig._used = True
    if reset is not None:
        if not isinstance(reset, ResetSignal):
            raise AlwaysSeqError(_error.ResetType)
        reset._read = True
        reset._used = True

    def _always_seq_decorator(func):
        if not isinstance(func, FunctionType):
            raise AlwaysSeqError(_error.ArgType)
        if _isGenFunc(func):
            raise AlwaysSeqError(_error.ArgType)
        if func.__code__.co_argcount > 0:
            raise AlwaysSeqError(_error.NrOfArgs)
        return _AlwaysSeq(func, edge, reset)
    return _always_seq_decorator


class _AlwaysSeq(_Always):

    def __init__(self, func, edge, reset):
        senslist = [edge]
        self.reset = reset
        if reset is not None:
            self.genfunc = self.genfunc_reset
            active = self.reset.active
            async = self.reset.async
            if async:
                if active:
                    senslist.append(reset.posedge)
                else:
                    senslist.append(reset.negedge)
        else:
            self.genfunc = self.genfunc_no_reset

        super(_AlwaysSeq, self).__init__(func, senslist)

        # find symdict
        # similar to always_comb, but in class constructor
        varnames = func.__code__.co_varnames
        symdict = {}
        for n, v in func.__globals__.items():
            if n not in varnames:
                symdict[n] = v
        # handle free variables
        if func.__code__.co_freevars:
            for n, c in zip(func.__code__.co_freevars, func.__closure__):
                try:
                    obj = _cell_deref(c)
                    symdict[n] = obj
                except NameError:
                    raise NameError(n)
        self.symdict = symdict

        # now infer outputs to be reset
        s = inspect.getsource(func)
        s = _dedent(s)
        tree = ast.parse(s)
        # print ast.dump(tree)
        v = _AttrRefTransformer(self)
        v.visit(tree)
        v = _SigNameVisitor(self.symdict)
        v.visit(tree)

        if v.results['inout']:
            raise AlwaysSeqError(_error.SigAugAssign, v.results['inout'])

        if v.results['embedded_func']:
            raise AlwaysSeqError(_error.EmbeddedFunction)

        sigregs = self.sigregs = []
        varregs = self.varregs = []
        for n in v.results['output']:
            reg = self.symdict[n]
            if isinstance(reg, _Signal):
                sigregs.append(reg)
            elif isinstance(reg, intbv):
                varregs.append((n, reg, int(reg)))
            else:
                assert _isListOfSigs(reg)
                for e in reg:
                    sigregs.append(e)

    def reset_sigs(self):
        for s in self.sigregs:
            s.next = s._init

    def reset_vars(self):
        for v in self.varregs:
            # only intbv's for now
            n, reg, init = v
            reg._val = init

    def genfunc_reset(self):
        senslist = self.senslist
        if len(senslist) == 1:
            senslist = senslist[0]
        reset_sigs = self.reset_sigs
        reset_vars = self.reset_vars
        func = self.func
        while 1:
            yield senslist
            if self.reset == self.reset.active:
                reset_sigs()
                reset_vars()
            else:
                func()

    def genfunc_no_reset(self):
        senslist = self.senslist
        assert len(senslist) == 1
        senslist = senslist[0]
        func = self.func
        while 1:
            yield senslist
            func()
