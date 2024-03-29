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

""" myhdl _extractHierarchy module.

"""

import inspect
import re
import string
import sys
import ast

from ._errors import ExtractHierarchyError, ToVerilogError, ToVHDLError
from ._enum import EnumItemType
from .numeric._bitarray import bitarray
from ._Signal import _Signal, _isListOfSigs
from ._getcellvars import _getCellVars
from ._misc import _isGenSeq, _get_instances
from ._resolverefs import _resolveRefs
from ._util import _flatten, _genfunc, _isTupleOfInts, _isTupleOfFloats, _isTupleOfBitArray

_profileFunc = None


class _error:
    NoInstances = "No instances found"
    InconsistentHierarchy = "Inconsistent hierarchy - are all" \
                            " instances returned ?"
    InconsistentToplevel = "Inconsistent top level %s for %s - should be 1"
    MissingInstance = "\n{}:{}\nIn block {} there is an instance not returned: {}"
    MissingInstances = "\n{}:{}\nIn block {} there are instances not returned: {}"


class _Constant:
    def __init__(self, orig_name, value):
        self.name = None
        self.orig_name = orig_name
        self.instance = None
        self.value = value
        self.used = False


class _Instance:
    __slots__ = ['level', 'obj', 'subs', 'constdict', 'sigdict', 'memdict',
                 'romdict', 'name', 'func', 'frame',
                 ]

    def __init__(self, level, obj, subs, constdict, sigdict, memdict,
                 romdict, func, frame):
        self.level = level
        self.obj = obj
        self.subs = subs
        self.constdict = constdict
        self.sigdict = sigdict
        self.memdict = memdict
        self.romdict = romdict
        self.func = func
        self.frame = frame

        self.name = None


_memInfoMap = {}


class _MemInfo:
    __slots__ = ['mem', 'name', 'elObj', 'depth', 'type', '_used', '_driven',
                 '_read']

    def __init__(self, mem):
        self.mem = mem
        self.name = None
        self.depth = len(mem)
        self.elObj = mem[0]
        self.type = None
        self._used = False
        self._driven = None
        self._read = False

    @property
    def used(self):
        return self._used

    @used.setter
    def used(self, val):
        self._used = bool(val)
        for s in self.mem:
            s._used = bool(val)

    def _clear(self):
        self._driven = None
        self._read = False
        for el in self.mem:
            el._clear()


def _getMemInfo(mem):
    return _memInfoMap[id(mem)]


def _makeMemInfo(mem):
    key = id(mem)
    if key not in _memInfoMap:
        _memInfoMap[key] = _MemInfo(mem)
    return _memInfoMap[key]


def _isMem(mem):
    return id(mem) in _memInfoMap


_romInfoMap = {}


class _RomInfo:
    __slots__ = ['mem', 'orig_name', 'name', 'elObj', 'depth', 'type', '_used']

    def __init__(self, orig_name, mem):
        self.mem = mem
        self.orig_name = orig_name
        self.name = None
        self.depth = len(mem)
        if (self.depth > 0):
            if isinstance(mem[0], int):
                for elObj in mem:
                    if elObj < 0:
                        break
            else:
                elObj = mem[0]
            self.elObj = elObj
        else:
            self.elObj = None
        self.type = None
        self._used = False

    @property
    def used(self):
        return self._used

    @used.setter
    def used(self, val):
        self._used = bool(val)


def _getRomInfo(mem):
    return _romInfoMap[id(mem)]


def _makeRomInfo(n, mem):
    key = id(mem)
    if key not in _romInfoMap:
        _romInfoMap[key] = _RomInfo(n, mem)
    return _romInfoMap[key]


def _isRom(mem):
    return id(mem) in _romInfoMap


class _UserCode:
    __slots__ = ['code', 'namespace', 'funcname', 'func', 'sourcefile',
                 'sourceline']

    def __init__(self, code, namespace, funcname, func, sourcefile,
                 sourceline):
        self.code = code
        self.namespace = namespace
        self.sourcefile = sourcefile
        self.func = func
        self.funcname = funcname
        self.sourceline = sourceline

    def __str__(self):
        try:
            code = self._interpolate()
        except:
            tipe, value, _ = sys.exc_info()
            info = "in file %s, function %s starting on line %s:\n    " % \
                   (self.sourcefile, self.funcname, self.sourceline)
            msg = "%s: %s" % (tipe, value)
            self.raiseError(msg, info)
        code = "\n%s\n" % code
        return code

    def _scrub_namespace(self):
        for nm, obj in self.namespace.items():
            if _isMem(obj):
                memi = _getMemInfo(obj)
                self.namespace[nm] = memi.name

    def _interpolate(self):
        self._scrub_namespace()
        return string.Template(self.code).substitute(self.namespace)


