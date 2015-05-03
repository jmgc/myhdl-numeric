#  This file is part of the myhdl library, a Python package for using
#  Python as a Hardware Description Language.
#
#  Copyright (C) 2003-2014 Jan Decaluwe
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

""" myhdl toVHDL conversion module.

"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division


import sys
import math
import os

import inspect
from datetime import datetime
#import compiler
#from compiler import ast as astNode
import ast
from types import GeneratorType
import warnings
from copy import copy
import string

import myhdl
from myhdl import *
from myhdl import ToVHDLError, ToVHDLWarning
from .._extractHierarchy import (_HierExtr, _isMem, _getMemInfo,
                                 _UserVhdlCode, _userCodeMap)

from .._instance import _Instantiator
from ..conversion._misc import (_error,_kind,_context,
                                _ConversionMixin, _Label, _genUniqueSuffix, _isConstant)
from ..conversion._analyze import (_analyzeSigs, _analyzeGens, _analyzeTopFunc,
                                   _Ram, _Rom, _enumTypeSet, _constDict, _extConstDict)
from .._Signal import _Signal,_WaiterList
from ..conversion._toVHDLPackage import _package
from .._util import  _flatten
from .._compat import integer_types, class_types, StringIO, PY2
from ..numeric._bitarray import bitarray
from ..numeric._uintba import uintba
from ..numeric._sintba import sintba
from ..numeric._sfixba import sfixba, fixmath
from ..numeric._conversion import (numeric_types,
                                   numeric_functions_dict,
                                   numeric_attributes_dict)

from collections import Callable

_version = myhdl.__version__.replace('.','')
_shortversion = _version.replace('dev','')
_converting = 0
_profileFunc = None
_enumPortTypeSet = set()

def _checkArgs(arglist):
    for arg in arglist:
        if not isinstance(arg, (GeneratorType, _Instantiator, _UserVhdlCode)):
            raise ToVHDLError(_error.ArgType, arg)

def _flatten(*args):
    arglist = []
    for arg in args:
        if id(arg) in _userCodeMap['vhdl']:
            arglist.append(_userCodeMap['vhdl'][id(arg)])
        elif isinstance(arg, (list, tuple, set)):
            for item in arg:
                arglist.extend(_flatten(item))
        else:
            arglist.append(arg)
    return arglist

def _makeDoc(doc, indent=''):
    if doc is None:
        return ''
    doc = inspect.cleandoc(doc)
    pre = '\n' + indent + '-- '
    doc = '-- ' + doc
    doc = doc.replace('\n', pre)
    return doc


class _ToVHDLConvertor(object):

    __slots__ = ("name",
                 "directory",
                 "component_declarations",
                 "header",
                 "no_myhdl_header",
                 "no_myhdl_package",
                 "library",
                 "use_clauses",
                 "architecture",
                 "numeric_ports",
                 "use_fixed_point",
                 )

    def __init__(self):
        self.name = None
        self.directory = None
        self.component_declarations = None
        self.header = ''
        self.no_myhdl_header = False
        self.no_myhdl_package = False
        self.library = "work"
        self.architecture = "MyHDL"
        self.numeric_ports = True
        self.use_clauses = None
        self.use_fixed_point = False

    def __call__(self, func, *args, **kwargs):
        global _converting
        if _converting:
            if 'VHDLVersion' in kwargs:
                kwargs.pop('VHDLVersion')
            return func(*args, **kwargs) # skip
        else:
            # clean start
            sys.setprofile(None)
        from myhdl import _traceSignals
        if _traceSignals._tracing:
            raise ToVHDLError("Cannot use toVHDL while tracing signals")
        if not isinstance(func, Callable):
            raise ToVHDLError(_error.FirstArgType, "got %s" % type(func))

        _converting = 1
        if self.name is None:
            name = func.__name__
        else:
            name = str(self.name)
        try:
            version = None
            if 'VHDLVersion' in kwargs:
                version = kwargs.pop('VHDLVersion')
            h = _HierExtr(name, func, *args, **kwargs)
        finally:
            _converting = 0

        if self.directory is None:
            directory = ''
        else:
            directory = self.directory

        compDecls = self.component_declarations
        useClauses = self.use_clauses

        vpath = os.path.join(directory, name + ".vhd")
        vfile = open(vpath, 'w')
        ppath = os.path.join(directory, "pck_myhdl_%s.vhd" % _shortversion)
        pfile = None
#        # write MyHDL package always during development, as it may change
#        pfile = None
#        if not os.path.isfile(ppath):
#            pfile = open(ppath, 'w')
        if not self.no_myhdl_package:
            pfile = open(ppath, 'w')

        ### initialize properly ###
        _genUniqueSuffix.reset()
        _enumTypeSet.clear()
        _enumPortTypeSet.clear()
        _constDict.clear()
        _extConstDict.clear()

        arglist = _flatten(h.top)
        _checkArgs(arglist)
        genlist = _analyzeGens(arglist, h.absnames)
        siglist, memlist = _analyzeSigs(h.hierarchy, hdl='VHDL')
        # print h.top
        _annotateTypes(genlist)

        ### infer interface
        top_inst = h.hierarchy[0]
        intf = _analyzeTopFunc(top_inst, func, *args, **kwargs)
        intf.name = name
        # sanity checks on interface
        for portname in intf.argnames:
            s = intf.argdict[portname]
            if s._name is None:
                raise ToVHDLError(_error.ShadowingSignal, portname)
            if s._inList:
                raise ToVHDLError(_error.PortInList, portname)
            # add enum types to port-related set
            if isinstance(s._val, EnumItemType):
                obj = s._val._type
                if obj in _enumTypeSet:
                    _enumTypeSet.remove(obj)
                    _enumPortTypeSet.add(obj)
                else:
                    assert obj in _enumPortTypeSet

        doc = _makeDoc(inspect.getdoc(func))

        needPck = len(_enumPortTypeSet) > 0
        lib = self.library
        arch = self.architecture
        numeric = self.numeric_ports

        self._convert_filter(h, intf, siglist, memlist, genlist)

        fixed_point = self.use_fixed_point
        
        if not fixed_point:
            for tree in genlist:
                if hasattr(tree, 'hasFixedPoint'):
                    fixed_point = tree.hasFixedPoint
                    break

        if not fixed_point:
            for sig in siglist:
                if not sig._used:
                    continue
                tipe = inferVhdlClass(sig._init)
                if tipe is not None and issubclass(tipe, vhd_sfixed):
                    fixed_point = True
                    break
        if pfile:
            _writeFileHeader(pfile, ppath)
            print(_package(version, fixed_point), file=pfile)
            pfile.close()

        _writeFileHeader(vfile, vpath)
        if needPck:
            _writeCustomPackage(vfile, intf)
        _writeModuleHeader(vfile, intf, needPck, lib, arch, useClauses, doc,
                           numeric, fixed_point)
        _writeFuncDecls(vfile)
        _writeConstants(vfile)
        _writeTypeDefs(vfile)
        _writeSigDecls(vfile, intf, siglist, memlist)
        _writeCompDecls(vfile, compDecls)
        _convertGens(genlist, siglist, memlist, vfile)
        _writeModuleFooter(vfile, arch)

        vfile.close()
        # tbfile.close()

        ### clean-up properly ###
        self._cleanup(siglist)

        return h.top

    def _cleanup(self, siglist):
        # clean up signal names
        for sig in siglist:
            sig._clear()
#             sig._name = None
#             sig._driven = False
#             sig._read = False

        # clean up attributes
        self.name = None
        self.component_declarations = None
        self.header = ''
        self.no_myhdl_header = False
        self.no_myhdl_package = False
        self.architecture = "MyHDL"
        self.numeric_ports = True


    def _convert_filter(self, h, intf, siglist, memlist, genlist):
        # intended to be a entry point for other uses:
        #  code checking, optimizations, etc
        pass


toVHDL = _ToVHDLConvertor()

myhdl_header = """\
-- File: $filename
-- Generated by MyHDL $version
-- Date: $date
"""

def _writeFileHeader(f, fn):
    vars = dict(filename=fn,
                version=myhdl.__version__,
                date=datetime.today().ctime()
                )
    if toVHDL.header:
        print(string.Template(toVHDL.header).substitute(vars), file=f)
    if not toVHDL.no_myhdl_header:
        print(string.Template(myhdl_header).substitute(vars), file=f)
    print(file=f)


def _writeCustomPackage(f, intf):
    print(file=f)
    print("package pck_%s is" % intf.name, file=f)
    print(file=f)
    print("attribute enum_encoding: string;", file=f)
    print(file=f)
    sortedList = list(_enumPortTypeSet)
    sortedList.sort(key=lambda x: x._name)
    for t in sortedList:
        print("    %s" % t._toVHDL(), file=f)
    print(file=f)
    print("end package pck_%s;" % intf.name, file=f)
    print(file=f)


def _writeModuleHeader(f, intf, needPck, lib, arch, useClauses, doc, numeric,
                       fixed = False):
    print("library IEEE;", file=f)
    print("use IEEE.std_logic_1164.all;", file=f)
    print("use IEEE.numeric_std.all;", file=f)
    if fixed:
        print("use IEEE.fixed_float_types.all;", file=f)
        print("use IEEE.fixed_pkg.all;", file=f)
    print("use std.textio.all;", file=f)
    print(file=f)
    if lib != "work":
        print("library %s;" % lib, file=f)
    if useClauses is not None:
        f.write(useClauses)
        f.write("\n")
    else:
        print("use %s.pck_myhdl_%s.all;" % (lib, _shortversion), file=f)
    print(file=f)
    if needPck:
        print("use %s.pck_%s.all;" % (lib, intf.name), file=f)
        print(file=f)
    print("entity %s is" % intf.name, file=f)
    if intf.argnames:
        f.write("    port (")
        c = ''
        for portname in intf.argnames:
            s = intf.argdict[portname]
            f.write("%s" % c)
            c = ';'
            # make sure signal name is equal to its port name
            s._name = portname
            # make it non-numeric optionally
            if s._type in (intbv, bitarray):
                s._numeric = numeric
            r = _getRangeString(s)
            p = _getTypeString(s)
            if s._driven:
                if s._read:
                    warnings.warn("%s: %s" % (_error.OutputPortRead, portname),
                                  category=ToVHDLWarning
                                  )
                    f.write("\n        %s: inout %s%s" % (portname, p, r))
                else:
                    f.write("\n        %s: out %s%s" % (portname, p, r))
            else:
                if not s._read:
                    warnings.warn("%s: %s" % (_error.UnusedPort, portname),
                                  category=ToVHDLWarning
                                  )
                f.write("\n        %s: in %s%s" % (portname, p, r))
        f.write("\n    );\n")
    print("end entity %s;" % intf.name, file=f)
    print(doc, file=f)
    print(file=f)
    print("architecture %s of %s is" % (arch, intf.name), file=f)
    print(file=f)


def _writeFuncDecls(f):
    return
    # print >> f, package

def _writeConstants(f):
    f.write("\n")
    # guess nice representation
    for c in _constDict:
        if c in _extConstDict:
            continue
        v = _constDict[c]
        s = str(int(v))
        sign = ''
        if v < 0:
            sign = '-'
        for i in range(4, 31):
            if abs(v) == 2**i:
                s = "%s2**%s" % (sign, i)
                break
            if abs(v) == 2**i-1:
                s = "%s2**%s-1" % (sign, i)
                break
        v = _constDict[c]
        f.write("constant %s: integer := %s;\n" % (c, s))
    f.write("\n")

def _writeTypeDefs(f):
    f.write("\n")
    sortedList = list(_enumTypeSet)
    sortedList.sort(key=lambda x: x._name)
    for t in sortedList:
        f.write("%s\n" % t._toVHDL())
    f.write("\n")

constwires = []

def _writeSigDecls(f, intf, siglist, memlist):
    del constwires[:]
    for s in siglist:
        if not s._used:
            continue
        if s._name in intf.argnames:
            continue
        r = _getRangeString(s)
        p = _getTypeString(s)
        if s._driven:
            if not s._read:
                warnings.warn("%s: %s" % (_error.UnreadSignal, s._name),
                              category=ToVHDLWarning
                              )
            # the following line implements initial value assignments
            # print >> f, "%s %s%s = %s;" % (s._driven, r, s._name, int(s._val))
            print("signal %s: %s%s;" % (s._name, p, r), file=f)
        elif s._read:
            # the original exception
            # raise ToVHDLError(_error.UndrivenSignal, s._name)
            # changed to a warning and a continuous assignment to a wire
            warnings.warn("%s: %s" % (_error.UndrivenSignal, s._name),
                          category=ToVHDLWarning
                          )
            constwires.append(s)
            print("signal %s: %s%s;" % (s._name, p, r), file=f)
    for m in memlist:
        if not m._used:
            continue
        # infer attributes for the case of named signals in a list
        for i, s in enumerate(m.mem):
            if not m._driven and s._driven:
                m._driven = s._driven
            if not m._read and s._read:
                m._read = s._read
        if not m._driven and not m._read:
            continue
        r = _getRangeString(m.elObj)
        p = _getTypeString(m.elObj)
        t = "t_array_%s" % m.name
        print("type %s is array(0 to %s) of %s%s;" % (t, m.depth - 1, p, r), file=f)
        print("signal %s: %s;" % (m.name, t), file=f)
    print(file=f)

def _writeCompDecls(f,  compDecls):
    if compDecls is not None:
        print(compDecls, file=f)

def _writeModuleFooter(f, arch):
    print("end architecture %s;" % arch, file=f)

def _getRangeString(s):
    if isinstance(s._val, EnumItemType):
        return ''
    elif s._type is bool:
        return ''
    elif s._type is bitarray:
        return "(%s downto %s)" % (s.high - 1, s.low)
    elif s._nrbits is not None:
        ls = getattr(s, 'lenStr', False)
        if ls:
            msb = ls + '-1'
        else:
            msb = s._nrbits-1
        return "(%s downto 0)" %  msb
    else:
        raise AssertionError

def _getTypeString(s):
    if isinstance(s._val, EnumItemType):
        return s._val._type._name
    elif s._type is bool:
        return "std_logic"
    elif s._type is bitarray:
        obj = inferVhdlObj(s._init)
        if obj is not None:
            return obj.toStr(False)
    if not s._numeric:
        return "std_logic_vector"
    if s._min is not None and s._min < 0:
        return "signed"
    else:
        return "unsigned"

def _convertGens(genlist, siglist, memlist, vfile):
    blockBuf = StringIO()
    funcBuf = StringIO()
    for tree in genlist:
        if isinstance(tree, _UserVhdlCode):
            blockBuf.write(str(tree))
            continue
        if tree.kind == _kind.ALWAYS:
            Visitor = _ConvertAlwaysVisitor
        elif tree.kind == _kind.INITIAL:
            Visitor = _ConvertInitialVisitor
        elif tree.kind == _kind.SIMPLE_ALWAYS_COMB:
            Visitor = _ConvertSimpleAlwaysCombVisitor
        elif tree.kind == _kind.ALWAYS_DECO:
            Visitor = _ConvertAlwaysDecoVisitor
        elif tree.kind == _kind.ALWAYS_SEQ:
            Visitor = _ConvertAlwaysSeqVisitor
        else: # ALWAYS_COMB
            Visitor = _ConvertAlwaysCombVisitor
        v = Visitor(tree, blockBuf, funcBuf)
        v.visit(tree)
    vfile.write(funcBuf.getvalue()); funcBuf.close()
    print("begin", file=vfile)
    print(file=vfile)
    for s in constwires:
        if s._type is bool:
            c = int(s._val)
            pre, suf = "'", "'"
        elif s._type is intbv:
            c = int(s._val)
            w = len(s)
            assert w != 0
            if s._min < 0:
                pre, suf = "to_signed(", ", %s)" % w
            else:
                pre, suf = "to_unsigned(", ", %s)" % w
        elif s._type is bitarray and isinstance(s._val, sintba):
            c = s.__index__()
            w = s.high
            if s.min < 0:
                pre, suf = "to_signed(", ", %s)" % w
            else:
                pre, suf = "to_unsigned(", ", %s)" % w
        elif s._type is bitarray and isinstance(s._val, sfixba):
            c = s.__index__()
            h = s.high
            l = s.low
            pre, suf = "to_sfixed(", ", %s, %s)" % (h - 1, l)
        else:
            raise ToVHDLError("Unexpected type for constant signal", s._name)
        print("%s <= %s%s%s;" % (s._name, pre, c, suf), file=vfile)
    print(file=vfile)
    # shadow signal assignments
    for s in siglist:
        if hasattr(s, 'toVHDL') and s._read:
            print(s.toVHDL(), file=vfile)
    # hack for slice signals in a list
    for m in memlist:
        if m._read:
            for s in m.mem:
                if hasattr(s, 'toVHDL'):
                    print(s.toVHDL(), file=vfile)
    print(file=vfile)
    vfile.write(blockBuf.getvalue()); blockBuf.close()


opmap = {
    ast.Add      : '+',
    ast.Sub      : '-',
    ast.Mult     : '*',
    ast.Div      : '/',
    ast.Mod      : 'mod',
    ast.Pow      : '**',
    ast.LShift   : 'shift_left',
    ast.RShift   : 'shift_right',
    ast.BitOr    : 'or',
    ast.BitAnd   : 'and',
    ast.BitXor   : 'xor',
    ast.FloorDiv : '/',
    ast.Div      : '/',
    ast.Invert   : 'not ',
    ast.Not      : 'not ',
    ast.UAdd     : '+',
    ast.USub     : '-',
    ast.Eq       : '=',
    ast.Gt       : '>',
    ast.GtE      : '>=',
    ast.Lt       : '<',
    ast.LtE      : '<=',
    ast.NotEq    : '/=',
    ast.And      : 'and',
    ast.Or       : 'or',
}


class _ConvertVisitor(ast.NodeVisitor, _ConversionMixin):

    def __init__(self, tree, buf):
        self.tree = tree
        self.buf = buf
        self.returnLabel = tree.name
        self.ind = ''
        self.SigAss = False
        self.isLhs = False
        self.labelStack = []
        self.context = None

    def write(self, arg):
        self.buf.write("%s" % arg)

    def writeline(self, nr=1):
        for i in range(nr):
            self.buf.write("\n%s" % self.ind)

    def writeDoc(self, node):
        assert hasattr(node, 'doc')
        doc = _makeDoc(node.doc, self.ind)
        self.write(doc)
        self.writeline()

    @staticmethod
    def IntRepr(obj):
        if obj >= 0:
            s = "%s" % int(obj)
        else:
            s = "(- %s)" % abs(int(obj))
        return s

    @staticmethod
    def RealRepr(obj):
        if obj >= 0:
            s = "%s" % real(obj)
        else:
            s = "(- %s)" % abs(real(obj))
        return s

    @staticmethod
    def BitRepr(item, var):
        return '"%s"' % bin(item, len(var))

    @staticmethod
    def inferCast(vhd, ori):
        pre, suf = "", ""
        if isinstance(vhd, vhd_nat):
            if not isinstance(ori, vhd_int):
                pre, suf = "to_integer(", ")"
        elif isinstance(vhd, vhd_int):
            if not isinstance(ori, vhd_int):
                pre, suf = "to_integer(", ")"
        elif isinstance(vhd, vhd_real):
            if isinstance(ori, vhd_int):
                pre, suf = "real(", ")"
            elif isinstance(ori, vhd_unsigned):
                pre, suf = "c_u2r(", ")"
            elif isinstance(ori, vhd_signed):
                pre, suf = "c_s2r(", ")"
            elif not isinstance(ori, vhd_real):
                pre, suf = "to_real(", ")"
        elif isinstance(vhd, vhd_unsigned):
            if isinstance(ori, vhd_unsigned):
                if vhd.size != ori.size:
                    pre, suf = "c_u2u(", ", %s)" % vhd.size
            elif isinstance(ori, vhd_signed):
                # note the order of resizing and casting here (otherwise bug!)
                if vhd.size == ori.size:
                    pre, suf = "unsigned(", ")"
                else:
                    # The chain is weird, but it is to chop the upper bits,
                    # taking out the sign, which is the standard methodology
                    # in VHDL. Other option could be to use slices, but the
                    # results are equivalent, and this is more easy to read.
                    pre, suf = "c_s2u(", ", %s)" % vhd.size
            elif isinstance(ori, vhd_sfixed):
                if vhd.trunc or ori.trunc:
                    pre, suf = "t_f2u(", ", %s)" % vhd.size
                else:
                    pre, suf = "c_f2u(", ", %s)" % vhd.size
            elif isinstance(ori, vhd_std_logic):
                pre, suf = "c_l2u(", ", %s)" % vhd.size
            else:
                pre, suf = "c_i2u(", ", %s)" % vhd.size
        elif isinstance(vhd, vhd_signed):
            if isinstance(ori, vhd_signed):
                if ori.size != vhd.size:
                    pre, suf = "c_s2s(", ", %s)" % vhd.size
            elif isinstance(ori, vhd_unsigned):
                if vhd.size != ori.size:
                    pre, suf = "c_u2s(", ", %s)" % vhd.size
                else:
                    pre, suf = "signed(", ")"
            elif isinstance(ori, vhd_sfixed):
                if vhd.trunc or ori.trunc:
                    pre, suf = "t_f2s(", ", %s)" % vhd.size
                else:
                    pre, suf = "c_f2s(", ", %s)" % vhd.size
            elif isinstance(ori, vhd_std_logic):
                pre, suf = "c_l2s(", ", %s)" % vhd.size
            else:
                pre, suf = "c_i2s(", ", %s)" % vhd.size
        elif isinstance(vhd, vhd_sfixed):
            if isinstance(ori, vhd_sfixed):
                if (vhd.size[0] != ori.size[0]) or \
                        (vhd.size[1] != ori.size[1]):
                    if vhd.trunc or ori.trunc:
                        pre, suf = "t_f2f(", ", %s, %s)" % \
                                (vhd.size[0], vhd.size[1])
                    else:
                        pre, suf = "c_f2f(", ", %s, %s)" % \
                                (vhd.size[0], vhd.size[1])
            elif isinstance(ori, vhd_unsigned):
                if vhd.trunc or ori.trunc:
                    pre, suf = "c_u2f(", ", %s, %s)" % (vhd.size[0], vhd.size[1])
                else:
                    pre, suf = "t_u2f(", ", %s, %s)" % (vhd.size[0], vhd.size[1])
            elif isinstance(ori, vhd_signed):
                if vhd.trunc or ori.trunc:
                    pre, suf = "c_s2f(", ", %s, %s)" % (vhd.size[0], vhd.size[1])
                else:
                    pre, suf = "t_s2f(", ", %s, %s)" % (vhd.size[0], vhd.size[1])
            elif isinstance(ori, vhd_std_logic):
                pre, suf = "c_l2f(", ", %s, %s)" % (vhd.size[0], vhd.size[1])
            elif isinstance(ori, vhd_string):
                pre, suf = "c_str2f(", ", %s, %s)" % \
                            (vhd.size[0], vhd.size[1])
            elif isinstance(ori, vhd_real):
                pre, suf = "to_sfixed(", ", %s, %s)" % (vhd.size[0], vhd.size[1])
            else:
                pre, suf = "c_i2f(", ", %s, %s)" % (vhd.size[0], vhd.size[1])
        elif isinstance(vhd, vhd_boolean):
            if not isinstance(ori, vhd_boolean):
                pre, suf = "bool(", ")"
        elif isinstance(vhd, vhd_std_logic):
            if not isinstance(ori, vhd_std_logic):
                if isinstance(ori, vhd_unsigned) :
                    pre, suf = "", "(0)"
                else:
                    pre, suf = "stdl(", ")"
        elif isinstance(vhd, vhd_string):
            if isinstance(ori, vhd_enum):
                pre, suf = "%s'image(" % ori._type._name, ")"

        return pre, suf

    def writeIntSize(self, n):
        # write size for large integers (beyond 32 bits signed)
        # with some safety margin
        if n >= 2**30:
            size = int(math.ceil(math.log(n+1,2))) + 1  # sign bit!
            self.write("%s'sd" % size)

    def writeDeclaration(self, obj, name, kind="", dir="", endchar=";", constr=True):
        if isinstance(obj, EnumItemType):
            tipe = obj._type._name
        elif isinstance(obj, _Ram):
            tipe = "t_array_%s" % name
            elt = inferVhdlObj(obj.elObj).toStr(True)
            self.write("type %s is array(0 to %s) of %s;" % (tipe, obj.depth - 1, elt))
            self.writeline()
        else:
            vhd = inferVhdlObj(obj)
            if isinstance(vhd, vhd_enum):
                tipe = obj._val._type._name
            else:
                tipe = vhd.toStr(constr)
        if kind: kind += " "
        if dir: dir += " "
        self.write("%s%s: %s%s%s" % (kind, name, dir, tipe, endchar))

    def writeDeclarations(self):
        if self.tree.hasPrint:
            self.writeline()
            self.write("variable L: line;")
        for name, obj in self.tree.vardict.items():
            if isinstance(obj, _loopInt):
                continue # hack for loop vars
            self.writeline()
            self.writeDeclaration(obj, name, kind="variable")

    def indent(self):
        self.ind += ' ' * 4

    def dedent(self):
        self.ind = self.ind[:-4]

    def visit_BinOp(self, node):
        if isinstance(node.op, (ast.LShift, ast.RShift)):
            self.shiftOp(node)
        elif isinstance(node.op, (ast.BitAnd, ast.BitOr, ast.BitXor)):
            self.BitOp(node)
        elif isinstance(node.op, ast.Mod) and (self.context == _context.PRINT):
            self.visit(node.left)
            self.write(", ")
            self.visit(node.right)
        else:
            self.BinOp(node)

    def inferBinaryOpCast(self, node, left, right, op):
        if isinstance(left.vhd, vhd_sfixed) or \
                isinstance(right.vhd, vhd_sfixed):
            vhd_sfixed.inferBinaryOpCast(node, left, right, op)
        elif isinstance(left.vhd, vhd_vector) or \
                isinstance(right.vhd, vhd_vector):
            vhd_vector.inferBinaryOpCast(node, left, right, op)
        pre, suf = self.inferCast(node.vhd, node.vhdOri)
        if isinstance(node.op, ast.FloorDiv) and \
                isinstance(node.vhdOri, vhd_sfixed):
            pre = pre + 'floor('
            suf = ')' + suf
        if pre == "":
            pre, suf = "(", ")"
        return pre, suf

    def BinOp(self, node):
        pre, suf = self.inferBinaryOpCast(node, node.left, node.right, node.op)
        self.write(pre)
        self.visit(node.left)
        self.write(" %s " % opmap[type(node.op)])
        self.visit(node.right)
        self.write(suf)

    def inferShiftOpCast(self, node, left, right, op):
        if isinstance(left.vhd, vhd_sfixed):
            vhd_sfixed.inferShiftOpCast(node, left, right, op)
        if isinstance(left.vhd, vhd_vector):
            vhd_vector.inferShiftOpCast(node, left, right, op)
        pre, suf = self.inferCast(node.vhd, node.vhdOri)
        return pre, suf

    def shiftOp(self, node):
        pre, suf = self.inferShiftOpCast(node, node.left, node.right, node.op)
        self.write(pre)
        self.write("%s(" % opmap[type(node.op)])
        self.visit(node.left)
        self.write(", ")
        self.visit(node.right)
        self.write(")")
        self.write(suf)

    def BitOp(self, node):
        pre, suf = self.inferCast(node.vhd, node.vhdOri)
        self.write(pre)
        self.write("(")
        self.visit(node.left)
        self.write(" %s " % opmap[type(node.op)])
        self.visit(node.right)
        self.write(")")
        self.write(suf)

    def visit_BoolOp(self, node):
        if isinstance(node.vhd, vhd_std_logic):
            self.write("stdl")
        self.write("(")
        self.visit(node.values[0])
        for n in node.values[1:]:
            self.write(" %s " % opmap[type(node.op)])
            self.visit(n)
        self.write(")")

    def visit_UnaryOp(self, node):
        if isinstance(node.op, ast.USub):
            if isinstance(node.operand, ast.Num):
                n = node.operand.n
                newnode = copy(node.operand)
                newnode.n = -n
                newnode.vhd = node.vhd
                newnode.vhdOri = node.vhdOri
                self.visit(newnode)
                return
        pre, suf = self.inferCast(node.vhd, node.vhdOri)
        self.write(pre)
        self.write("(")
        if not isinstance(node.op, ast.UAdd):
            self.write(opmap[type(node.op)])
        self.visit(node.operand)
        self.write(")")
        self.write(suf)

    def visit_Attribute(self, node):
        if isinstance(node.ctx, ast.Store):
            self.setAttr(node)
        else:
            self.getAttr(node)

    def setAttr(self, node):
        assert node.attr == 'next'
        self.SigAss = True
        if isinstance(node.value, ast.Name):
            sig = self.tree.symdict[node.value.id]
            self.SigAss = sig._name
        self.visit(node.value)
        node.obj = self.getObj(node.value)

    def getAttr(self, node):
        if isinstance(node.value, ast.Subscript):
            self.setAttr(node)
            return

        assert isinstance(node.value, ast.Name), node.value
        n = node.value.id
        if n in self.tree.symdict:
            obj = self.tree.symdict[n]
        elif n in self.tree.vardict:
            obj = self.tree.vardict[n]
        else:
            raise AssertionError("object not found")
        if isinstance(obj, _Signal):
            if node.attr == 'next':
                sig = self.tree.symdict[node.value.id]
                self.SigAss = obj._name
                self.visit(node.value)
            elif node.attr == 'posedge':
                self.write("rising_edge(")
                self.visit(node.value)
                self.write(")")
            elif node.attr == 'negedge':
                self.write("falling_edge(")
                self.visit(node.value)
                self.write(")")
            elif node.attr == 'val':
                pre, suf = self.inferCast(node.vhd, node.vhdOri)
                self.write(pre)
                self.visit(node.value)
                self.write(suf)
        if isinstance(obj, (_Signal, intbv, bitarray)):
            if node.attr in numeric_attributes_dict:
                pre, suf = self.inferCast(node.vhd, node.vhdOri)
                self.write(pre)
                self.write("%s" % node.obj)
                self.write(suf)
        if isinstance(obj, EnumType):
            assert hasattr(obj, node.attr)
            e = getattr(obj, node.attr)
            self.write(e._toVHDL())

    def visit_Assert(self, node):
        # XXX
        self.write("assert ")
        self.visit(node.test)
        self.indent()
        self.writeline()
        self.write('report "*** AssertionError ***"')
        self.writeline()
        self.write("severity error;")
        self.dedent()

    def visit_Assign(self, node):
        lhs = node.targets[0]
        rhs = node.value
        # shortcut for expansion of ROM in case statement
        if isinstance(node.value, ast.Subscript) and \
                isinstance(node.value.slice, ast.Index) and \
                isinstance(node.value.value.obj, _Rom):
            rom = node.value.value.obj.rom
            self.write("case ")
            self.visit(node.value.slice)
            self.write(" is")
            self.indent()
            size = lhs.vhd.size
            for i, n in enumerate(rom):
                self.writeline()
                if i == len(rom)-1:
                    self.write("when others => ")
                else:
                    self.write("when %s => " % i)
                self.visit(lhs)
                if self.SigAss:
                    self.write(' <= ')
                    self.SigAss = False
                else:
                    self.write(' := ')
                if isinstance(lhs.vhd, vhd_std_logic):
                    self.write("'%s';" % n)
                elif isinstance(lhs.vhd, vhd_int):
                    self.write("%s;" % n)
                elif isinstance(lhs.vhd, vhd_sfixed):
                    high = size[0]
                    low = size[1]
                    self.write('resize(c_str2f(')
                    self.write('"%s"' % bin(n, high + 1))
                    self.write('), %s, %s);' % (high, low))
                else:
                    self.write('"%s";' % bin(n, size))
            self.dedent()
            self.writeline()
            self.write("end case;")
            return
        elif isinstance(node.value, ast.ListComp):
            # skip list comprehension assigns for now
            return
        # default behavior
        if isinstance(lhs.vhd, vhd_type):
            rhs.vhd = lhs.vhd
        convOpen, convClose = "", ""
        self.isLhs = True
        self.visit(lhs)
        self.isLhs = False
        if self.SigAss:
            if isinstance(lhs.value, ast.Name):
                sig = self.tree.symdict[lhs.value.id]
                if not sig._numeric:
                    #if not isinstance(rhs, ast.Num):
                    convOpen, convClose = "std_logic_vector(", ")"
            self.write(' <= ')
            self.SigAss = False
        else:
            self.write(' := ')
        self.write(convOpen)
        # node.expr.target = obj = self.getObj(node.nodes[0])
        self.visit(rhs)
        self.write(convClose)
        self.write(';')

    def visit_AugAssign(self, node):
        # XXX apparently no signed context required for augmented assigns
        left, op, right =  node.target, node.op, node.value
        isFunc = False
        pre, suf = "", ""
        if isinstance(op, (ast.Add, ast.Sub, ast.Mult, ast.Mod,
                           ast.FloorDiv, ast.Div)):
            pre, suf = self.inferBinaryOpCast(node, left, right, op)
        elif isinstance(op, (ast.LShift, ast.RShift)):
            isFunc = True
            pre, suf = self.inferShiftOpCast(node, left, right, op)
        elif isinstance(op, (ast.BitAnd, ast.BitOr, ast.BitXor)):
            pre, suf = self.inferCast(node.vhd, node.vhdOri)
        self.visit(left)
        self.write(" := ")
        self.write(pre)
        if isFunc:
            self.write("%s(" % opmap[type(op)])
        left_pre, left_suf = self.inferCast(left.vhd, left.vhdOri)
        self.write(left_pre)
        self.visit(left)
        self.write(left_suf)
        if isFunc:
            self.write(", ")
        else:
            self.write(" %s " % opmap[type(op)])
        self.visit(right)
        if isFunc:
            self.write(")")
        self.write(suf)
        self.write(";")

    def visit_Break(self, node):
        self.write("exit;")

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            fn = node.func
            if fn.id == 'print':
                self.visit_Print(node)
                return
        else:
            fn = node.func
        # assert isinstance(fn, astNode.Name)
        f = self.getObj(fn)

        if f is print:
            self.visit_Print(node)
            return

        fname = ''
        pre, suf = '', ''
        opening, closing = '(', ')'
        sep = ", "
        if f is bool:
            opening, closing = '', ''
            arg = node.args[0]
            arg.vhd = node.vhd
        elif f is len:
            val = self.getVal(node)
            self.require(node, val is not None, "cannot calculate len")
            self.write(repr(val))
            return
        elif f is now:
            pre, suf = self.inferCast(node.vhd, node.vhdOri)
            self.write(pre)
            self.write("(now / 1 ns)")
            self.write(suf)
            return
        elif f is ord:
            opening, closing = '', ''
            if isinstance(node.args[0], ast.Str):
                if len(node.args[0].s) > 1:
                    self.raiseError(node, _error.UnsupportedType, "Strings with length > 1" )
                else:
                    node.args[0].s = ord(node.args[0].s)
        elif f in integer_types:
            opening, closing = '', ''
            # convert number argument to integer
            if isinstance(node.args[0], ast.Num):
                node.args[0].n = int(node.args[0].n)
        elif f is float:
            opening, closing = '', ''
            # convert number argument to integer
            if isinstance(node.args[0], ast.Num):
                node.args[0].n = float(node.args[0].n)
        elif inspect.isclass(f) and issubclass(f, (intbv, bitarray)):
            pre, post = "", ""
            arg = node.args[0]
            pre, post = self.inferCast(node.vhd, arg.vhdOri)
            self.write(pre)
            self.visit(arg)
            self.write(post)
            return
        elif f == intbv.signed: # note equality comparison
            # this call comes from a getattr
            arg = fn.value
            pre, suf = self.inferCast(node.vhd, node.vhdOri)
            opening, closing = '', ''
            if isinstance(arg.vhd, vhd_unsigned):
                opening, closing = "signed(", ")"
            self.write(pre)
            self.write(opening)
            self.visit(arg)
            self.write(closing)
            self.write(suf)
            return
        elif (type(f) in class_types) and issubclass(f, Exception):
            self.write(f.__name__)
        elif f in (posedge, negedge):
            opening, closing = ' ', ''
            self.write(f.__name__)
        elif f is delay:
            self.visit(node.args[0])
            self.write(" ns")
            return
        elif f is concat:
            pre, suf = self.inferCast(node.vhd, node.vhdOri)
            opening, closing =  "unsigned'(", ")"
            sep = " & "
        elif hasattr(node, 'tree'):
            pre, suf = self.inferCast(node.vhd, node.tree.vhd)
            fname = node.tree.name
        elif f in numeric_functions_dict.values():
            pre, suf = self.inferCast(node.vhd, node.vhdOri)
            fname = f.__name__
        else:
            pre, suf = self.inferCast(node.vhd, node.vhdOri)
        if node.args:
            self.write(pre)
            # TODO rewrite making use of fname variable
            self.write(fname)
            self.write(opening)
            self.visit(node.args[0])
            for arg in node.args[1:]:
                self.write(sep)
                self.visit(arg)
            self.write(closing)
            self.write(suf)
        if hasattr(node, 'tree'):
            if node.tree.kind == _kind.TASK:
                Visitor = _ConvertTaskVisitor
            else:
                Visitor = _ConvertFunctionVisitor
            v = Visitor(node.tree, self.funcBuf)
            v.visit(node.tree)

    def visit_Compare(self, node):
        n = node.vhd
        ns = node.vhd.size
        pre, suf = "(", ")"
        if isinstance(n, vhd_std_logic):
            pre = "stdl("
        elif isinstance(n, vhd_unsigned):
            pre, suf = "to_unsigned(", ", %s)" % ns
        elif isinstance(n, vhd_signed):
            pre, suf = "to_signed(", ", %s)" % ns
        elif isinstance(n, vhd_sfixed):
            pre, suf = "to_sfixed(", ", %s, %s)" % ns
        self.write(pre)
        self.visit(node.left)
        op, right = node.ops[0], node.comparators[0]
        self.write(" %s " % opmap[type(op)])
        self.visit(right)
        self.write(suf)

    def visit_Num(self, node):
        n = node.n
        if isinstance(node.vhd, vhd_std_logic):
            self.write("'%s'" % n)
        elif isinstance(node.vhd, vhd_boolean):
            self.write("%s" % bool(n))
        elif isinstance(node.vhd, vhd_unsigned):
            if abs(n) < 2**31:
                self.write("to_unsigned(%s, %s)" % (n, node.vhd.size))
            else:
                self.write('unsigned\'("%s")' % bin(n, node.vhd.size))
        elif isinstance(node.vhd, vhd_signed):
            if abs(n) < 2**31:
                self.write("to_signed(%s, %s)" % (n, node.vhd.size))
            else:
                self.write('signed\'("%s")' % bin(n, node.vhd.size))
        elif isinstance(node.vhd, vhd_sfixed):
            if isinstance(n, integer_types):
                self.write('resize(c_str2f("%s"), %s, %s)' % \
                           (bin(n, node.vhd.size[0] + 1),
                            node.vhd.size[0],
                            node.vhd.size[1]))
            else:
                self.write('to_sfixed(%s, %s, %s)' % \
                           (n, node.vhd.size[0], node.vhd.size[1]))
        elif isinstance(node.vhd, vhd_nat):
            if isinstance(node.vhdOri, vhd_nat):
                pre, suf = "(", ")"
            elif isinstance(node.vhdOri, vhd_int):
                pre, suf = "natural(", ")"
            if n < 0:
                self.write(pre)
            self.write(n)
            if n < 0:
                self.write(suf)
        elif isinstance(node.vhd, vhd_int):
            if isinstance(node.vhdOri, vhd_nat):
                pre, suf = "integer(", ")"
            elif isinstance(node.vhdOri, vhd_int):
                pre, suf = "(", ")"
            if n < 0:
                self.write(pre)
            self.write(n)
            if n < 0:
                self.write(suf)
        elif isinstance(node.vhd, vhd_real):
            if isinstance(node.vhdOri, vhd_int):
                pre, suf = "real(", ")"
            elif isinstance(node.vhdOri, vhd_real):
                pre, suf = "(", ")"
            if n < 0:
                self.write(pre)
            self.write(float(n))
            if n < 0:
                self.write(suf)

    def visit_Str(self, node):
        typemark = 'string'
        if isinstance(node.vhd, vhd_unsigned):
            typemark = 'unsigned'
        self.write("%s'(\"%s\")" % (typemark, node.s))

    def visit_Continue(self, node, *args):
       self.write("next;")

    def visit_Expr(self, node):
        expr = node.value
        # docstrings on unofficial places
        if isinstance(expr, ast.Str):
            doc = _makeDoc(expr.s, self.ind)
            self.write(doc)
            return
        # skip extra semicolons
        if isinstance(expr, ast.Num):
            return
        self.visit(expr)
        # ugly hack to detect an orphan "task" call
        if isinstance(expr, ast.Call) and hasattr(expr, 'tree'):
            self.write(';')

    def visit_IfExp(self, node):
        pre, suf = self.inferCast(node.vhd, node.body.vhdOri)
        self.write(pre)
        self.visit(node.body)
        self.write(suf)
        self.write(' when ')
        self.visit(node.test)
        self.write(' else ')
        pre, suf = self.inferCast(node.vhd, node.orelse.vhdOri)
        self.write(pre)
        self.visit(node.orelse)
        self.write(suf)

    def visit_For(self, node):
        self.labelStack.append(node.breakLabel)
        self.labelStack.append(node.loopLabel)
        var = node.target.id
        cf = node.iter
        f = self.getObj(cf.func)
        args = cf.args
        assert len(args) <= 3
        self.require(node, len(args) < 3, "explicit step not supported")
        if f is range:
            cmp = '<'
            op = 'to'
            oneoff = ''
            if len(args) == 1:
                start, stop, step = None, args[0], None
            elif len(args) == 2:
                start, stop, step = args[0], args[1], None
            else:
                start, stop, step = args
        else: # downrange
            cmp = '>='
            op = 'downto'
            if len(args) == 1:
                start, stop, step = args[0], None, None
            elif len(args) == 2:
                start, stop, step = args[0], args[1], None
            else:
                start, stop, step = args
        assert step is None
##        if node.breakLabel.isActive:
##             self.write("begin: %s" % node.breakLabel)
##             self.writeline()
##         if node.loopLabel.isActive:
##             self.write("%s: " % node.loopLabel)
        self.write("for %s in " % var)
        if start is None:
            self.write("0")
        else:
            self.write("integer(")
            self.visit(start)
            if f is downrange:
                self.write("-1")
            self.write(")")
        self.write(" %s " % op)
        self.write("integer(")
        if stop is None:
            self.write("0")
        else:
            self.visit(stop)
            if f is range:
                self.write("-1")
        self.write(")")
        self.write(" loop")
        self.indent()
        self.visit_stmt(node.body)
        self.dedent()
        self.writeline()
        self.write("end loop;")
##         if node.breakLabel.isActive:
##             self.writeline()
##             self.write("end")
        self.labelStack.pop()
        self.labelStack.pop()

    def visit_FunctionDef(self, node):
        raise AssertionError("To be implemented in subclass")

    def visit_If(self, node):
        if node.ignore:
            return
        # only map to VHDL case if it's a full case
        if node.isFullCase:
            self.mapToCase(node)
        else:
            self.mapToIf(node)

    def mapToCase(self, node):
        var = node.caseVar
        obj = self.getObj(var)
        self.write("case ")
        self.visit(var)
        self.write(" is")
        self.indent()
        for i, (test, suite) in enumerate(node.tests):
            self.writeline()
            item = test.case[1]
            if isinstance(item, EnumItemType):
                itemRepr = item._toVHDL()
            elif hasattr(obj, '_nrbits'):
                itemRepr = self.BitRepr(item, obj)
            else:
                itemRepr = i
            comment = ""
            self.write("when ")
            self.write(itemRepr)
            self.write(" =>%s" % comment)
            self.indent()
            self.visit_stmt(suite)
            self.dedent()
        if node.else_:
            self.writeline()
            self.write("when others =>")
            self.indent()
            self.visit_stmt(node.else_)
            self.dedent()
        else:
            self.writeline()
            self.write("when others =>")
            self.indent()
            self.writeline()
            self.write("null;")
            self.dedent()
        self.dedent()
        self.writeline()
        self.write("end case;")

    def mapToIf(self, node):
        first = True
        for test, suite in node.tests:
            if first:
                ifstring = "if "
                first = False
            else:
                ifstring = "elsif "
                self.writeline()
            self.write(ifstring)
            self.visit(test)
            self.write(" then")
            self.indent()
            self.visit_stmt(suite)
            self.dedent()
        if node.else_:
            self.writeline()
            edges = self.getEdge(node)
            if edges is not None:
                edgeTests = [e._toVHDL() for e in edges]
                self.write("elsif ")
                self.write(" or ".join(edgeTests))
                self.write(" then")
            else:
                self.write("else")
            self.indent()
            self.visit_stmt(node.else_)
            self.dedent()
        self.writeline()
        self.write("end if;")

    def visit_ListComp(self, node):
        pass # do nothing

    def visit_Module(self, node):
        for stmt in node.body:
            self.visit(stmt)

    def visit_NameConstant(self, node):
        node.id = str(node.value)
        self.getName(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.setName(node)
        else:
            self.getName(node)

    def visit_NameConstant(self, node):
        self.getName(node)

    def setName(self, node):
        self.write(node.id)

    def getName(self, node):
        if (not PY2) and isinstance(node, ast.NameConstant):
            n = str(node.value)
        else:
            n = node.id
        if n == 'False':
            if isinstance(node.vhd, vhd_std_logic):
                s = "'0'"
            else:
                s = "False"
        elif n == 'True':
            if isinstance(node.vhd, vhd_std_logic):
                s = "'1'"
            else:
                s = "True"
        elif n == 'None':
            s = "(others => 'Z')"
        elif n in self.tree.vardict:
            s = n
            obj = self.tree.vardict[n]
            ori = inferVhdlObj(obj)
            pre, suf = self.inferCast(node.vhd, ori)
            s = "%s%s%s" % (pre, s, suf)

        elif n in self.tree.argnames:
            assert n in self.tree.symdict
            obj = self.tree.symdict[n]
            vhd = inferVhdlObj(obj)
            if isinstance(vhd, vhd_std_logic) and isinstance(node.vhd, vhd_boolean):
                s = "(%s = '1')" %  n
            else:
                s = n
        elif n in self.tree.symdict:
            obj = self.tree.symdict[n]
            s = n
            if isinstance(obj, bool):
                s = "'%s'" % int(obj)
                # print the symbol for a boolean in the global constant dict
                if n in _constDict and obj == _constDict[n]:
                    if isinstance(node.vhd, vhd_boolean):
                        s = "bool(%s)" % n
            elif isinstance(obj, integer_types):
                # print the symbol for an integer in the global constant dict
                if n in _constDict and obj == _constDict[n]:
                    assert abs(obj) < 2**31
                    if isinstance(node.vhd, (vhd_int, vhd_real)):
                        s = n
                    elif isinstance(node.vhd, vhd_boolean):
                        s = "bool(%s)" % n
                    elif isinstance(node.vhd, vhd_std_logic):
                        s = "stdl(%s)" % n
                    elif isinstance(node.vhd, vhd_unsigned):
                        s = "to_unsigned(%s, %s)" % (n, node.vhd.size)
                    elif isinstance(node.vhd, vhd_signed):
                        s = "to_signed(%s, %s)" % (n, node.vhd.size)
                    elif isinstance(node.vhd, vhd_sfixed):
                        s = 'resize(to_sfixed("%s", %s, 0), %s, %s)' % \
                                    (n, vhd.size[0],
                                     vhd.size[0], vhd.size[1])
                else:
                    if isinstance(node.vhd, vhd_int):
                        s = self.IntRepr(obj)
                    elif isinstance(node.vhd, vhd_real):
                        s = self.RealRepr(obj)
                    elif isinstance(node.vhd, vhd_std_logic):
                        s = "'%s'" % int(obj)
                    elif isinstance(node.vhd, vhd_unsigned):
                        if abs(obj) < 2** 31:
                            s = "to_unsigned(%s, %s)" % (n, node.vhd.size)
                        else:
                            s = 'unsigned\'("%s")' % bin(obj, node.vhd.size)
                    elif isinstance(node.vhd, vhd_signed):
                        if abs(obj) < 2** 31:
                            s = "to_signed(%s, %s)" % (n, node.vhd.size)
                        else:
                            s = 'signed\'("%s")' % bin(obj, node.vhd.size)
                    elif isinstance(node.vhd, vhd_sfixed):
                        s = "c_str2f(%s, %s, %s)" % \
                                (bin(obj, node.vhd.size[0] -
                                     node.vhd.size[1] + 1),
                                 node.vhd.size[0], node.vhd.size[1])
            elif isinstance(obj, _Signal):
                s = str(obj)
                ori = inferVhdlObj(obj)
                # print 'name', n
                # support for non-numeric signals
                if self.SigAss is not obj._name and not obj._numeric:
                    if obj._min < 0:
                        s = "signed(%s)" %s
                    else:
                        s = "unsigned(%s)" %s
                pre, suf = self.inferCast(node.vhd, ori)
                s = "%s%s%s" % (pre, s, suf)
            elif _isMem(obj):
                m = _getMemInfo(obj)
                assert m.name
                s = m.name
            elif isinstance(obj, EnumItemType):
                s = obj._toVHDL()
            elif (type(obj) in class_types) and issubclass(obj, Exception):
                s = n
            else:
                self.raiseError(node, _error.UnsupportedType, "%s, %s" % (n, type(obj)))
        else:
            raise ToVHDLError(_error.NotSupported, "name ref: %s" % n)
        self.write(s)

    def visit_Pass(self, node):
        self.write("null;")

    def visit_Print(self, node):
        argnr = 0
        for s in node.format:
            if isinstance(s, str):
                self.write('write(L, string\'("%s"));' % s)
            else:
                a = node.args[argnr]
                argnr += 1
                if s.conv is int:
                    a.vhd = vhd_int()
                else:
                    if isinstance(a.vhdOri, vhd_vector):
                        a.vhd = vhd_int()
                    elif isinstance(a.vhdOri, vhd_std_logic):
                        a.vhd = vhd_boolean()
                    elif isinstance(a.vhdOri, vhd_enum):
                        a.vhd = vhd_string()
                self.write("write(L, ")
                self.context = _context.PRINT
                self.visit(a)
                self.context = None
                if s.justified == 'LEFT':
                    self.write(", justified=>LEFT")
                if s.width:
                    self.write(", field=>%s" % s.width)
                self.write(")")
                self.write(';')
            self.writeline()
        self.write("writeline(output, L);")

    def visit_Raise(self, node):
        self.write('assert False report "End of Simulation" severity Failure;')

    def visit_Return(self, node):
        pass

    def visit_Subscript(self, node):
        if isinstance(node.slice, ast.Slice):
            self.accessSlice(node)
        else:
            self.accessIndex(node)

    def accessSlice(self, node):
        if isinstance(node.value, ast.Call) and \
           issubclass(node.value.func.obj, (intbv, bitarray)) and \
           _isConstant(node.value.args[0], self.tree.symdict):
            c = self.getVal(node)._val
            pre, post = "", ""
            if isinstance(node.vhd, vhd_unsigned):
                if node.vhd.size <= 30:
                    pre, post = "to_unsigned(", ", %s)" % node.vhd.size
                else:
                    pre, post = "unsigned'(", ")"
                    c = '"%s"' % bin(c, node.vhd.size)
            elif isinstance(node.vhd, vhd_signed):
                if node.vhd.size <= 30:
                    pre, post = "to_signed(", ", %s)" % node.vhd.size
                else:
                    pre, post = "signed'(", ")"
                    c = '"%s"' % bin(c, node.vhd.size)
            elif isinstance(node.vhd, vhd_sfixed):
                pre, post = "c_str2f(", ", %s, %s)" % \
                        (node.vhd.size[0], node.vhd.size[1])
                c = '"%s"' % bin(c, node.vhd.size[0] - node.vhd.size[1] + 1)
            self.write(pre)
            self.write("%s" % c)
            self.write(post)
            return
        pre, suf = self.inferCast(node.vhd, node.vhdOri)
        if isinstance(node.value.vhd, vhd_signed) and isinstance(node.ctx, ast.Load):
            pre = pre + "unsigned("
            suf = ")" + suf
        self.write(pre)
        self.visit(node.value)
        lower, upper = node.slice.lower, node.slice.upper
        # special shortcut case for [:] slice
        self.write("(")
        size = node.value.vhd.size
        if type(size) is tuple:
            high = size[0]
            low = size[1]
        else:
            high = size - 1
            low = 0

        if lower is None:
            self.write("%s" % high)
        else:
            self.write("integer(")
            self.visit(lower)
            self.write("-1)")
        self.write(" downto ")
        if upper is None:
            self.write("%s" % low)
        else:
            self.visit(upper)
        self.write(")")
        self.write(suf)

    def accessIndex(self, node):
        pre, suf = self.inferCast(node.vhd, node.vhdOri)
        self.write(pre)
        self.visit(node.value)
        self.write("(")
        #assert len(node.subs) == 1
        self.visit(node.slice.value)
        self.write(")")
        self.write(suf)

    def visit_stmt(self, body):
        for stmt in body:
            self.writeline()
            self.visit(stmt)
            # ugly hack to detect an orphan "task" call
            if isinstance(stmt, ast.Call) and hasattr(stmt, 'tree'):
                self.write(';')

    def visit_Tuple(self, node):
        assert self.context != None
        sep = ", "
        tpl = node.elts
        self.visit(tpl[0])
        for elt in tpl[1:]:
            self.write(sep)
            self.visit(elt)

    def visit_While(self, node):
        self.labelStack.append(node.breakLabel)
        self.labelStack.append(node.loopLabel)
        self.write("while ")
        self.visit(node.test)
        self.write(" loop")
        self.indent()
        self.visit_stmt(node.body)
        self.dedent()
        self.writeline()
        self.write("end loop")
        self.write(";")
        self.labelStack.pop()
        self.labelStack.pop()

    def visit_Yield(self, node):
        self.write("wait ")
        yieldObj = self.getObj(node.value)
        if isinstance(yieldObj, delay):
            self.write("for ")
        elif isinstance(yieldObj, _WaiterList):
            self.write("until ")
        else:
            self.write("on ")
        self.context = _context.YIELD
        self.visit(node.value)
        self.context = _context.UNKNOWN
        self.write(";")

    def manageEdges(self, ifnode, senslist):
        """ Helper method to convert MyHDL style template into VHDL style"""
        first = senslist[0]
        if isinstance(first, _WaiterList):
            bt = _WaiterList
        elif isinstance(first, _Signal):
            bt = _Signal
        elif isinstance(first, delay):
            bt  = delay
        assert bt
        for e in senslist:
            if not isinstance(e, bt):
                self.raiseError(ifnode, "base type error in sensitivity list")
        if len(senslist) >= 2 and bt == _WaiterList:
            # ifnode = node.code.nodes[0]
            # print ifnode
            assert isinstance(ifnode, ast.If)
            asyncEdges = []
            for test, suite in ifnode.tests:
                e = self.getEdge(test)
                if e is None:
                    self.raiseError(ifnode, "No proper edge value test")
                asyncEdges.append(e)
            if not ifnode.else_:
                self.raiseError(ifnode, "No separate else clause found")
            edges = []
            for s in senslist:
                for e in asyncEdges:
                    if s is e:
                        break
                else:
                    edges.append(s)
            ifnode.edge = edges
            senslist = [s.sig for s in senslist]
        return senslist


class _ConvertAlwaysVisitor(_ConvertVisitor):

    def __init__(self, tree, blockBuf, funcBuf):
        _ConvertVisitor.__init__(self, tree, blockBuf)
        self.funcBuf = funcBuf

    def visit_FunctionDef(self, node):
        self.writeDoc(node)
        w = node.body[-1]
        y = w.body[0]
        if isinstance(y, ast.Expr):
            y = y.value
        assert isinstance(y, ast.Yield)
        senslist = y.senslist
        senslist = self.manageEdges(w.body[1], senslist)
        singleEdge = (len(senslist) == 1) and isinstance(senslist[0], _WaiterList)
        self.write("%s: process (" % self.tree.name)
        if singleEdge:
            self.write(senslist[0].sig)
        else:
            for e in senslist[:-1]:
                self.write(e)
                self.write(', ')
            self.write(senslist[-1])
        self.write(") is")
        self.indent()
        self.writeDeclarations()
        self.dedent()
        self.writeline()
        self.write("begin")
        self.indent()
        if singleEdge:
            self.writeline()
            self.write("if %s then" % senslist[0]._toVHDL())
            self.indent()
        # assert isinstance(w.body, ast.stmt)
        for stmt in w.body[1:]:
            self.writeline()
            self.visit(stmt)
        self.dedent()
        if singleEdge:
            self.writeline()
            self.write("end if;")
            self.dedent()
        self.writeline()
        self.write("end process %s;" % self.tree.name)
        self.writeline(2)


class _ConvertInitialVisitor(_ConvertVisitor):

    def __init__(self, tree, blockBuf, funcBuf):
        _ConvertVisitor.__init__(self, tree, blockBuf)
        self.funcBuf = funcBuf

    def visit_FunctionDef(self, node):
        self.writeDoc(node)
        self.write("%s: process is" % self.tree.name)
        self.indent()
        self.writeDeclarations()
        self.dedent()
        self.writeline()
        self.write("begin")
        self.indent()
        self.visit_stmt(node.body)
        self.writeline()
        self.write("wait;")
        self.dedent()
        self.writeline()
        self.write("end process %s;" % self.tree.name)
        self.writeline(2)


class _ConvertAlwaysCombVisitor(_ConvertVisitor):

    def __init__(self, tree, blockBuf, funcBuf):
        _ConvertVisitor.__init__(self, tree, blockBuf)
        self.funcBuf = funcBuf

    def visit_FunctionDef(self, node):
        # a local function works nicely too
        def compressSensitivityList(senslist):
            ''' reduce spelled out list items like [*name*(0), *name*(1), ..., *name*(n)] to just *name*'''
            r = []
            for item in senslist:
                name = item._name.split('(',1)[0]
                if not name in r:
                    r.append( name ) # note that the list now contains names and not Signals, but we are interested in the strings anyway ...
            return r

        self.writeDoc(node)
        senslist = compressSensitivityList(self.tree.senslist)
        self.write("%s: process (" % self.tree.name)
        for e in senslist[:-1]:
            self.write(e)
            self.write(', ')
        self.write(senslist[-1])
        self.write(") is")
        self.indent()
        self.writeDeclarations()
        self.dedent()
        self.writeline()
        self.write("begin")
        self.indent()
        self.visit_stmt(node.body)
        self.dedent()
        self.writeline()
        self.write("end process %s;" % self.tree.name)
        self.writeline(2)


class _ConvertSimpleAlwaysCombVisitor(_ConvertVisitor):

    def __init__(self, tree, blockBuf, funcBuf):
        _ConvertVisitor.__init__(self, tree, blockBuf)
        self.funcBuf = funcBuf

    def visit_Attribute(self, node):
        if isinstance(node.ctx, ast.Store):
            self.SigAss = True
            if isinstance(node.value, ast.Name):
                sig = self.tree.symdict[node.value.id]
                self.SigAss = sig._name
            self.visit(node.value)
        else:
            self.getAttr(node)

    def visit_FunctionDef(self, node, *args):
        self.writeDoc(node)
        self.visit_stmt(node.body)
        self.writeline(2)


class _ConvertAlwaysDecoVisitor(_ConvertVisitor):

    def __init__(self, tree, blockBuf, funcBuf):
        _ConvertVisitor.__init__(self, tree, blockBuf)
        self.funcBuf = funcBuf

    def visit_FunctionDef(self, node, *args):
        self.writeDoc(node)
        assert self.tree.senslist
        senslist = self.tree.senslist
        senslist = self.manageEdges(node.body[-1], senslist)
        singleEdge = (len(senslist) == 1) and isinstance(senslist[0], _WaiterList)
        self.write("%s: process (" % self.tree.name)
        if singleEdge:
            self.write(senslist[0].sig)
        else:
            for e in senslist[:-1]:
                self.write(e)
                self.write(', ')
            self.write(senslist[-1])
        self.write(") is")
        self.indent()
        self.writeDeclarations()
        self.dedent()
        self.writeline()
        self.write("begin")
        self.indent()
        if singleEdge:
            self.writeline()
            self.write("if %s then" % senslist[0]._toVHDL())
            self.indent()
        self.visit_stmt(node.body)
        self.dedent()
        if singleEdge:
            self.writeline()
            self.write("end if;")
            self.dedent()
        self.writeline()
        self.write("end process %s;" % self.tree.name)
        self.writeline(2)


def _convertInitVal(reg, init):
    pre, suf = '', ''
    if isinstance(reg, _Signal):
        tipe = inferVhdlObj(reg._init)
        if not reg._numeric:
            pre, suf = 'std_logic_vector(', ')'
    else:
        assert isinstance(reg, (intbv, bitarray))
        tipe = inferVhdlObj(reg)
    if isinstance(tipe, (vhd_boolean, vhd_std_logic)):
        v = "'1'" if init else "'0'"
    elif isinstance(tipe, vhd_unsigned):
        vhd_tipe = tipe.toStr(False)
        if abs(init) < 2**31:
            v = '%sto_%s(%s, %s)%s' % (pre, vhd_tipe, init, tipe.size, suf)
        else:
            v = '%s%s\'("%s")%s' % (pre, vhd_tipe, bin(init, tipe.size), suf)
    elif isinstance(tipe, vhd_signed):
        vhd_tipe = tipe.toStr(False)
        if abs(init) < 2**31:
            v = '%sto_%s(%s, %s)%s' % (pre, vhd_tipe, init, tipe.size, suf)
        else:
            v = '%s%s\'("%s")%s' % (pre, vhd_tipe, bin(init, tipe.size), suf)
    elif isinstance(tipe, vhd_sfixed):
        vhd_tipe = tipe.toStr(False)
        high = tipe.size[0]
        low = tipe.size[1]
        v = '%sc_str2f("%s", %s, %s)%s' % (pre,
                                           bin(init,
                                               tipe.size[0] - tipe.size[1] + 1),
                                               high, low, suf)        
    else:
        assert isinstance(tipe, vhd_enum)
        v = init._toVHDL()
    return v


class _ConvertAlwaysSeqVisitor(_ConvertVisitor):

    def __init__(self, tree, blockBuf, funcBuf):
        _ConvertVisitor.__init__(self, tree, blockBuf)
        self.funcBuf = funcBuf

    def visit_FunctionDef(self, node, *args):
        self.writeDoc(node)
        assert self.tree.senslist
        senslist = self.tree.senslist
        edge = senslist[0]
        reset = self.tree.reset
        async = reset is not None and reset.async
        sigregs = self.tree.sigregs
        varregs = self.tree.varregs
        self.write("%s: process (" % self.tree.name)
        self.write(edge.sig)
        if async:
            self.write(', ')
            self.write(reset)
        self.write(") is")
        self.indent()
        self.writeDeclarations()
        self.dedent()
        self.writeline()
        self.write("begin")
        self.indent()
        if not async:
            self.writeline()
            self.write("if %s then" % edge._toVHDL())
            self.indent()
        if reset is not None:
            self.writeline()
            self.write("if (%s = '%s') then" % (reset, int(reset.active)))
            self.indent()
            for s in sigregs:
                self.writeline()
                self.write("%s <= %s;" % (s, _convertInitVal(s, s._init)))
            for v in varregs:
                n, reg, init = v
                self.writeline()
                self.write("%s := %s;" % (n, _convertInitVal(reg, init)))
            self.dedent()
            self.writeline()
            if async:
                self.write("elsif %s then" % edge._toVHDL())
            else:
                self.write("else")
            self.indent()
        self.visit_stmt(node.body)
        self.dedent()
        if reset is not None:
            self.writeline()
            self.write("end if;")
            self.dedent()
        if not async:
            self.writeline()
            self.write("end if;")
            self.dedent()
        self.writeline()
        self.write("end process %s;" % self.tree.name)
        self.writeline(2)


class _ConvertFunctionVisitor(_ConvertVisitor):

    def __init__(self, tree, funcBuf):
        _ConvertVisitor.__init__(self, tree, funcBuf)
        self.returnObj = tree.returnObj
        self.returnLabel = _Label("RETURN")

    def writeOutputDeclaration(self):
        self.write(self.tree.vhd.toStr(constr=False))

    def writeInputDeclarations(self):
        endchar = ""
        for name in self.tree.argnames:
            self.write(endchar)
            endchar = ";"
            obj = self.tree.symdict[name]
            self.writeline()
            self.writeDeclaration(obj, name, dir="in", constr=False, endchar="")

    def visit_FunctionDef(self, node):
        self.write("function %s(" % self.tree.name)
        self.indent()
        self.writeInputDeclarations()
        self.writeline()
        self.write(") return ")
        self.writeOutputDeclaration()
        self.write(" is")
        self.writeDeclarations()
        self.dedent()
        self.writeline()
        self.write("begin")
        self.indent()
        self.visit_stmt(node.body)
        self.dedent()
        self.writeline()
        self.write("end function %s;" % self.tree.name)
        self.writeline(2)

    def visit_Return(self, node):
        self.write("return ")
        node.value.vhd = self.tree.vhd
        self.visit(node.value)
        self.write(";")


class _ConvertTaskVisitor(_ConvertVisitor):

    def __init__(self, tree, funcBuf):
        _ConvertVisitor.__init__(self, tree, funcBuf)
        self.returnLabel = _Label("RETURN")

    def writeInterfaceDeclarations(self):
        endchar = ""
        for name in self.tree.argnames:
            self.write(endchar)
            endchar = ";"
            obj = self.tree.symdict[name]
            output = name in self.tree.outputs
            input = name in self.tree.inputs
            inout = input and output
            dir = (inout and "inout") or (output and "out") or "in"
            self.writeline()
            self.writeDeclaration(obj, name, dir=dir, constr=False, endchar="")

    def visit_FunctionDef(self, node):
        self.write("procedure %s" % self.tree.name)
        if self.tree.argnames:
            self.write("(")
            self.indent()
            self.writeInterfaceDeclarations()
            self.write(")")
        self.write(" is")
        self.writeDeclarations()
        self.dedent()
        self.writeline()
        self.write("begin")
        self.indent()
        self.visit_stmt(node.body)
        self.dedent()
        self.writeline()
        self.write("end procedure %s;" % self.tree.name)
        self.writeline(2)




# type inference


class vhd_type(object):
    def __init__(self, size=0):
        self.size = size
        self.trunc = False
    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, self.size)
    def maybeNegative(self):
        return False
    def inferBinaryOpCast(node, left, right, op):
        pass
    def _not_implemented(self, other):
        return NotImplemented

class vhd_int(vhd_type):
    def toStr(self, constr=True):
        return "integer"

    def _direct(self, other):
        if isinstance(other, vhd_int):
            return vhd_int(-1)
        else:
            return NotImplemented

    __add__ = __sub__ = __mul__ = __floordiv__ = __mod__ = __pow__ = _direct
    __radd__ = __rsub__ = __rmul__ = __rfloordiv__ = __rmod__ = _direct
    __rpow__ = _direct
    __truediv__ = __rtruediv = vhd_type._not_implemented 
    __and__ = __rand__ = __or__ = __ror__ = vhd_type._not_implemented
    __xor__ = __rxor__ = vhd_type._not_implemented
    
    def __abs__(self):
        return vhd_int()

    def __pos__(self):
        return vhd_int()
    
    def __neg__(self):
        return vhd_int()
    
    def __inv__(self):
        return NotImplemented

    def maybeNegative(self):
        return True

class vhd_nat(vhd_int):
    def toStr(self, constr=True):
        return "natural"

    def _direct(self, other):
        if isinstance(other, vhd_nat):
            return vhd_nat(1)
        else:
            return NotImplemented

    __add__ = __sub__ = __mul__ = __floordiv__ = __mod__ = __pow__ = _direct
    __radd__ = __rsub__ = __rmul__ = __rfloordiv__ = vhd_type._not_implemented
    __rpow__ = vhd_type._not_implemented
    __truediv__ = __rtruediv = __rmod__ = vhd_type._not_implemented 
    __and__ = __rand__ = __or__ = __ror__ = vhd_type._not_implemented
    __xor__ = __rxor__ = vhd_type._not_implemented
    
    def __abs__(self):
        return vhd_nat()

    def __pos__(self):
        return vhd_nat()
    
    def __neg__(self):
        return vhd_int()
    
    def __inv__(self):
        return NotImplemented

    def maybeNegative(self):
        return False

class vhd_real(vhd_type):
    def toStr(self, constr=True):
        return "real"

    def _direct(self, other):
        if isinstance(other, vhd_real):
            return vhd_real(-1)
        else:
            return NotImplemented

    __add__ = __sub__ = __mul__ = __truediv__ = __mod__ = __pow__ = _direct
    __radd__ = __rsub__ = __rmul__ = __rtruediv__ = __rmod__ = _direct
    __rpow__ = _direct
    __floordiv__ = __floordiv = _direct 
    __and__ = __rand__ = __or__ = __ror__ = vhd_type._not_implemented
    __xor__ = __rxor__ = vhd_type._not_implemented
    
    def __abs__(self):
        return vhd_real()

    def __pos__(self):
        return vhd_real()
    
    def __neg__(self):
        return vhd_real()
    
    def __inv__(self):
        return NotImplemented

    def maybeNegative(self):
        return True


class vhd_string(vhd_type):
    pass

class vhd_enum(vhd_type):
    def __init__(self, tipe):
        self._type = tipe

    def toStr(self, constr = True):
        return self._type.__dict__['_name']


class vhd_std_logic(vhd_type):
    def __init__(self, size=0):
        vhd_type.__init__(self)
        self.size = 1
    def toStr(self, constr=True):
        return 'std_logic'

    def _logical(self, other):
        if isinstance(other, (vhd_std_logic, vhd_boolean)):
            return vhd_std_logic()
        else:
            return NotImplemented

    __add__ = __sub__ = __mul__ = __floordiv__ = __truediv__ = vhd_type._not_implemented
    __mod__ = vhd_type._not_implemented
    __radd__ = __rsub__ = __rmul__ = __rfloordiv__ = vhd_type._not_implemented
    __rtruediv__ = __rmod__ = vhd_type._not_implemented
    __and__ = __rand__ = __or__ = __ror__ = _logical
    __xor__ = __rxor__ = _logical
    
    def __abs__(self):
        return NotImplemented

    def __pos__(self):
        return NotImplemented
    
    def __neg__(self):
        return NotImplemented
    
    def __inv__(self):
        return self


class vhd_boolean(vhd_type):
    def __init__(self, size=0):
        vhd_type.__init__(self)
        self.size = 1
    def toStr(self, constr=True):
        return 'boolean'

    def _logical(self, other):
        if isinstance(other, vhd_boolean):
            return vhd_boolean()
        else:
            return NotImplemented

    __add__ = __sub__ = __mul__ = __floordiv__ = __truediv__ = vhd_type._not_implemented
    __mod__ = vhd_type._not_implemented
    __radd__ = __rsub__ = __rmul__ = __rfloordiv__ = vhd_type._not_implemented
    __rtruediv__ = __rmod__ = vhd_type._not_implemented
    __and__ = __rand__ = __or__ = __ror__ = _logical
    __xor__ = __rxor__ = _logical
    
    def __abs__(self):
        return NotImplemented

    def __pos__(self):
        return NotImplemented
    
    def __neg__(self):
        return NotImplemented
    
    def __inv__(self):
        return self


class vhd_vector(vhd_type):
    def __init__(self, size=0, lenStr=False):
        vhd_type.__init__(self, size)
        self.lenStr = lenStr

    def _logical(self, other):
        if isinstance(other, vhd_int):
            result = copy(self)
        elif isinstance(other, vhd_vector):
            high = max(other.size, self.size)
            result = type(self)(high)
        else:
            return NotImplemented
        self.trunc = True
        other.trunc = True
        result.trunc = True
        return result

    __add__ = __sub__ = __mul__ = __floordiv__ = vhd_type._not_implemented
    __truediv__ = __mod__ = vhd_type._not_implemented
    __radd__ = __rsub__ = __rmul__ = __rfloordiv__ = vhd_type._not_implemented
    __rtruediv__ = __rmod__ = vhd_type._not_implemented
    __and__ = __or__ = __xor__ = _logical
    __rand__ = __ror__ = __rxor__ = vhd_type._not_implemented
    
    def __abs__(self):
        return NotImplemented

    def __pos__(self):
        return NotImplemented
    
    def __neg__(self):
        return NotImplemented
    
    def __inv__(self):
        return self

    @staticmethod
    def inferBinaryOpCast(node, left, right, op):
        ns, os = node.vhd.size, node.vhdOri.size
        if type(ns) is tuple:
            ns = ns[0] + 1
        ds = ns - os
        if ds > 0:
            if isinstance(left.vhd, vhd_vector) and \
                    isinstance(right.vhd, vhd_vector):
                if isinstance(op, (ast.Add, ast.Sub)):
                    left.vhd.size = ns
                    # in general, resize right also
                    # for a simple name, resizing is not necessary
                    if not isinstance(right, ast.Name):
                        right.vhd.size = ns
                    node.vhdOri.size = ns
                elif isinstance(op, ast.Mod):
                    right.vhd.size = ns
                    node.vhdOri.size = ns
                elif isinstance(op, ast.FloorDiv):
                    left.vhd.size = ns
                    node.vhdOri.size = ns
                elif isinstance(op, ast.Mult):
                    left.vhd.size += ds
                    node.vhdOri.size = ns
                else:
                    raise ToVHDLError(_error.NotSupported,
                                      "unexpected op %s" % op)
            elif isinstance(left.vhd, vhd_vector) and \
                    isinstance(right.vhd, vhd_int):
                if isinstance(op, (ast.Add, ast.Sub, ast.Mod, ast.FloorDiv)):
                    left.vhd.size = ns
                    node.vhdOri.size = ns
                elif isinstance(op, ast.Mult):
                    left.vhd.size += ds
                    node.vhdOri.size = 2 * left.vhd.size
                else:
                    raise ToVHDLError(_error.NotSupported,
                                      "unexpected op %s" % op)
            elif isinstance(left.vhd, vhd_int) and\
                    isinstance(right.vhd, vhd_vector):
                if isinstance(op, (ast.Add, ast.Sub, ast.Mod, ast.FloorDiv)):
                    right.vhd.size = ns
                    node.vhdOri.size = ns
                elif isinstance(op, ast.Mult):
                    node.vhdOri.size = 2 * right.vhd.size
                else:
                    raise ToVHDLError(_error.NotSupported,
                                      "unexpected op %s" % op)

    @staticmethod
    def inferShiftOpCast(node, left, right, op):
        ns, os = node.vhd.size, node.vhdOri.size
        ds = ns - os
        if ds > 0:
            left.vhd.size = ns
            node.vhdOri.size = ns

                
class vhd_unsigned(vhd_vector):
    def toStr(self, constr=True):
        if constr:
            ls = self.lenStr
            if ls:
                return "unsigned(%s downto 0)" % (ls - 1)
            else:
                return "unsigned(%s downto 0)" % (self.size - 1)
        else:
            return "unsigned"
        
    def __add__(self, other):
        if isinstance(other, vhd_nat):
            return copy(self)
        elif isinstance(other, vhd_int):
            return vhd_signed(self.size)
        elif isinstance(other, vhd_unsigned):
            return vhd_unsigned(max(self.size, other.size))
        else:
            return NotImplemented

    def __radd__(self, other):
        if isinstance(other, vhd_nat):
            return copy(self)
        elif isinstance(other, vhd_int):
            return vhd_signed(self.size)
        else:
            return NotImplemented

    def __sub__(self, other):
        if isinstance(other, vhd_nat):
            return copy(self)
        elif isinstance(other, vhd_int):
            return vhd_signed(self.size)
        elif isinstance(other, vhd_unsigned):
            return vhd_unsigned(max(self.size, other.size))
        else:
            return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, vhd_nat):
            return copy(self)
        elif isinstance(other, vhd_int):
            return vhd_signed(self.size)
        else:
            return NotImplemented

    def __mul__(self, other):
        if isinstance(other, vhd_nat):
            return vhd_unsigned(2*self.size)
        elif isinstance(other, vhd_int):
            return vhd_signed(2*self.size)
        elif isinstance(other, vhd_unsigned):
            return vhd_unsigned(self.size + other.size)
        else:
            return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, vhd_nat):
            return vhd_unsigned(2*self.size)
        elif isinstance(other, vhd_int):
            return vhd_signed(2*self.size)
        else:
            return NotImplemented

    def __floordiv__(self, other):
        if isinstance(other, vhd_nat):
            return copy(self)
        elif isinstance(other, vhd_int):
            return vhd_signed(self.size)
        elif isinstance(other, vhd_unsigned):
            return copy(self)
        else:
            return NotImplemented

    def __rfloordiv__(self, other):
        if isinstance(other, vhd_nat):
            return copy(self)
        elif isinstance(other, vhd_int):
            return vhd_signed(self.size)
        else:
            return NotImplemented

    __truediv__ = __rtruediv__ = vhd_type._not_implemented

    def __mod__(self, other):
        if isinstance(other, vhd_nat):
            return copy(self)
        elif isinstance(other, vhd_int):
            return vhd_signed(self.size)
        elif isinstance(other, vhd_unsigned):
            return copy(other)
        else:
            return NotImplemented

    def __rmod__(self, other):
        if isinstance(other, vhd_nat):
            return copy(self)
        elif isinstance(other, vhd_int):
            return vhd_signed(self.size)
        else:
            return NotImplemented

    def __abs__(self):
        return NotImplemented

    def __pos__(self):
        return copy(self)
    
    def __neg__(self):
        return NotImplemented
    

class vhd_signed(vhd_vector):
    def toStr(self, constr=True):
        if constr:
            ls = self.lenStr
            if ls:
                return "signed(%s downto 0)" % (ls - 1)
            else:
                return "signed(%s downto 0)" % (self.size - 1)
        else:
            return "signed"

    def __add__(self, other):
        if isinstance(other, vhd_int):
            return copy(self)
        elif isinstance(other, vhd_signed):
            return vhd_signed(max(self.size, other.size))
        else:
            return NotImplemented

    def __radd__(self, other):
        if isinstance(other, vhd_int):
            return copy(self)
        else:
            return NotImplemented

    def __sub__(self, other):
        if isinstance(other, vhd_int):
            return copy(self)
        elif isinstance(other, vhd_signed):
            return vhd_signed(max(self.size, other.size))
        else:
            return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, vhd_int):
            return copy(self)
        else:
            return NotImplemented

    def __mul__(self, other):
        if isinstance(other, vhd_int):
            return vhd_signed(2*self.size)
        elif isinstance(other, vhd_signed):
            return vhd_signed(self.size + other.size)
        else:
            return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, vhd_int):
            return vhd_signed(2*self.size)
        else:
            return NotImplemented

    def __floordiv__(self, other):
        if isinstance(other, vhd_int):
            return copy(self)
        elif isinstance(other, vhd_signed):
            return copy(self)
        else:
            return NotImplemented

    def __rfloordiv__(self, other):
        if isinstance(other, vhd_int):
            return copy(self)
        else:
            return NotImplemented

    __truediv__ = __rtruediv__ = vhd_type._not_implemented

    def __mod__(self, other):
        if isinstance(other, vhd_int):
            return copy(self)
        elif isinstance(other, vhd_signed):
            return copy(other)
        else:
            return NotImplemented

    def __rmod__(self, other):
        if isinstance(other, vhd_int):
            return copy(self)
        else:
            return NotImplemented

    def __abs__(self):
        return copy(self)

    def __pos__(self):
        return copy(self)
    
    def __neg__(self):
        return copy(self)

    def maybeNegative(self):
        return True


class vhd_sfixed(vhd_type):
    def __init__(self, size=(0, 0), lenStr=False):
        vhd_type.__init__(self, size)
        self.lenStr = lenStr

    def toStr(self, constr=True):
        if constr:
            ls = self.lenStr
            if ls:
                return "sfixed(%s downto %s)" % (ls[0], ls[1])
            else:
                return "sfixed(%s downto %s)" % (self.size[0],
                                                 self.size[1])
        else:
            return "sfixed"

    def __add__(self, other):
        if isinstance(other, (vhd_int, vhd_real)):
            return vhd_sfixed((self.size[0] + 1, self.size[1]))
        elif isinstance(other, vhd_vector):
            return vhd_sfixed((max(self.size[0], other.size - 1) + 1,
                               self.size[1]))
        elif isinstance(other, vhd_sfixed):
            return vhd_sfixed((max(self.size[0], other.size[0]) + 1,
                              min(self.size[1], other.size[1])))
        else:
            return NotImplemented

    __radd__ = __add__

    def __sub__(self, other):
        if isinstance(other, (vhd_int, vhd_real)):
            return vhd_sfixed((self.size[0] + 1, self.size[1]))
        elif isinstance(other, vhd_vector):
            return vhd_sfixed((max(self.size[0], other.size - 1) + 1,
                               self.size[1]))
        elif isinstance(other, vhd_sfixed):
            return vhd_sfixed((max(self.size[0], other.size[0]) + 1,
                               min(self.size[1], other.size[1])))
        else:
            return NotImplemented

    __rsub__ = __sub__

    def __mul__(self, other):
        if isinstance(other, (vhd_int, vhd_real)):
            return vhd_sfixed((2 * self.size[0] + 1, 2 * self.size[1]))
        elif isinstance(other, vhd_vector):
            return vhd_sfixed((self.size[0] + other.size - 1, self.size[1]))
        elif isinstance(other, vhd_sfixed):
            return vhd_sfixed((self.size[0] + other.size[0] + 1,
                               self.size[1] + other.size[1]))
        else:
            return NotImplemented

    __rmul__ = __mul__

    def __floordiv__(self, other):
        if isinstance(other, (vhd_int, vhd_real)):
            return vhd_sfixed((self.size[0] - self.size[1] + 1,
                               self.size[1] - self.size[0]))
        elif isinstance(other, vhd_vector):
            return vhd_sfixed((self.size[0] + 1,
                               self.size[1] - other.size + 1))
        elif isinstance(other, vhd_sfixed):
            return vhd_sfixed((self.size[0] - other.size[1] + 1,
                               self.size[1] - other.size[0]))
        else:
            return NotImplemented

    __rfloordiv__ = __floordiv__

    def __truediv__(self, other):
        if isinstance(other, (vhd_int, vhd_real)):
            return vhd_sfixed((self.size[0] + 1,
                               self.size[1] - self.size[0]))
        elif isinstance(other, vhd_vector):
            return vhd_sfixed((self.size[0] + 1,
                               self.size[1] - other.size + 1))
        elif isinstance(other, vhd_sfixed):
            return vhd_sfixed((self.size[0] - other.size[1] + 1,
                               self.size[1] - other.size[0]))
        else:
            return NotImplemented

    __rtruediv__ = __truediv__

    def __mod__(self, other):
        if isinstance(other, (vhd_int, vhd_real)):
            return vhd_sfixed((self.size[0], min(self.size[1], 0)))
        elif isinstance(other, vhd_vector):
            return vhd_sfixed((other.size - 1,
                               min(self.size[1], 0)))
        elif isinstance(other, vhd_sfixed):
            return vhd_sfixed((other.size[0],
                               min(self.size[1], other.size[1])))
        else:
            return NotImplemented

    __rmod__ = __mod__

    def _logical(self, other):
        high = None
        low = None
        if isinstance(other, vhd_unsigned):
            high = max(other.size, self.size[0])
            low = min(0, self.size[1])
        elif isinstance(other, vhd_signed):
            high = max(other.size - 1, self.size[0])
            low = min(0, self.size[1])
        elif isinstance(other, vhd_sfixed):
            high = max(other.size[0], self.size[0])
            low = min(other.size[1], self.size[1])
        else:
            return NotImplemented
        result = vhd_sfixed((high, low))
        self.trunc = True
        other.trunc = True
        result.trunc = True
        return result

    __and__ = __or__ = __xor__ = _logical
    __rand__ = __ror__ = __rxor__ = _logical
    
    def __abs__(self):
        return vhd_sfixed((self.size[0] + 1, self.size[1]))

    def __pos__(self):
        return self
    
    def __neg__(self):
        return vhd_sfixed((self.size[0] + 1, self.size[1]))
    
    def __inv__(self):
        return copy(self)

    def maybeNegative(self):
        return True

    @staticmethod
    def inferBinaryOpCast(node, left, right, op):
        ns_low = os_low = 0
        ns_high, os_high = node.vhd.size, node.vhdOri.size
        if type(ns_high) is tuple:
            ns_low = ns_high[1]
            ns_high = ns_high[0]
        if type(os_high) is tuple:
            os_low = os_high[1]
            os_high = os_high[0]
        ds_high = ns_high - os_high
        ds_low = ns_low - os_low
        if ds_high <= 0:
            ds_high = 0
            ns_high = os_high
        if ds_low >= 0:
            ds_low = 0
            ns_low = os_low
        if isinstance(left.vhd, vhd_sfixed):
            if isinstance(right.vhd, vhd_sfixed):
                pass
            elif isinstance(right.vhd, (vhd_int, vhd_real)):
                if isinstance(op, (ast.Add, ast.Sub)):
                    left.vhd.size = (ns_high - 1, ns_low)
                elif isinstancd(op, (ast.Mod, ast.FloorDiv, ast.Div)):
                    left.vhd.size = (ns_high, ns_low)
                elif isinstance(op, ast.Mult):
                    left.vhd.size = (left.vhd.size[0] + ds_high,
                                     left.vhd.size[1] + ds_low)
                else:
                    raise ToVHDLError(_error.NotSupported,
                                      "unexpected op %s" % op)
            else:
                raise AssertionError("unexpected operand %s" % right.vhd)
        elif isinstance(right.vhd, vhd_sfixed):
            if isinstance(left.vhd, (vhd_int, vhd_real)):
                if isinstance(op, (ast.Add, ast.Sub)):
                    right.vhd.size = (ns_high - 1, ns_low)
                elif isinstance(op, (ast.Mod, ast.FloorDiv, ast.Div)):
                    right.vhd.size = (ns_high, ns_low)
                elif isinstance(op, ast.Mult):
                    right.vhd.size = (right.vhd.size[0] + ds_high,
                                      right.vhd.size[1] + ds_low)
                else:
                    raise ToVHDLError(_error.NotSupported,
                                      "unexpected op %s" % op)
            else:
                raise ToVHDLError(_error.NotSupported,
                                  "unexpected operand %s for %s" % \
                                  (op, left.vhd))
        if isinstance(op, ast.Add):
            node.vhdOri = left.vhd + right.vhd
        elif isinstance(op, ast.Sub):
            node.vhdOri = left.vhd - right.vhd
        elif isinstance(op, ast.Mult):
            node.vhdOri = left.vhd * right.vhd
        elif isinstance(op, ast.FloorDiv):
            node.vhdOri = left.vhd // right.vhd
        elif isinstance(op, ast.Div):
            node.vhdOri = left.vhd / right.vhd
        elif isinstance(op, ast.Mod):
            node.vhdOri = left.vhd % right.vhd
        elif isinstance(op, ast.Pow):
            node.vhdOri = left.vhd ** right.vhd
        else:
            raise ToVHDLError(_error.NotSupported, "Unknown op %s" % op)

    @staticmethod
    def inferShiftOpCast(node, left, right, op):
        ns, os = node.vhd.size, node.vhdOri.size
        ds_high = ns[0] - os[0]
        ds_low = ns[1] - os[1]
        if ds_high > 0:
            left_high = ns[0]
        else:
            left_high = left.vhd.size[0]
        if ds_low < 0:
            left_low = ns[1]
        else:
            left_low = left.vhd.size[1]
        left.vhd.size = (left_high, left_low)
        node.vhdOri.size = (left_high, left_low)

class _loopInt(int):
    pass

def inferVhdlClass(obj):
    vhd = None
    if (isinstance(obj, _Signal) and obj._type is intbv) or \
            isinstance(obj, intbv):
        if obj.min is None or obj.min < 0:
            vhd = vhd_signed
        else:
            vhd = vhd_unsigned
    elif (isinstance(obj, _Signal) and obj._type is bitarray) or \
            isinstance(obj, bitarray):
        if isinstance(obj, _Signal):
            obj = obj._init
        if isinstance(obj, uintba):
            vhd = vhd_unsigned
        elif isinstance(obj, sintba):
            vhd = vhd_signed
        elif isinstance(obj, sfixba):
            vhd = vhd_sfixed
        else:
            raise ToVHDLError(_error.NotSupported, "Not valid bitarray child.")
    elif (isinstance(obj, _Signal) and obj._type is bool) or \
            isinstance(obj, bool):
        vhd = vhd_std_logic
    elif (isinstance(obj, _Signal) and isinstance(obj._init, EnumItemType)) or\
            isinstance(obj, EnumItemType):
        vhd = vhd_enum
    elif isinstance(obj, integer_types):
        if obj >= 0:
            vhd = vhd_nat
        else:
            vhd = vhd_int
    elif isinstance(obj, float):
        vhd = vhd_real
    return vhd

def inferVhdlObj(obj):
    vhd = inferVhdlClass(obj)
    if vhd is None:
        return vhd
    elif issubclass(vhd, (vhd_unsigned, vhd_signed)):
        ls = getattr(obj, 'lenStr', False)
        vhd = vhd(size=len(obj), lenStr=ls)
    elif issubclass(vhd, vhd_sfixed):
        ls = getattr(obj, 'lenStr', False)
        high = getattr(obj, 'high', False)
        low = getattr(obj, 'low', False)
        # vhd_sfixed represents the vhdl element, so the sizes are
        # represented in the same format.
        vhd = vhd_sfixed(size=(high - 1, low), lenStr=ls)
    elif issubclass(vhd, vhd_std_logic):
        vhd = vhd()
    elif issubclass(vhd, vhd_enum):
        if isinstance(obj, _Signal):
            tipe = obj._val._type
        else:
            tipe = obj._type
        vhd = vhd(tipe)
    elif issubclass(vhd, (vhd_int, vhd_real)):
        vhd = vhd()
    return vhd

def maybeNegative(vhd):
    return vhd.maybeNegative()

class _AnnotateTypesVisitor(ast.NodeVisitor, _ConversionMixin):

    def __init__(self, tree):
        self.tree = tree

    def visit_FunctionDef(self, node):
        # don't visit arguments and decorators
        for stmt in node.body:
            self.visit(stmt)

    def visit_Attribute(self, node):
        self.generic_visit(node)
        if node.attr in ('max', 'min', 'high', 'low'):
            node.vhd = vhd_int(-1)
        elif node.attr in ('is_signed'):
            node.vhd = vhd_boolean()
        else:
            node.vhd = copy(node.value.vhd)
        node.vhdOri = copy(node.vhd)

    def visit_Assert(self, node):
        self.visit(node.test)
        node.test.vhd = vhd_boolean()

    def visit_AugAssign(self, node):
        self.visit(node.target)
        self.visit(node.value)
        node.left, node.right = node.target, node.value
        if isinstance(node.op, (ast.BitOr, ast.BitAnd, ast.BitXor)):
            self.inferBitOpType(node)
        elif isinstance(node.op, (ast.RShift, ast.LShift)):
            self.inferShiftType(node)
        else:
            self.inferBinOpType(node)
        node.vhd = copy(node.target.vhdOri)

    def visit_Call(self, node):
        fn = node.func
        # assert isinstance(fn, astNode.Name)
        f = self.getObj(fn)
        node.vhd = inferVhdlObj(node.obj)
        self.generic_visit(node)
        if f is concat:
            s = 0
            for a in node.args:
                if isinstance(a, ast.Str):
                    a.vhd = vhd_unsigned(a.vhd.size)
                elif isinstance(a.vhd, vhd_signed):
                    a.vhd = vhd_unsigned(a.vhd.size) 
                elif isinstance(a.vhd, vhd_sfixed):
                    a.vhd = vhd_unsigned(a.vhd.size[0] - a.vhd.size[1] + 1) 
                s += a.vhd.size
            node.vhd = vhd_unsigned(s)
        elif f is bool:
            node.vhd = vhd_boolean()
        elif f in _flatten(integer_types, ord):
            node.vhd = vhd_int()
            node.args[0].vhd = vhd_int()
        elif f is float:
            node.vhd = vhd_real()
            node.args[0].vhd = vhd_real()
        elif f in (intbv, modbv):
            node.vhd = vhd_int()
        elif f in numeric_types:
            node.vhd = inferVhdlObj(node.obj)
            if isinstance(node.vhd, vhd_sfixed):
                self.tree.hasFixedPoint = True
        elif f is len:
            node.vhd = vhd_int()
        elif f is now:
            node.vhd = vhd_nat()
        elif f == intbv.signed: # note equality comparison
            # this comes from a getattr
            node.vhd = vhd_signed(fn.value.vhd.size)
        elif hasattr(node, 'tree'):
            v = _AnnotateTypesVisitor(node.tree)
            v.visit(node.tree)
            node.vhd = node.tree.vhd = inferVhdlObj(node.tree.returnObj)
        node.vhdOri = copy(node.vhd)

    def visit_Compare(self, node):
        node.vhd = vhd_boolean()
        self.generic_visit(node)
        left, op, right = node.left, node.ops[0], node.comparators[0]
        if isinstance(left.vhd, vhd_sfixed):
            if isinstance(right.vhd, vhd_signed):
                right.vhd = vhd_sfixed((right.vhd.size - 1, 0))
            elif isinstance(right.vhd, vhd_unsigned):
                right.vhd = vhd_sfixed((right.vhd.size, 0))
            elif isinstance(right.vhd, vhd_nat):
                right.vhd = vhd_int(1)
        elif isinstance(right.vhd, vhd_sfixed):
            if isinstance(left.vhd, vhd_signed):
                left.vhd = vhd_sfixed((left.vhd.size - 1, 0))
            elif isinstance(left.vhd, vhd_unsigned):
                left.vhd = vhd_sfixed((left.vhd.size, 0))
            elif isinstance(left.vhd, vhd_nat):
                left.vhd = vhd_int(1)
        elif isinstance(left.vhd, vhd_std_logic) or isinstance(right.vhd, vhd_std_logic):
            left.vhd = right.vhd = vhd_std_logic()
        elif isinstance(left.vhd, vhd_unsigned) and maybeNegative(right.vhd):
            left.vhd = vhd_signed(left.vhd.size + 1)
        elif maybeNegative(left.vhd) and isinstance(right.vhd, vhd_unsigned):
            right.vhd = vhd_signed(right.vhd.size + 1)
        node.vhdOri = copy(node.vhd)

    def visit_Str(self, node):
        node.vhd = vhd_string()
        node.vhdOri = copy(node.vhd)

    def visit_Num(self, node):
        if node.n is float:
            node.vhd = vhd_real()
        else:
            if node.n < 0:
                node.vhd = vhd_int()
            else:
                node.vhd = vhd_nat()
        node.vhdOri = copy(node.vhd)

    def visit_For(self, node):
        var = node.target.id
        # make it possible to detect loop variable
        self.tree.vardict[var] = _loopInt(-1)
        self.generic_visit(node)

    def visit_NameConstant(self, node):
        node.vhd = inferVhdlObj(node.value)
        node.vhdOri = copy(node.vhd)

    def visit_Name(self, node):
        if node.id in self.tree.vardict:
            node.obj = self.tree.vardict[node.id]
        node.vhd = inferVhdlObj(node.obj)
        node.vhdOri = copy(node.vhd)

    def visit_NameConstant(self, node):
        node.vhd = inferVhdlObj(node.value)
        node.vhdOri = copy(node.vhd)

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, (ast.LShift, ast.RShift)):
            self.inferShiftType(node)
        elif isinstance(node.op, (ast.BitAnd, ast.BitOr, ast.BitXor)):
            self.inferBitOpType(node)
        elif isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Str): # format string
            pass
        else:
            self.inferBinOpType(node)

    def inferShiftType(self, node):
        node.left.vhd.trunc = True
        node.vhd = copy(node.left.vhd)
        node.right.vhd = vhd_nat()
        node.vhdOri = copy(node.vhd)

    def inferBitOpType(self, node):
        left = node.left.vhd
        right = node.right.vhd
        if isinstance(node.op, ast.BitAnd):
            obj = left & right
        elif isinstance(node.op, ast.BitOr):
            obj = left | right
        elif isinstance(node.op, ast.BitXor):
            obj = left ^ right
        node.vhd = node.left.vhd = node.right.vhd = obj
        node.vhdOri = copy(node.vhd)

    def inferBinOpType(self, node):
        left, op, right = node.left, node.op, node.right
        if isinstance(left.vhd, (vhd_boolean, vhd_std_logic)):
                left.vhd = vhd_unsigned(1)
        if isinstance(right.vhd, (vhd_boolean, vhd_std_logic)):
                right.vhd = vhd_unsigned(1)
        if isinstance(left.vhd, vhd_sfixed):
            if isinstance(right.vhd, vhd_nat):
                right.vhd = vhd_int(-1)
            elif isinstance(right.vhd, vhd_unsigned):
                right.vhd = vhd_sfixed((right.vhd.size, 0))
            elif isinstance(right.vhd, vhd_signed):
                right.vhd = vhd_sfixed((right.vhd.size - 1, 0))
        elif isinstance(right.vhd, vhd_sfixed):
            if isinstance(left.vhd, vhd_nat):
                left.vhd = vhd_int(-1)
            elif isinstance(left.vhd, vhd_unsigned):
                left.vhd = vhd_sfixed((left.vhd.size, 0))
            elif isinstance(left.vhd, vhd_signed):
                left.vhd = vhd_sfixed((left.vhd.size - 1, 0))
        elif isinstance(left.vhd, vhd_signed):
            if isinstance(right.vhd, vhd_unsigned):
                right.vhd = vhd_signed(right.vhd.size + 1)
        elif isinstance(right.vhd, vhd_signed):
            if isinstance(left.vhd, vhd_unsigned):
                left.vhd = vhd_signed(left.vhd.size + 1)
        elif isinstance(left.vhd, vhd_unsigned):
            if isinstance(right.vhd, vhd_nat):
                if isinstance(op, ast.Sub):
                    left.vhd = vhd_signed(left.vhd.size + 1)
            elif isinstance(right.vhd, vhd_int):
                left.vhd = vhd_signed(left.vhd.size + 1)
        elif isinstance(right.vhd, vhd_unsigned):
            if isinstance(right.vhd, vhd_nat):
                pass
            elif isinstance(right.vhd, vhd_int):
                right.vhd = vhd_signed(right.vhd.size + 1)
        elif isinstance(left.vhd, vhd_real):
            if isinstance(right.vhd, vhd_int):
                right.vhd = vhd_real(-1)
        elif isinstance(right.vhd, vhd_real):
            if isinstance(left.vhd, vhd_int):
                left.vhd = vhd_real(-1)

        if isinstance(op, ast.Add):
            node.vhd = left.vhd + right.vhd
        elif isinstance(op, ast.Sub):
            node.vhd = left.vhd - right.vhd
        elif isinstance(op, ast.Mult):
            node.vhd = left.vhd * right.vhd
        elif isinstance(op, ast.FloorDiv):
            node.vhd = left.vhd // right.vhd
        elif isinstance(op, ast.Div):
            node.vhd = left.vhd / right.vhd
        elif isinstance(op, ast.Mod):
            node.vhd = left.vhd % right.vhd
        elif isinstance(op, ast.Pow):
            node.vhd = left.vhd ** right.vhd
        else:
            raise ToVHDLError(_error.NotSupported, "Unknown op %s" % op)

        node.vhdOri = copy(node.vhd)

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        for n in node.values:
            n.vhd = vhd_boolean()
        node.vhd = vhd_boolean()
        node.vhdOri = copy(node.vhd)

    def visit_If(self, node):
        if node.ignore:
            return
        self.generic_visit(node)
        for test, suite in node.tests:
            test.vhd = vhd_boolean()

    def visit_IfExp(self, node):
        self.generic_visit(node)
        node.test.vhd = vhd_boolean()

    def visit_ListComp(self, node):
        pass # do nothing

    def visit_Subscript(self, node):
        if isinstance(node.slice, ast.Slice):
            self.accessSlice(node)
        else:
            self.accessIndex(node)

    def accessSlice(self, node):
        self.generic_visit(node)
        lower = node.value.vhd.size
        if isinstance(lower, tuple):
            upper = lower[1]
            lower = lower[0] + 1
        else:
            upper = 0
        t = type(node.value.vhd)
        # node.expr.vhd = vhd_unsigned(node.expr.vhd.size)
        if node.slice.lower:
            node.slice.lower.vhd = vhd_int()
            lower = self.getVal(node.slice.lower)
        if node.slice.upper:
            node.slice.upper.vhd = vhd_int()
            upper = self.getVal(node.slice.upper)
        if isinstance(node.ctx, ast.Store):
            if issubclass(t, vhd_sfixed):
                node.vhd = t((lower - upper - 1, 0))
            else:
                node.vhd = t(lower - upper)
        else:
            node.vhd = vhd_unsigned(lower-upper)
        node.vhdOri = copy(node.vhd)

    def accessIndex(self, node):
        self.generic_visit(node)
        node.vhd = vhd_std_logic() # XXX default
        node.slice.value.vhd = vhd_int()
        obj = node.value.obj
        if isinstance(obj, list):
            assert len(obj)
            node.vhd = inferVhdlObj(obj[0])
        elif isinstance(obj, _Ram):
            node.vhd = inferVhdlObj(obj.elObj)
        elif isinstance(obj, _Rom):
            node.vhd = vhd_int()
        elif isinstance(obj, (intbv, bitarray)):
            node.vhd = vhd_std_logic()
        node.vhdOri = copy(node.vhd)

    def visit_UnaryOp(self, node):
        self.visit(node.operand)
        node.vhd = copy(node.operand.vhd)
        if isinstance(node.op, ast.Not):
            # postpone this optimization until initial values are written
#            if isinstance(node.operand.vhd, vhd_std_logic):
#                node.vhd = vhd_std_logic()
#            else:
#                node.vhd = node.operand.vhd = vhd_boolean()
            node.vhd = node.operand.vhd = vhd_boolean()
        elif isinstance(node.op, ast.USub):
            if isinstance(node.vhd, vhd_unsigned):
                node.vhd = vhd_signed(node.vhd.size+1)
            elif isinstance(node.vhd, vhd_nat):
                node.vhd = vhd_int()
        elif isinstance(node.op, ast.Invert):
            if isinstance(node.vhd, (vhd_int, vhd_real)):
                raise ToVHDLError(_error.NotSupported,
                                  "Cannot invert natural or " \
                                  "integer values")
        node.vhdOri = copy(node.vhd)

    def visit_While(self, node):
        self.generic_visit(node)
        node.test.vhd = vhd_boolean()


def _annotateTypes(genlist):
    for tree in genlist:
        if isinstance(tree, _UserVhdlCode):
            continue
        v = _AnnotateTypesVisitor(tree)
        v.visit(tree)







