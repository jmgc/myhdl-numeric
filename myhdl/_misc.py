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

""" MyHDL miscellaneous public objects.

This module provides the following public myhdl objects:
instances -- function that returns instances in a generator function
downrange -- function that returns a downward range

"""



import inspect

from ._Cosimulation import Cosimulation
from ._instance import _Instantiator


def _isGenSeq(obj):
    from ._block import _Block
    if isinstance(obj, (Cosimulation, _Instantiator, _Block)):
        return True
    if not isinstance(obj, (list, tuple, set)):
        return False

    for e in obj:
        if not _isGenSeq(e):
            return False
    return True


def _get_instances(locals):
    l = {k: v for k, v in locals.items() if _isGenSeq(v)}
    return l

def _check_instances(inst, error):
    error_str = "\n{}:{}\nIn block {} there is an instance not returned: {}"
    insts = set(k for k, v in _get_instances(inst.frame.f_locals).items()
                if not (isinstance(v, (list, tuple, set)) and len(v) == 0))
    returned = set(sub[0] for sub in inst.subs)
    insts -= returned
    if insts:
        file = inst.frame.f_code.co_filename
        line = inst.frame.f_lineno
        if len(insts) == 1:
            raise error(error_str.format(file, line, inst.name, insts.pop()))
        else:
            raise error(error_str.format(file, line, inst.name, insts))


def instances():
    f = inspect.currentframe()
    d = inspect.getouterframes(f)[1][0].f_locals
    return list(_get_instances(d).values())


def downrange(start, stop=0, step=1):
    """ Return a downward range. """
    return range(start-1, stop-1, -step)