class _UserCodeDepr(_UserCode):
    def _interpolate(self):
        return self.code % self.namespace


class _UserVerilogCode(_UserCode):
    def raiseError(self, msg, info):
        raise ToVerilogError("Error in user defined Verilog code", msg, info)


class _UserVhdlCode(_UserCode):
    def raiseError(self, msg, info):
        raise ToVHDLError("Error in user defined VHDL code", msg, info)


class _UserVerilogCodeDepr(_UserVerilogCode, _UserCodeDepr):
    pass


class _UserVhdlCodeDepr(_UserVhdlCode, _UserCodeDepr):
    pass


class _UserVerilogInstance(_UserVerilogCode):
    def __str__(self):
        args = inspect.getargspec(self.func)[0]
        s = "%s %s(" % (self.funcname, self.code)
        sep = ''
        for arg in args:
            if arg in self.namespace and isinstance(self.namespace[arg],
                                                    _Signal):
                signame = self.namespace[arg]._name
                s += sep
                sep = ','
                s += "\n    .%s(%s)" % (arg, signame)
        s += "\n);\n\n"
        return s


class _UserVhdlInstance(_UserVhdlCode):
    def __str__(self):
        args = inspect.getargspec(self.func)[0]
        s = "%s: entity work.%s(MyHDL)\n" % (self.code, self.funcname)
        s += "    port map ("
        sep = ''
        for arg in args:
            if arg in self.namespace and isinstance(self.namespace[arg],
                                                    _Signal):
                signame = self.namespace[arg]._name
                s += sep
                sep = ','
                s += "\n        %s=>%s" % (arg, signame)
        s += "\n    );\n\n"
        return s


class _CallFuncVisitor:

    def __init__(self):
        self.linemap = {}

    def visitAssign(self, node):
        if isinstance(node.expr, ast.Call):
            self.lineno = None
            self.visit(node.expr)
            self.linemap[self.lineno] = node.lineno

    def visitName(self, node):
        self.lineno = node.lineno


