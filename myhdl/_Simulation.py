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

""" Module that provides the Simulation class """
from __future__ import absolute_import
from __future__ import print_function


import os
from operator import itemgetter
from warnings import warn
from types import GeneratorType

from ._Cosimulation import Cosimulation
from ._errors import StopSimulation, _SuspendSimulation
from ._errors import SimulationError
from ._simulator import _simulator
from ._Waiter import _Waiter, _inferWaiter, _SignalTupleWaiter
from ._util import _flatten, _printExcInfo
from ._instance import _Instantiator


schedule = _simulator._futureEvents.append


class _error:
    pass
_error.ArgType = "Inappriopriate argument type"
_error.MultipleCosim = "Only a single cosimulator argument allowed"
_error.DuplicatedArg = "Duplicated argument"


class Simulation(object):

    """ Simulation class.

    Methods:
    run -- run a simulation for some duration

    """

    def __init__(self, *args):
        """ Construct a simulation object.

        *args -- list of arguments. Each argument is a generator or
                 a nested sequence of generators.

        """
        _simulator._time = 0
        arglist = _flatten(*args)
        self._waiters, self._cosim = _makeWaiters(arglist)
        if not self._cosim and _simulator._cosim:
            warn("Cosimulation not registered as Simulation argument")
        self._finished = False
        del _simulator._futureEvents[:]
        del _simulator._siglist[:]
        del _simulator._signals[:]

    def _finalize(self):
        cosim = self._cosim
        if cosim:
            _simulator._cosim = 0
            os.close(cosim._rt)
            os.close(cosim._wf)
            cosim._child.wait()
        if _simulator._tracing:
            _simulator._tracing = 0
            _simulator._tf.close()
        # clean up for potential new run with same signals
        for s in _simulator._signals:
            s._clear()
        self._finished = True

    def runc(self, duration=0, quiet=0):
        simrunc.run(sim=self, duration=duration, quiet=quiet)

    def run(self, duration=None, quiet=0):

        """ Run the simulation for some duration.

        duration -- specified simulation duration (default: forever)
        quiet -- don't print StopSimulation messages (default: off)

        """

        # If the simulation is already finished, raise StopSimulation immediately
        # From this point it will propagate to the caller, that can catch it.
        if self._finished:
            raise StopSimulation("Simulation has already finished")
        waiters = self._waiters
        maxTime = None
        if duration:
            stop = _Waiter(None)
            stop.hasRun = 1
            maxTime = _simulator._time + duration
            schedule((maxTime, stop))
        cosim = self._cosim
        t = _simulator._time
        actives = {}
        tracing = _simulator._tracing
        tracefile = _simulator._tf
        exc = []
        _pop = waiters.pop
        _append = waiters.append
        _extend = waiters.extend

        while 1:
            try:

                for s in _simulator._siglist:
                    _extend(s._update())
                del _simulator._siglist[:]

                while waiters:
                    waiter = _pop()
                    try:
                        waiter.next(waiters, actives, exc)
                    except StopIteration:
                        continue

                if cosim:
                    cosim._get()
                    if _simulator._siglist or cosim._hasChange:
                        cosim._put(t)
                        continue
                elif _simulator._siglist:
                    continue

                if actives:
                    for wl in actives.values():
                        wl.purge()
                    actives = {}

                # at this point it is safe to potentially suspend a simulation
                if exc:
                    raise exc[0]

                # future events
                if _simulator._futureEvents:
                    if t == maxTime:
                        raise _SuspendSimulation(
                            "Simulated %s timesteps" % duration)
                    _simulator._futureEvents.sort(key=itemgetter(0))
                    t = _simulator._time = _simulator._futureEvents[0][0]
                    if tracing:
                        print("#%s" % t, file=tracefile)
                    if cosim:
                        cosim._put(t)
                    while _simulator._futureEvents:
                        newt, event = _simulator._futureEvents[0]
                        if newt == t:
                            if isinstance(event, _Waiter):
                                _append(event)
                            else:
                                _extend(event.apply())
                            del _simulator._futureEvents[0]
                        else:
                            break
                else:
                    raise StopSimulation("No more events")

            except _SuspendSimulation:
                if not quiet:
                    _printExcInfo()
                if tracing:
                    tracefile.flush()
                return 1

            except StopSimulation:
                if not quiet:
                    _printExcInfo()
                self._finalize()
                self._finished = True
                return 0

            except Exception as e:
                if tracing:
                    tracefile.flush()
                # if the exception came from a yield, make sure we can resume
                if exc and e is exc[0]:
                    pass  # don't finalize
                else:
                    self._finalize()
                # now reraise the exception
                raise


def _makeWaiters(arglist):
    waiters = []
    ids = set()
    cosim = None
    for arg in arglist:
        if isinstance(arg, GeneratorType):
            waiters.append(_inferWaiter(arg))
        elif isinstance(arg, _Instantiator):
            waiters.append(arg.waiter)
        elif isinstance(arg, Cosimulation):
            if cosim is not None:
                raise SimulationError(_error.MultipleCosim)
            cosim = arg
            waiters.append(_SignalTupleWaiter(cosim._waiter()))
        elif isinstance(arg, _Waiter):
            waiters.append(arg)
        elif arg is True:
            pass
        else:
            raise SimulationError(_error.ArgType, str(type(arg)))
        if id(arg) in ids:
            raise SimulationError(_error.DuplicatedArg)
        ids.add(id(arg))
    # add waiters for shadow signals
    for sig in _simulator._signals:
        if hasattr(sig, '_waiter'):
            waiters.append(sig._waiter)
    return waiters, cosim
