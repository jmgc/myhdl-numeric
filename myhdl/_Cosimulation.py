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

""" Module that provides the Cosimulation class """
from __future__ import absolute_import

import os
import shlex
import subprocess

from myhdl._intbv import intbv
from myhdl import CosimulationError
from myhdl._simulator import _simulator
from myhdl._compat import PY2, string_types, to_bytes, to_str

_MAXLINE = 4096

class _error:
    pass
_error.MultipleCosim = "Only a single cosimulator allowed"
_error.DuplicateSigNames = "Duplicate signal name in myhdl vpi call"
_error.SigNotFound = "Signal not found in Cosimulation arguments"
_error.TimeZero = "myhdl vpi call when not at time 0"
_error.NoCommunication = "No signals communicating to myhdl"
_error.SimulationEnd = "Premature simulation end"
_error.OSError = "OSError"

class Cosimulation(object):

    """ Cosimulation class. """

    def __init__(self, exe="", **kwargs):
        
        """ Construct a cosimulation object. """
        
        if _simulator._cosim != 0:
            raise CosimulationError(_error.MultipleCosim)
        _simulator._cosim = id(self)
        
        self._rt, self._wt = rt, wt = os.pipe()
        self._rf, self._wf = rf, wf = os.pipe()

        # New pipes are not inheritable by default since py 3.4
        if not PY2:
            for p in rt, wt, rf, wf:
                os.set_inheritable(p, True)

        self._fromSignames = fromSignames = []
        self._fromSizes = fromSizes = []
        self._fromSigs = fromSigs = []
        self._toSignames = toSignames = []
        self._toSizes = toSizes = []
        self._toSigs = toSigs = []
        self._toSigDict = toSigDict = {}
        self._hasChange = 0
        self._getMode = 1

        def close_rt_wf():
            os.close(rt)
            os.close(wf)

        env = os.environ.copy()
        env['MYHDL_TO_PIPE'] = str(wt)
        env['MYHDL_FROM_PIPE'] = str(rf)

        if isinstance(exe, string_types):
            exe = shlex.split(exe)
            
        try:
            sp = subprocess.Popen(exe, env=env, close_fds=False,
                                  preexec_fn=close_rt_wf)
        except OSError as e:
            raise CosimulationError(_error.OSError, str(e))

        self._child = sp

        os.close(wt)
        os.close(rf)
        while 1:
            s = to_str(os.read(rt, _MAXLINE))
            if not s:
                raise CosimulationError(_error.SimulationEnd)
            e = s.split()
            if e[0] == "FROM":
                if int(e[1]) != 0:
                    raise CosimulationError(_error.TimeZero, "$from_myhdl")
                for i in range(2, len(e)-1, 2):
                    n = e[i]
                    if n in fromSignames:
                        raise CosimulationError(_error.DuplicateSigNames, n)
                    if not n in kwargs:
                        raise CosimulationError(_error.SigNotFound, n)
                    fromSignames.append(n)
                    fromSigs.append(kwargs[n])
                    fromSizes.append(int(e[i+1]))
                os.write(wf, b"OK")
            elif e[0] == "TO":
                if int(e[1]) != 0:
                    raise CosimulationError(_error.TimeZero, "$to_myhdl")
                for i in range(2, len(e)-1, 2):
                    n = e[i]
                    if n in toSignames:
                        raise CosimulationError(_error.DuplicateSigNames, n)
                    if not n in kwargs:
                        raise CosimulationError(_error.SigNotFound, n)
                    toSignames.append(n)
                    toSigs.append(kwargs[n])
                    toSigDict[n] = kwargs[n]
                    toSizes.append(int(e[i+1]))
                os.write(wf, b"OK")
            elif e[0] == "START":
                if not toSignames:
                    raise CosimulationError(_error.NoCommunication)
                os.write(wf, b"OK")
                break
            else:
                raise CosimulationError("Unexpected cosim input")

    def _get(self):
        if not self._getMode:
            return
        buf = to_str(os.read(self._rt, _MAXLINE))
        if not buf:
            raise CosimulationError(_error.SimulationEnd)
        e = buf.split()
        for i in range(1, len(e), 2):
            s, v = self._toSigDict[e[i]], e[i+1]
            if v in 'zZ':
                next = None
            elif v in 'xX':
                next = s._init
            else:
                try:
                    next = int(v, 16)
                    if s._nrbits and s._min is not None and s._min < 0:
                        if next >= (1 << (s._nrbits-1)):
                            next |= (-1 << s._nrbits)
                except ValueError:
                    next = intbv(0)
            s.next = next
                 
        self._getMode = 0

    def _put(self, time):
        buflist = []
        buf = repr(time)
        if buf[-1] == 'L':
            buf = buf[:-1] # strip trailing L
        buflist.append(buf)
        if self._hasChange:
            self._hasChange = 0
            for s in self._fromSigs:
                v = int(s._val)
                # signed support
                if s._nrbits and v < 0:
                    v += (1 << s._nrbits)
                buf = hex(v)[2:]
                if buf[-1] == 'L':
                    buf = buf[:-1] # strip trailing L
                buflist.append(buf)
        os.write(self._wf, to_bytes(" ".join(buflist)))
        self._getMode = 1

    def _waiter(self):
        sigs = tuple(self._fromSigs)
        while 1:
            yield sigs
            self._hasChange = 1
            
    def __del__(self):
        """ Clear flag when this object destroyed - to suite unittest. """
        _simulator._cosim = 0