class _HierExtr:

    def __init__(self, name, dut, *args, **kwargs):

        global _profileFunc
        _memInfoMap.clear()
        self.userCodeMap = {'verilog': {},
                            'vhdl': {}
                            }

        self.skipNames = ('always_comb', 'instance',
                          'always_seq', '_always_seq_decorator',
                          'always', '_always_decorator',
                          'instances',
                          'processes', 'posedge', 'negedge')
        self.skip = 0
        self.hierarchy = hierarchy = []
        self.absnames = absnames = {}
        self.level = 0

        _profileFunc = self.extractor
        sys.setprofile(_profileFunc)
        _top = dut(*args, **kwargs)
        sys.setprofile(None)
        if not hierarchy:
            raise ExtractHierarchyError(_error.NoInstances)

        self.top = _top

        # streamline hierarchy
        hierarchy.reverse()
        # walk the hierarchy to define relative and absolute names
        names = {}
        top_inst = hierarchy[0]
        obj, subs = top_inst.obj, top_inst.subs
        names[id(obj)] = name
        absnames[id(obj)] = name

        if not top_inst.level == 1:
            raise ExtractHierarchyError(_error.InconsistentToplevel % (top_inst.level, name),
                                        f"\nCheck the return of instances: {list(_get_instances(top_inst.frame.f_locals).keys())}")
        for inst in hierarchy:
            obj, subs = inst.obj, inst.subs
            if id(obj) not in names:
                raise ExtractHierarchyError(_error.InconsistentHierarchy)

            inst.name = names[id(obj)]
            _HierExtr._check_instances(inst)
            tn = absnames[id(obj)]

            for sn, so in subs:
                names[id(so)] = sn
                absnames[id(so)] = "%s_%s" % (tn, sn)

                if isinstance(so, (tuple, list)):
                    for i, soi in enumerate(so):
                        sni = "%s_%s" % (sn, i)
                        names[id(soi)] = sni
                        absnames[id(soi)] = "%s_%s_%s" % (tn, sn, i)

    @staticmethod
    def _check_instances(inst):
        insts = set(k for k, v in _get_instances(inst.frame.f_locals).items()
                    if not (isinstance(v, (list, tuple, set)) and len(v) == 0))
        returned = set(sub[0] for sub in inst.subs)
        insts -= returned
        if insts:
            file = inst.frame.f_code.co_filename
            line = inst.frame.f_lineno
            if len(insts) == 1:
                raise ExtractHierarchyError(_error.MissingInstance.format(file, line, inst.name, insts.pop()))
            else:
                raise ExtractHierarchyError(_error.MissingInstances.format(file, line, inst.name, insts))

    def extractor(self, frame, event, arg):
        if event == "call":

            funcname = frame.f_code.co_name
            # skip certain functions
            if funcname in self.skipNames:
                self.skip += 1
            if not self.skip:
                self.level += 1

        elif event == "return":

            funcname = frame.f_code.co_name
            func = frame.f_globals.get(funcname)

            if func is None:
                # Didn't find a func in the global space, try the local "self"
                # argument and see if it has a method called *funcname*
                obj = frame.f_locals.get('self')
                if hasattr(obj, funcname):
                    func = getattr(obj, funcname)

            if not self.skip:
                isGenSeq = _isGenSeq(arg)
                if isGenSeq:
                    specs = {}
                    for hdl in self.userCodeMap:
                        spec = "__%s__" % hdl
                        if spec in frame.f_locals and frame.f_locals[spec]:
                            specs[spec] = frame.f_locals[spec]
                        spec = "%s_code" % hdl
                        if func and hasattr(func, spec) and \
                                getattr(func, spec):
                            specs[spec] = getattr(func, spec)
                        spec = "%s_instance" % hdl
                        if func and hasattr(func, spec) and \
                                getattr(func, spec):
                            specs[spec] = getattr(func, spec)
                    if specs:
                        self._add_user_code(specs, arg, funcname, func, frame)
                # building hierarchy only makes sense if there are generators
                if isGenSeq and arg:
                    constdict = {}
                    sigdict = {}
                    memdict = {}
                    romdict = {}
                    symdict = frame.f_globals.copy()
                    symdict.update(frame.f_locals)
                    cellvars = []
                    # All nested functions will be in co_consts
                    if func:
                        local_gens = []
                        consts = func.__code__.co_consts
                        for item in _flatten(arg):
                            genfunc = _genfunc(item)
                            if genfunc.__code__ in consts:
                                local_gens.append(item)
                        if local_gens:
                            cellvarlist = _getCellVars(symdict, local_gens)
                            cellvars.extend(cellvarlist)
                            objlist = _resolveRefs(symdict, local_gens)
                            cellvars.extend(objlist)

                    for n, v in symdict.items():
                        # extract signals and memories
                        # also keep track of whether they are used in
                        # generators only include objects that are used in
                        # generators
                        if isinstance(v, _Signal):
                            sigdict[n] = v
                            if n in cellvars:
                                v._markUsed()
                        elif isinstance(v, (int, float, bitarray,
                                            EnumItemType)):
                            constdict[n] = _Constant(n, v)
                        elif _isListOfSigs(v):
                            m = _makeMemInfo(v)
                            memdict[n] = m
                            if n in cellvars:
                                m._used = True
                        elif _isTupleOfInts(v):
                            m = _makeRomInfo(n, v)
                            romdict[n] = m
                            if n in cellvars:
                                m._used = True
                        elif _isTupleOfFloats(v):
                            m = _makeRomInfo(n, v)
                            romdict[n] = m
                            if n in cellvars:
                                m._used = True
                        elif _isTupleOfBitArray(v):
                            m = _makeRomInfo(n, v)
                            romdict[n] = m
                            if n in cellvars:
                                m._used = True

                    subs = []
                    for n, sub in frame.f_locals.items():
                        for elt in _infer_args(arg):
                            if elt is sub:
                                subs.append((n, sub))
                    inst = _Instance(self.level, arg, subs, constdict,
                                     sigdict, memdict, romdict, func, frame)
                    self.hierarchy.append(inst)

                self.level -= 1

            if funcname in self.skipNames:
                self.skip -= 1

    def _add_user_code(self, specs, arg, funcname, func, frame):
        classMap = {
            '__verilog__': _UserVerilogCodeDepr,
            '__vhdl__': _UserVhdlCodeDepr,
            'verilog_code': _UserVerilogCode,
            'vhdl_code': _UserVhdlCode,
            'verilog_instance': _UserVerilogInstance,
            'vhdl_instance': _UserVhdlInstance,
        }
        namespace = frame.f_globals.copy()
        namespace.update(frame.f_locals)
        sourcefile = inspect.getsourcefile(frame)
        sourceline = inspect.getsourcelines(frame)[1]
        for hdl in self.userCodeMap:
            oldspec = "__%s__" % hdl
            codespec = "%s_code" % hdl
            instancespec = "%s_instance" % hdl
            spec = None
            # XXX add warning logic
            if instancespec in specs:
                spec = instancespec
            elif codespec in specs:
                spec = codespec
            elif oldspec in specs:
                spec = oldspec
            if spec:
                assert id(arg) not in self.userCodeMap[hdl]
                code = specs[spec]
                self.userCodeMap[hdl][id(arg)] = classMap[spec](code, namespace,
                                                                funcname, func,
                                                                sourcefile, sourceline)


def _infer_args(arg):
    c = [arg]
    if isinstance(arg, (tuple, list)):
        c += list(arg)
    return c
