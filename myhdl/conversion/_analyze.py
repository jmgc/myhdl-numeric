#  This file is part of the myhdl library, a Python package for using
#  Python as a Hardware Description Language.
#
#  Copyright (C) 2003-2013 Jan Decaluwe
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

""" MyHDL conversion analysis module.

"""
from __future__ import absolute_import, print_function, division

import inspect
import sys
# import compiler
# from compiler import ast as astNode
from types import FunctionType, MethodType
import re
import ast

import myhdl
from .._intbv import intbv
from .._enum import EnumType, EnumItemType
from .._modbv import modbv
from .._concat import concat
from .._delay import delay
from .._misc import downrange
from .._errors import ConversionError
from .._always_comb import _AlwaysComb
from .._always_seq import _AlwaysSeq
from .._always import _Always
from ..conversion._misc import _error, _access, _kind, \
    _ConversionMixin, _Label, _genUniqueSuffix, _get_argnames
from .._extractHierarchy import _isMem, _getMemInfo, _UserCode
from .._Signal import _Signal, _WaiterList
from .._ShadowSignal import _ShadowSignal, _SliceSignal, _TristateDriver
from .._util import _isTupleOfInts, _flatten, _makeAST, _isTupleOfFloats
from .._resolverefs import _AttrRefTransformer
from .._compat import builtins, integer_types, long, string_types, PY2
from ..numeric._conversion import numeric_functions_dict, \
    numeric_attributes_dict
from ..numeric._bitarray import bitarray


_enumTypeSet = set()


def _makeName(n, prefixes, case=None):
    # trim empty prefixes
    prefixes = [p for p in prefixes if p]
    if len(prefixes) > 1:
        # name = '_' + '_'.join(prefixes[1:]) + '_' + n
        name = '_'.join(prefixes[1:]) + '_' + n
    else:
        name = n
    if '[' in name or ']' in name:
        name = "\\" + name + ' '
        # print prefixes
        # print name
    if case == 'lower':
        return name.lower()
    elif case == 'upper':
        return name.upper()
    else:
        return name


def _analyzeSigs(hierarchy, hdl='Verilog', initlevel=0):
    curlevel = initlevel
    siglist = []
    memlist = []
    prefixes = []

    for inst in hierarchy:
        level = inst.level
        name = inst.name
        sigdict = inst.sigdict
        memdict = inst.memdict
        delta = curlevel - level
        curlevel = level
        assert(delta >= -1)
        if delta > -1:  # same or higher level
            prefixes = prefixes[:curlevel-1]
        # skip processing and prefixing in context without signals
        if not (sigdict or memdict):
            prefixes.append("")
            continue
        prefixes.append(name)
        for n, s in sigdict.items():
            if s._name is not None:
                continue
            if isinstance(s, _SliceSignal):
                continue
            s._name = _makeName(n, prefixes)
            if not s._nrbits:
                raise ConversionError(_error.UndefinedBitWidth, s._name)
            # slice signals
            for sl in s._slicesigs:
                sl._setName(hdl)
            siglist.append(s)
        # list of signals
        for n, m in memdict.items():
            if m.name is not None:
                continue
            m.name = _makeName(n, prefixes)
            memlist.append(m)

    if hdl != "VHDL":
        _analyzeMems(memlist, hdl)

    return siglist, memlist


def _analyzeMems(memlist, hdl):
    open_sym, close_sym = '[', ']'
    if hdl == 'VHDL':
        open_sym, close_sym = '(', ')'

    # handle the case where a named signal appears in a list also by giving
    # priority to the list and marking the signals as unused
    for m in memlist:
        if not m._used:
            continue
        for s in m.mem:
            s._inList = None

    for m in memlist:
        if not m._used:
            continue

        for i, s in enumerate(m.mem):
            s._name = "%s%s%s%s" % (m.name, open_sym, i, close_sym)
            s._used = False
            if s._inList is not None:
                raise ConversionError(_error.SignalInMultipleLists, s._name)
            s._inList = m
            if not s._nrbits:
                raise ConversionError(_error.UndefinedBitWidth, s._name)
            if not isinstance(s.val, type(m.elObj.val)):
                raise ConversionError(_error.InconsistentType, s._name)
            if s._nrbits != m.elObj._nrbits:
                raise ConversionError(_error.InconsistentBitWidth, s._name)


def _analyzeGens(top, absnames):
    genlist = []
    for g in top:
        if isinstance(g, _UserCode):
            tree = g
        elif isinstance(g, (_AlwaysComb, _AlwaysSeq, _Always)):
            f = g.func
            tree = g.ast
            tree.symdict = f.__globals__.copy()
            tree.callstack = []
            # handle free variables
            tree.nonlocaldict = {}
            if f.__code__.co_freevars:
                for n, c in zip(f.__code__.co_freevars, f.__closure__):
                    obj = c.cell_contents
                    tree.symdict[n] = obj
                    # currently, only intbv as automatic nonlocals
                    # (until Python 3.0)
                    if isinstance(obj, (intbv, bitarray)):
                        tree.nonlocaldict[n] = obj
            tree.name = absnames.get(id(g), str(_Label("BLOCK"))).upper()
            v = _AttrRefTransformer(tree)
            v.visit(tree)
            v = _FirstPassVisitor(tree)
            v.visit(tree)
            if isinstance(g, _AlwaysComb):
                v = _AnalyzeAlwaysCombVisitor(tree, g.senslist)
            elif isinstance(g, _AlwaysSeq):
                v = _AnalyzeAlwaysSeqVisitor(tree, g.senslist, g.reset,
                                             g.sigregs, g.varregs)
            else:
                v = _AnalyzeAlwaysDecoVisitor(tree, g.senslist)
            v.visit(tree)
        else:  # @instance
            f = g.gen.gi_frame
            tree = g.ast
            tree.symdict = f.f_globals.copy()
            tree.symdict.update(f.f_locals)
            tree.nonlocaldict = {}
            tree.callstack = []
            tree.name = absnames.get(id(g), str(_Label("BLOCK"))).upper()
            v = _AttrRefTransformer(tree)
            v.visit(tree)
            v = _FirstPassVisitor(tree)
            v.visit(tree)
            v = _AnalyzeBlockVisitor(tree)
            v.visit(tree)
        genlist.append(tree)

    return genlist


class _FirstPassVisitor(ast.NodeVisitor, _ConversionMixin):

    """First pass visitor.

    Prune unsupported contructs, and add some useful attributes.

    """

    def __init__(self, tree):
        self.tree = tree
        self.toplevel = True

    def visit_Tuple(self, node):
        if isinstance(node.ctx, ast.Store):
            self.raiseError(node, _error.NotSupported, "tuple assignment")

    def visit_Repr(self, node):
        self.raiseError(node, _error.NotSupported, "backquote")

    def visit_ClassDef(self, node):
        self.raiseError(node, _error.NotSupported, "class statement")

    def visit_Dict(self, node):
        self.raiseError(node, _error.NotSupported, "dictionary")

    # def visit_BinOp(self, node):
    #     if isinstance(node.op, ast.Div):
    #

    def visit_Ellipsis(self, node):
        self.raiseError(node, _error.NotSupported, "ellipsis")

    def visit_Exec(self, node):
        self.raiseError(node, _error.NotSupported, "exec statement")

    def visitExpression(self, node, *args):
        self.raiseError(node, _error.NotSupported, "Expression node")

    def visit_ImportFrom(self, node):
        self.raiseError(node, _error.NotSupported, "from statement")

    def visit_Global(self, node):
        self.raiseError(node, _error.NotSupported, "global statement")

    def visit_Import(self, node):
        self.raiseError(node, _error.NotSupported, "import statement")

    def visit_Lambda(self, node):
        self.raiseError(node, _error.NotSupported, "lambda statement")

    def visit_ListComp(self, node):
        if len(node.generators) > 1:
            self.raiseError(node, _error.NotSupported, "multiple for"
                            " statements in list comprehension")
        if node.generators[0].ifs:
            self.raiseError(node, _error.NotSupported, "if statement in list"
                            " comprehension")
        self.generic_visit(node)

    def visit_List(self, node):
        self.raiseError(node, _error.NotSupported, "list")

    def visitSliceObj(self, node):
        self.raiseError(node, _error.NotSupported, "slice object")

    # All try blocks from python 3.3+
    def visit_Try(self, node):
        self.raiseError(node, _error.NotSupported, "try statement")

    # Legacy try blocks
    def visit_TryExcept(self, node):
        self.raiseError(node, _error.NotSupported, "try-except statement")

    def visit_TryFinally(self, node):
        self.raiseError(node, _error.NotSupported, "try-finally statement")

    def visit_Assign(self, node):
        if len(node.targets) > 1:
            self.raiseError(node, _error.NotSupported, "multiple assignments")
        self.visit(node.targets[0])
        self.visit(node.value)

    def visit_Call(self, node):
        # ast.Call signature changed in python 3.5
        # http://greentreesnakes.readthedocs.org/en/latest/nodes.html#Call
        if sys.version_info >= (3, 5):
            starargs = any(isinstance(arg, ast.Starred) for arg in node.args)
            kwargs = any(kw.arg is None for kw in node.keywords)
        else:
            starargs = node.starargs is not None
            kwargs = node.kwargs is not None

        if starargs:
            self.raiseError(node, _error.NotSupported, "extra positional"
                            " arguments")
        if kwargs:
            self.raiseError(node, _error.NotSupported, "extra named arguments")
        self.generic_visit(node)

    def visit_Compare(self, node):
        if len(node.ops) != 1:
            self.raiseError(node, _error.NotSupported, "chained comparison")
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.args.vararg or node.args.kwarg:
            self.raiseError(node, _error.NotSupported, "extra positional or"
                            " named arguments")
        if not self.toplevel:
            self.raiseError(node, _error.NotSupported, "embedded function"
                            " definition")
        self.toplevel = False
        node.argnames = _get_argnames(node)
        # don't visit decorator lists - they can support more than other calls
        # put official docstrings aside for separate processing
        node.doc = None
        if node.body and isinstance(node.body[0], ast.Expr) and \
                isinstance(node.body[0].value, ast.Str):
            node.doc = node.body[0].value.s
            node.body = node.body[1:]
        self.visitList(node.body)

    def flattenIf(self, node, tests, else_, co):
        """ Flatten if-then-else as in compiler package."""
        if node:
            # ugly hack to detect separate else clause
            if len(node) == 1 and \
                    isinstance(node[0], ast.If) and \
                    node[0].body[0].col_offset == co:
                elifnode = node[0]
                tests.append((elifnode.test, elifnode.body))
                self.flattenIf(elifnode.orelse, tests, else_, co)
            else:
                else_[:] = node

    def visit_If(self, node):
        node.ignore = False
        if not node.orelse:
            test = node.test
            if isinstance(test, ast.Name):
                if test.id == '__debug__':
                    node.ignore = True
                    return  # skip
        self.generic_visit(node)

        # add fields that match old compiler package
        tests = [(node.test, node.body)]
        else_ = []
        self.flattenIf(node.orelse, tests, else_, node.body[0].col_offset)
        node.tests = tests
        node.else_ = else_

    def visit_Print(self, node):
        if node.dest is not None:
            self.raiseError(node, _error.NotSupported, "printing to a file"
                            " with >> syntax")
        if not node.nl:
            self.raiseError(node, _error.NotSupported, "printing without"
                            " newline")


def getNrBits(obj):
    if hasattr(obj, '_nrbits'):
        return obj._nrbits
    return None


def hasType(obj, theType):
    if isinstance(obj, theType):
        return True
    if isinstance(obj, _Signal):
        if isinstance(obj._val, theType):
            return True
    return False


class ReferenceStack(list):
    def push(self):
        self.append(set())

    def add(self, item):
        self[-1].add(item)

    def __contains__(self, item):
        for s in self:
            if item in s:
                return True
        return False


class _Ram(object):
    __slots__ = ['elObj', 'depth']


class _Rom(object):
    __slots__ = ['elObj', 'rom']

    def __init__(self, rom):
        self.rom = rom
        self.elObj = rom[0]

    @property
    def depth(self):
        return len(self.rom)

re_str = re.compile(r"[^%]+")
re_ConvSpec = re.compile(r"%(?P<justified>[-]?)"
                         "(?P<width>[0-9]*)(?P<conv>[sd])")


class ConvSpec(object):
    def __init__(self, **kwargs):
        self.justified = "RIGHT"
        self.width = 0
        self.conv = str
        if kwargs['justified'] == '-':
            self.justified = "LEFT"
        if kwargs['width']:
            self.width = int(kwargs['width'])
        if kwargs['conv'] == 'd':
            self.conv = int

defaultConvSpec = ConvSpec(**re_ConvSpec.match(r"%s").groupdict())


def _getNritems(obj):
    """Return the number of items in an objects' type"""
    if isinstance(obj, _Signal):
        obj = obj._init
    if isinstance(obj, (intbv, bitarray)):
        return obj.max - obj.min
    elif isinstance(obj, EnumItemType):
        return len(obj._type)
    else:
        raise TypeError("Unexpected type, missing final \'else:\'?")


class _AnalyzeVisitor(ast.NodeVisitor, _ConversionMixin):

    def __init__(self, tree):
        tree.sigdict = {}
        tree.vardict = {}
        tree.inputs = set()
        tree.outputs = set()
        # hack for assigned mems
        tree.outmems = set()
        tree.argnames = []
        tree.kind = None
        tree.hasYield = 0
        tree.hasRom = False
        tree.hasLos = False
        tree.hasPrint = False
        self.tree = tree
        self.labelStack = []
        self.refStack = ReferenceStack()
        self.globalRefs = set()
        self.access = _access.INPUT
        self.kind = _kind.NORMAL
        self.myhdlObjects = set(val for _, val in
                                inspect.getmembers(sys.modules["myhdl"],
                                                   inspect.isclass))
        modules = inspect.getmembers(sys.modules["myhdl"],
                                     inspect.ismodule)
        for _, module in modules:
            self.myhdlObjects.update([val for _, val in
                                      inspect.getmembers(module,
                                                         inspect.isclass)])
            self.myhdlObjects.update([val for _, val in
                                      inspect.getmembers(module,
                                                         inspect.isfunction)])
        self.builtinObjects = builtins.__dict__.values()

    def _add_size(self, node, l, r):
        result = l + r
        if isinstance(result, integer_types):
            if result < 0:
                node.obj = long(-1)
            else:
                node.obj = long(0)
        else:
            node.obj = result

    def _sub_size(self, node, l, r):
        result = l - r
        if isinstance(result, integer_types):
            node.obj = long(-1)
        else:
            node.obj = result

    def _truediv_size(self, node, l, r):
        if r == 0:
            if isinstance(r, (intbv, bitarray)):
                if r.max != 0:
                    r_val = r.max
                else:
                    r_val = r.min
                r_obj = type(r)(r_val, r)
            else:
                r_obj = r
        else:
            r_obj = r
        result = l / r_obj
        if result is NotImplemented:
            raise NotImplementedError()
        elif isinstance(result, integer_types):
            if l < 0 or r < 0:
                node.obj = long(-1)
            else:
                node.obj = long(0)
        else:
            node.obj = result

    def _floordiv_size(self, node, l, r):
        if r == 0:
            if isinstance(r, (intbv, bitarray)):
                if r.max != 0:
                    r_val = r.max
                else:
                    r_val = r.min
                r_obj = type(r)(r_val, r)
            else:
                r_obj = r
        else:
            r_obj = r
        result = l // r_obj
        if isinstance(result, integer_types):
            if l < 0 or r < 0:
                node.obj = long(-1)
            else:
                node.obj = long(0)
        else:
            node.obj = result

    def _mod_size(self, node, l, r):
        if r == 0:
            if isinstance(r, (intbv, bitarray)):
                if r.max != 0:
                    r_val = r.max
                else:
                    r_val = r.min
                r_obj = type(r)(r_val, r)
            else:
                r_obj = type(r)(1)
        else:
            r_obj = r
        result = l % r_obj
        if isinstance(result, integer_types):
            if l < 0 or r < 0:
                node.obj = long(-1)
            else:
                node.obj = long(0)
        else:
            node.obj = result

    def _mul_size(self, node, l, r):
        result = abs(l) * abs(r)
        if isinstance(result, integer_types):
            if l < 0 or r < 0:
                node.obj = long(-1)
            else:
                node.obj = long(0)
        else:
            node.obj = result

    def _bitop_size(self, node, l, r):
        try:
            if isinstance(node.op, ast.BitAnd):
                node.obj = l & r
            elif isinstance(node.op, ast.BitOr):
                node.obj = l | r
            elif isinstance(node.op, ast.BitXor):
                node.obj = l ^ r
        except TypeError as e:
            self.raiseError(node, _error.NotSupported, e)

    def visit_BinOp(self, node):
        self.visit(node.left)
        self.visit(node.right)
        # Not compatible with collections
        if hasattr(node.left, 'obj') and hasattr(node.right, 'obj'):
            l = node.left.obj
            if isinstance(l, _Signal):
                l = l._val
            r = node.right.obj
            if isinstance(r, _Signal):
                r = r._val
            if isinstance(node.op, ast.Add):
                self._add_size(node, l, r)
            elif isinstance(node.op, ast.Sub):
                self._sub_size(node, l, r)
            elif isinstance(node.op, ast.FloorDiv):
                self._floordiv_size(node, l, r)
            elif isinstance(node.op, ast.Div):
                try:
                    self._truediv_size(node, l, r)
                except NotImplementedError:
                    self.raiseError(node, _error.NotSupported, "true division"
                                    " - consider '//'")
            elif isinstance(node.op, ast.Mod):
                if isinstance(l, string_types):
                    node.obj = long(-1)
                else:
                    self._mod_size(node, l, r)
            elif isinstance(node.op, ast.Mult):
                self._mul_size(node, l, r)
            elif isinstance(node.op, (ast.BitAnd, ast.BitOr, ast.BitXor)):
                self._bitop_size(node, l, r)
            elif isinstance(node.op, (ast.LShift, ast.RShift, ast.Pow)):
                node.obj = node.left.obj
                if isinstance(node.obj, _Signal) and \
                        issubclass(node.obj._type, intbv):
                    node.obj = node.obj._init
            else:
                raise AssertionError("Unknown binary operator: %s" % node.op)
            if isinstance(node.obj, bool):
                pass
            elif isinstance(node.obj, (integer_types, intbv)):
                node.obj = long(node.obj)
        else:
            node.obj = long(-1)

    def visit_BoolOp(self, node):
        for n in node.values:
            self.visit(n)
        for n in node.values:
            if not hasType(n.obj, bool):
                self.raiseError(node, _error.NotSupported, "non-boolean"
                                " argument in logical operator")
        node.obj = bool()

    def visit_UnaryOp(self, node):
        self.visit(node.operand)
        op = node.op
        node.obj = node.operand.obj
        if isinstance(op, ast.Not):
            node.obj = bool()
        elif isinstance(op, (ast.UAdd, ast.USub, ast.Invert)) and \
                not (isinstance(node.obj, bitarray) or
                     (isinstance(node.obj, _Signal) and
                      isinstance(node.obj._init, bitarray))):
            node.obj = long(-1)

    def visit_Attribute(self, node):
        if isinstance(node.ctx, ast.Store):
            self.setAttr(node)
        else:
            self.getAttr(node)
        if node.attr == 'next':
            if isinstance(node.value, ast.Name):
                n = node.value.id
                obj = node.value.obj
                if isinstance(obj, _Signal) and isinstance(obj._init, modbv):
                    if not obj._init._hasFullRange():
                        self.raiseError(node, _error.ModbvRange, n)

    def setAttr(self, node):
        if node.attr != 'next':
            self.raiseError(node, _error.NotSupported, "attribute assignment")
        self.tree.kind = _kind.TASK
        # self.access = _access.OUTPUT
        self.visit(node.value)
        # self.access = _access.INPUT

    def getAttr(self, node):
        self.visit(node.value)
        node.obj = None
        if isinstance(node.value, ast.Name):
            n = node.value.id
            if (n not in self.tree.vardict) and (n not in self.tree.symdict):
                raise AssertionError("attribute target: %s" % n)
        obj = node.value.obj
        if isinstance(obj, _Signal):
            if node.attr == 'posedge':
                node.obj = obj.posedge
            elif node.attr == 'negedge':
                node.obj = obj.negedge
            elif node.attr in ('val', 'next'):
                node.obj = obj.val
        if isinstance(obj, intbv) or \
                (isinstance(obj, _Signal) and isinstance(obj._init, intbv)):
            if node.attr == 'min':
                node.obj = obj.min
            elif node.attr == 'max':
                node.obj = obj.max
            elif node.attr == 'signed':
                node.obj = intbv.signed
        if isinstance(obj, bitarray) or \
                (isinstance(obj, _Signal) and isinstance(obj._init, bitarray)):
            if node.attr in numeric_attributes_dict:
                node.obj = getattr(obj, node.attr)
            elif node.attr in numeric_functions_dict.values():
                local_values = locals()
                global_values = globals()
                value = type(obj)
                if isinstance(obj, _Signal):
                    value = type(obj._init)
                method = getattr(value, node.attr)
                node.obj = method
        if isinstance(obj, EnumType):
            if not hasattr(obj, node.attr):
                pass
            assert hasattr(obj, node.attr), "%s.%s" % \
                (node.value.id, node.attr)
            node.obj = getattr(obj, node.attr)
            if obj not in _enumTypeSet:
                _enumTypeSet.add(obj)
                suf = _genUniqueSuffix.next()
                obj._setName(n+suf)
        if node.obj is None:  # attribute lookup failed
            self.raiseError(node, _error.UnsupportedAttribute, node.attr)

    def visit_Assign(self, node):
        target, value = node.targets[0], node.value
        self.access = _access.OUTPUT
        self.visit(target)
        self.access = _access.INPUT
        # set attribute to detect a top-level rhs
        value.isRhs = True
        if isinstance(target, ast.Name):
            node.kind = _kind.DECLARATION
            self.kind = _kind.DECLARATION
            self.visit(value)
            self.kind = _kind.NORMAL
            n = target.id
            if n in self.tree.sigdict:
                self.raiseError(node, _error.ShadowingVar, n)
            obj = self.getObj(value)
            if obj is None:
                obj = self.getValue(value)
                if obj is None:
                    self.raiseError(node, _error.TypeInfer, n)
            if isinstance(obj, (intbv, bitarray)):
                if len(obj) == 0:
                    self.raiseError(node, _error.IntbvBitWidth, n)
            if isinstance(obj, modbv):
                if not obj._hasFullRange():
                    self.raiseError(node, _error.ModbvRange, n)
            if n in self.tree.vardict:
                curObj = self.tree.vardict[n]
                if isinstance(obj, type(curObj)):
                    if isinstance(obj, integer_types) and obj < 0:
                        self.tree.vardict[n] = obj
                elif isinstance(curObj, type(obj)):
                    self.tree.vardict[n] = obj
                elif isinstance(obj, integer_types) and \
                        isinstance(curObj, integer_types):
                    self.tree.vardict[n] = long(obj)
                elif isinstance(obj, integer_types) and \
                        isinstance(curObj, bool):
                    self.tree.vardict[n] = obj
                elif isinstance(obj, bool) and \
                        isinstance(curObj, integer_types):
                    pass
                elif isinstance(obj, float) and \
                        isinstance(curObj, (bool, integer_types)):
                    self.tree.vardict[n] = obj
                elif isinstance(obj, (bool, integer_types)) and \
                        isinstance(curObj, float):
                    pass
                else:
                    self.raiseError(node, _error.TypeMismatch, n)
                if getNrBits(obj) != getNrBits(curObj):
                    self.raiseError(node, _error.NrBitsMismatch, n)
            else:
                self.tree.vardict[n] = obj
        else:
            self.visit(value)

    def visit_AugAssign(self, node):
        # declare node as an rhs for type inference optimization
        node.isRhs = True
        self.access = _access.INOUT
        self.visit(node.target)
        self.access = _access.INPUT
        self.visit(node.value)

    def visit_Break(self, node):
        self.labelStack[-2].isActive = True

    def visit_Call(self, node):
        self.visit(node.func)
        f = self.getObj(node.func)
        node.obj = None
        self.access = _access.UNKNOWN
        for arg in node.args:
            self.visit(arg)
        for kw in node.keywords:
            self.visit(kw)
        self.access = _access.INPUT
        argsAreInputs = True
        if type(f) is type and issubclass(f, (intbv, bitarray)):
            node.obj = self.getVal(node)
        elif f in numeric_functions_dict:
            # Add the object as the first argument.
            node.obj = self.getVal(node)
            node.args.insert(0, node.func.value)
        elif f is concat:
            node.obj = self.getVal(node)
        elif f is len:
            self.access = _access.UNKNOWN
            node.obj = long(0)  # XXX
        elif f is bool:
            node.obj = bool()
        elif f in _flatten(integer_types, ord):
            try:
                if self.getVal(node) < 0:
                    node.obj = long(-1)
                else:
                    node.obj = long(0)
            except ConversionError:
                # To have a default value in case the conversion fails.
                node.obj = long(-1)
        # elif f in (posedge , negedge):
        #     node.obj = _EdgeDetector()
        elif f is float:
            node.obj = float(-1.0)
        elif f is delay:
            node.obj = delay(0)
        elif f == intbv.signed:
            node.obj = int(-1)
        elif f is print:
            argsAreInputs = False
            if hasattr(node, 'keywords'):
                for keyword in node.keywords:
                    if keyword.arg == 'file':
                        self.raiseError(node, _error.NotSupported, "print to"
                                        " file with file= syntax")
                    elif keyword.arg == 'end':
                        self.raiseError(node, _error.NotSupported, "print"
                                        " end keyword not support")
            self.visit_Print(node)
        elif f in self.myhdlObjects:
            pass
        elif f is repr:
            self.raiseError(node, _error.NotSupported, "backquote or repr")
        elif f in self.builtinObjects:
            if f.__name__ == 'exec':
                self.raiseError(node, _error.NotSupported, "exec function")
            pass
        elif type(f) is FunctionType:
            argsAreInputs = False
            tree = _makeAST(f)
            fname = f.__name__
            tree.name = _Label(fname)
            tree.symdict = f.__globals__.copy()
            tree.nonlocaldict = {}
            if fname in self.tree.callstack:
                self.raiseError(node, _error.NotSupported, "Recursive call")
            tree.callstack = self.tree.callstack[:]
            tree.callstack.append(fname)
            # handle free variables
            if f.__code__.co_freevars:
                for n, c in zip(f.__code__.co_freevars, f.__closure__):
                    obj = c.cell_contents
                    if not isinstance(obj, (integer_types, float, _Signal)):
                        self.raiseError(node, _error.FreeVarTypeError, n)
                    tree.symdict[n] = obj
            v = _FirstPassVisitor(tree)
            v.visit(tree)
            v = _AnalyzeFuncVisitor(tree, node.args, node.keywords)
            v.visit(tree)
            node.obj = tree.returnObj
            node.tree = tree
            tree.argnames = argnames = _get_argnames(tree.body[0])
            # extend argument list with keyword arguments on the correct
            # position
            node.args.extend([None]*len(node.keywords))
            for kw in node.keywords:
                node.args[argnames.index(kw.arg)] = kw.value
            for n, arg in zip(argnames, node.args):
                if n in tree.outputs:
                    self.access = _access.OUTPUT
                    self.visit(arg)
                    self.access = _access.INPUT
                if n in tree.inputs:
                    self.visit(arg)
        elif type(f) is MethodType:
            fname = f.__name__
            self.raiseError(node, _error.NotSupported, "method call: '%s'" %
                            fname)
        else:
            debug_info = [e for e in ast.iter_fields(node.func)]
            raise AssertionError("Unexpected callable %s" % str(debug_info))
        if argsAreInputs:
            for arg in node.args:
                self.visit(arg)

    def visit_Compare(self, node):
        node.obj = bool()
        for n in [node.left] + node.comparators:
            self.visit(n)
        op, arg = node.ops[0], node.comparators[0]
        # node.expr.target = self.getObj(arg)
        # arg.target = self.getObj(node.expr)
        # detect specialized case for the test
        if isinstance(node.left, ast.Name) and \
                (isinstance(op, ast.Eq) or
                 ((isinstance(op, ast.In) and isinstance(arg, ast.Tuple)))):
            if isinstance(arg, ast.Tuple):
                args = arg.elts
            else:
                args = (arg,)
            # check wether it can be a case
            cases = []
            for arg in args:
                val = arg.obj
                if isinstance(val, bool):
                    val = int(val)  # cast bool to int first
                if isinstance(val, (EnumItemType, integer_types)):
                    cases.append((node.left, val))
                    if isinstance(arg, ast.Name):
                        name = arg.id
                        if (name in self.tree.objlist) and \
                                (self.tree.symdict[name] == val):
                            cases.append((node.left, name))
            if cases:
                node.case = cases
            # check whether it can be part of an edge check
            n = node.left.id
            if n in self.tree.sigdict:
                sig = self.tree.sigdict[n]
                v = self.getValue(arg)
                if v is not None:
                    if v == 0:
                        node.edge = sig.negedge
                    elif v == 1:
                        node.edge = sig.posedge

    def visit_Num(self, node):
        n = node.n
        # assign to value attribute for backwards compatibility
        node.value = n
        if n in (0, 1):
            node.obj = bool(n)
        elif isinstance(n, (integer_types, float)):
            node.obj = n
        else:
            node.obj = None

    def visit_Str(self, node):
        node.obj = node.s

    def visit_Continue(self, node):
        self.labelStack[-1].isActive = True

    def visit_For(self, node):
        node.breakLabel = _Label("BREAK")
        node.loopLabel = _Label("LOOP")
        self.labelStack.append(node.breakLabel)
        self.labelStack.append(node.loopLabel)
        self.refStack.push()
        self.visit(node.target)
        var = node.target.id

        cf = node.iter
        self.visit(cf)
        self.require(node, isinstance(cf, ast.Call),
                     "Expected (down)range call")
        f = self.getObj(cf.func)
        self.require(node, f in (range, downrange),
                     "Expected (down)range call")
        if len(cf.args) == 1 or (cf.args[0].obj >= 0 and cf.args[1].obj >= 0):
            self.tree.vardict[var] = 0
        else:
            self.tree.vardict[var] = -1

        for stmt in node.body:
            self.visit(stmt)
        self.refStack.pop()
        self.require(node, not node.orelse, "for-else not supported")
        self.labelStack.pop()
        self.labelStack.pop()

    def visit_FunctionDef(self, node):
        raise AssertionError("subclass must implement this")

    def visit_If(self, node):
        const_names = False
        if node.ignore:
            return
        for test, suite in node.tests:
            self.visit(test)
            if hasattr(test, "case") and isinstance(test.case[0][1], str):
                const_names = True
            self.refStack.push()
            self.visitList(suite)
            self.refStack.pop()
        if node.else_:
            self.refStack.push()
            self.visitList(node.else_)
            self.refStack.pop()
        # check whether the if can be mapped to a (parallel) case
        node.isCase = node.isFullCase = False
        test1 = node.tests[0][0]
        if not hasattr(test1, 'case'):
            return
        # don't infer a case if there's no elsif test
        if not node.tests[1:]:
            return

        var1, item1 = test1.case[0]
        choices = set(item for _, item in test1.case)

        for test, suite in node.tests[1:]:
            if not hasattr(test, 'case'):
                return
            for var, item in test.case:
                if var.id != var1.id or type(item) is not type(item1):
                    return
                if item in choices:
                    return
                choices.add(item)
        node.isCase = True
        node.caseVar = var1
        node.caseItem = item1
        if (node.else_ or (len(choices) == _getNritems(var1.obj))) and \
                (not const_names):
            node.isFullCase = True

    def visit_ListComp(self, node):
        mem = node.obj = _Ram()
        self.kind = _kind.DECLARATION
        try:
            self.visit(node.elt)
        except ConversionError as e:
            if e.kind == _error.UnboundLocal:
                pass
            else:
                raise
        self.kind = _kind.NORMAL
        mem.elObj = self.getObj(node.elt)
        if not isinstance(mem.elObj, (intbv, bitarray)) or \
                not len(mem.elObj) > 0:
            self.raiseError(node, _error.UnsupportedListComp)
        cf = node.generators[0].iter
        self.visit(cf)
        if not isinstance(cf, ast.Call):
            self.raiseError(node, _error.UnsupportedListComp)
        f = self.getObj(cf.func)
        if f is not range or len(cf.args) != 1:
            self.raiseError(node, _error.UnsupportedListComp)
        mem.depth = cf.args[0].obj

    def visit_NameConstant(self, node):
        node.obj = node.value

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.setName(node)
        else:
            self.getName(node)

    def setName(self, node):
        # XXX INOUT access in Store context, unlike with compiler
        # XXX check whether ast context is correct
        n = node.id
        if self.access == _access.INOUT:  # augmented assign
            if n in self.tree.sigdict:
                sig = self.tree.sigdict[n]
                if isinstance(sig, _Signal):
                    self.raiseError(node, _error.NotSupported,
                                    "Augmented signal assignment")
            if n in self.tree.vardict:
                obj = self.tree.vardict[n]
                # upgrade bool to int for augmented assignments
                if isinstance(obj, bool):
                    obj = int(-1)
                    self.tree.vardict[n] = obj
                node.obj = obj
        else:
            if n in ("__verilog__", "__vhdl__"):
                    self.raiseError(node, _error.NotSupported,
                                    "%s in generator function" % n)
            if n in self.globalRefs:
                self.raiseError(node, _error.UnboundLocal, n)
            self.refStack.add(n)

    def getName(self, node):
        n = node.id
        node.obj = None
        if n not in self.refStack:
            if (n in self.tree.vardict) and (n not in self.tree.nonlocaldict):
                self.raiseError(node, _error.UnboundLocal, n)
            self.globalRefs.add(n)
        if n in self.tree.sigdict:
            node.obj = sig = self.tree.sigdict[n]
            # mark shadow signal as driven only when they are seen somewhere
            if isinstance(sig, _ShadowSignal):
                sig._driven = 'wire'
            if isinstance(sig, _TristateDriver):
                sig._sig._driven = 'wire'
            if not isinstance(sig, _Signal):
                # print "not a signal: %s" % n
                pass
            else:
                if sig._type is bool:
                    node.edge = sig.posedge
            if self.access == _access.INPUT:
                self.tree.inputs.add(n)
            elif self.access == _access.OUTPUT:
                self.tree.kind = _kind.TASK
                if n in self.tree.outputs:
                    node.kind = _kind.REG
                self.tree.outputs.add(n)
            elif self.access == _access.UNKNOWN:
                pass
            else:
                self.raiseError(node, _error.NotSupported,
                                "Augmented signal assignment")
        if n in self.tree.vardict:
            obj = self.tree.vardict[n]
            if self.access == _access.INOUT:  # probably dead code
                # upgrade bool to int for augmented assignments
                if isinstance(obj, bool):
                    obj = int(-1)
                    self.tree.vardict[n] = obj
            node.obj = obj
        elif n in self.tree.symdict:
            node.obj = self.tree.symdict[n]
            if _isTupleOfInts(node.obj) or _isTupleOfFloats(node.obj):
                node.obj = _Rom(node.obj)
                self.tree.hasRom = True
            elif _isMem(node.obj):
                m = _getMemInfo(node.obj)
                if self.access == _access.INPUT:
                    m._read = True
                elif self.access == _access.OUTPUT:
                    m._driven = 'reg'
                    self.tree.outmems.add(n)
                elif self.access == _access.UNKNOWN:
                    pass
                else:
                    assert False, "unexpected mem access %s %s" % \
                        (n, self.access)
                self.tree.hasLos = True
            elif isinstance(node.obj, integer_types):
                node.value = node.obj
            elif isinstance(node.obj, float):
                node.value = node.obj
            if n in self.tree.nonlocaldict:
                # hack: put nonlocal intbv's in the vardict
                self.tree.vardict[n] = node.obj
        elif n in builtins.__dict__:
            node.obj = builtins.__dict__[n]
        else:
            self.raiseError(node, _error.UnboundLocal, n)

    def visit_Return(self, node):
        self.raiseError(node, _error.NotSupported, "return statement")

    def visit_Print(self, node):
        self.tree.hasPrint = True
        f = []
        nr = 0
        a = []
        if PY2 and isinstance(node, ast.Print):
            node_args = node.values
            if (len(node_args) == 1) and isinstance(node_args[0], ast.Tuple):
                node_args = node_args[0].elts
        else:
            node_args = node.args
        for n in node_args:
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) and \
               isinstance(n.left, ast.Str):
                if isinstance(n.right, ast.Tuple):
                    a.extend(n.right.elts)
                else:
                    a.append(n.right)
                s = n.left.s
                while s:
                    if not s:
                        break
                    if s[:2] == "%%":
                        f.append("%")
                        s = s[2:]
                        continue
                    m = re_ConvSpec.match(s)
                    if m:
                        c = ConvSpec(**m.groupdict())
                        if c.justified != "RIGHT":
                            self.raiseError(node,
                                            _error.UnsupportedFormatString,
                                            "format justification"
                                            " specification: %s" % s)
                        if c.width != 0:
                            self.raiseError(node,
                                            _error.UnsupportedFormatString,
                                            "format width"
                                            " specification: %s" % s)
                        f.append(c)
                        s = s[m.end():]
                        nr += 1
                        continue
                    m = re_str.match(s)
                    if m:
                        f.append(s[:m.end()])
                        s = s[m.end():]
                        continue
                    self.raiseError(node, _error.UnsupportedFormatString,
                                    "%s" % s)
            else:
                f.append(defaultConvSpec)
                a.append(n)
                nr += 1
            f.append(" ")
        # remove last single space if it exists
        if f:
            f.pop()
        node.format = f
        node.args = a
        if len(node.args) < nr:
            self.raiseError(node, _error.FormatString, "not enough arguments")
        if len(node.args) > nr:
            self.raiseError(node, _error.FormatString, "too many arguments")
        self.generic_visit(node)

    def visit_Subscript(self, node):
        if isinstance(node.slice, ast.Slice):
            self.accessSlice(node)
        else:
            self.accessIndex(node)

    def accessSlice(self, node):
        self.visit(node.value)
        node.obj = self.getObj(node.value)
        self.access = _access.INPUT
        lower, upper = node.slice.lower, node.slice.upper
        if lower:
            self.visit(lower)
        if upper:
            self.visit(upper)
        if isinstance(node.obj, (intbv, bitarray)):
            if self.kind == _kind.DECLARATION:
                self.require(lower, "Expected leftmost index")
                leftind = self.getVal(lower)
                if upper:
                    rightind = self.getVal(upper)
                else:
                    rightind = 0
                node.obj = node.obj[leftind:rightind]

    def accessIndex(self, node):
        self.visit(node.value)
        self.access = _access.INPUT
        self.visit(node.slice.value)
        if isinstance(node.value.obj, _Ram):
            if isinstance(node.ctx, ast.Store):
                self.raiseError(node, _error.ListElementAssign)
            else:
                node.obj = node.value.obj.elObj
        elif _isMem(node.value.obj):
            node.obj = node.value.obj[0]
        elif isinstance(node.value.obj, _Rom):
            for value in node.value.obj.rom:
                if value < 0:
                    node.obj = int(-1)
                    break
            else:
                node.obj = int(1)
        elif isinstance(node.value.obj, (intbv, bitarray)):
            node.obj = bool()
        else:
            node.obj = bool()  # XXX default

    def visit_Tuple(self, node):
        self.generic_visit(node)

    def visit_Try(self, node):
        self.raiseError(node, _error.NotSupported, "try statement")

    def visit_While(self, node):
        node.breakLabel = _Label("BREAK")
        node.loopLabel = _Label("LOOP")
        self.labelStack.append(node.breakLabel)
        self.labelStack.append(node.loopLabel)
        self.visit(node.test)
        self.refStack.push()
        for n in node.body:
            self.visit(n)
        self.refStack.pop()
        y = node.body[0]
        if isinstance(y, ast.Expr):
            y = y.value
        if ((PY2 and (node.test.obj is True)) or
                ((not PY2) and (self.getObj(node.test) is True))) and \
                isinstance(y, ast.Yield) and \
                not self.tree.hasYield > 1 and \
                not isinstance(self.getObj(y.value), delay):
            node.kind = _kind.ALWAYS
            self.tree.senslist = y.senslist
        self.require(node, not node.orelse, "while-else not supported")
        self.labelStack.pop()
        self.labelStack.pop()

    def visit_Yield(self, node, *args):
        self.tree.hasYield += 1
        n = node.value
        self.visit(n)
        senslist = []
        if isinstance(n, ast.Tuple):
            for n in n.elts:
                if not isinstance(n.obj, (_Signal, _WaiterList)):
                    self.raiseError(node, _error.UnsupportedYield)
                senslist.append(n.obj)
        elif isinstance(n.obj, (_Signal, _WaiterList, delay)):
            senslist = [n.obj]
        elif _isMem(n.obj):
            senslist = n.obj
        else:
            self.raiseError(node, _error.UnsupportedYield)
        node.senslist = senslist


class _AnalyzeBlockVisitor(_AnalyzeVisitor):

    def __init__(self, tree):
        _AnalyzeVisitor.__init__(self, tree)
        for n, v in self.tree.symdict.items():
            if isinstance(v, _Signal):
                self.tree.sigdict[n] = v

    def visit_FunctionDef(self, node):
        self.refStack.push()
        for n in node.body:
            self.visit(n)
        self.tree.kind = _kind.ALWAYS
        for n in node.body[:-1]:
            if not self.getKind(n) == _kind.DECLARATION:
                self.tree.kind = _kind.INITIAL
                break
        if self.tree.kind == _kind.ALWAYS:
            w = node.body[-1]
            if not self.getKind(w) == _kind.ALWAYS:
                self.tree.kind = _kind.INITIAL
        self.refStack.pop()

    def visit_Module(self, node):
        self.generic_visit(node)
        for n in self.tree.outputs:
            s = self.tree.sigdict[n]
            if s._driven:
                self.raiseError(node, _error.SigMultipleDriven, n)
            s._driven = "reg"
        for n in self.tree.inputs:
            s = self.tree.sigdict[n]
            s._markRead()

    def visit_Return(self, node):
        # value should be None
        if node.value is None:
            pass
        elif isinstance(node.value, ast.Name) and node.value.id == "None":
            pass
        else:
            self.raiseError(node, _error.NotSupported,
                            "return value other than None")


class _AnalyzeAlwaysCombVisitor(_AnalyzeBlockVisitor):

    def __init__(self, tree, senslist):
        _AnalyzeBlockVisitor.__init__(self, tree)
        self.tree.senslist = senslist

    def visit_FunctionDef(self, node):
        self.refStack.push()
        for n in node.body:
            self.visit(n)
        self.tree.kind = _kind.SIMPLE_ALWAYS_COMB
        for n in node.body:
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Str):
                continue  # skip doc strings
            if isinstance(n, ast.Assign) and \
               isinstance(n.targets[0], ast.Attribute) and \
               self.getKind(n.targets[0].value) != _kind.REG:
                pass
            else:
                self.tree.kind = _kind.ALWAYS_COMB
                return
        # rom access is expanded into a case statement in addition
        # to any always_comb that contains a list of signals
        # if self.tree.hasRom or self.tree.hasLos:
        if self.tree.hasRom:
            self.tree.kind = _kind.ALWAYS_COMB
        self.refStack.pop()

    def visit_Module(self, node):
        _AnalyzeBlockVisitor.visit_Module(self, node)
        if self.tree.kind == _kind.SIMPLE_ALWAYS_COMB:
            for n in self.tree.outputs:
                s = self.tree.sigdict[n]
                s._driven = "wire"
            for n in self.tree.outmems:
                m = _getMemInfo(self.tree.symdict[n])
                m._driven = "wire"


class _AnalyzeAlwaysSeqVisitor(_AnalyzeBlockVisitor):

    def __init__(self, tree, senslist, reset, sigregs, varregs):
        _AnalyzeBlockVisitor.__init__(self, tree)
        self.tree.senslist = senslist
        self.tree.reset = reset
        self.tree.sigregs = sigregs
        self.tree.varregs = varregs

    def visit_FunctionDef(self, node):
        self.refStack.push()
        for n in node.body:
            self.visit(n)
        self.tree.kind = _kind.ALWAYS_SEQ
        self.refStack.pop()


class _AnalyzeAlwaysDecoVisitor(_AnalyzeBlockVisitor):

    def __init__(self, tree, senslist):
        _AnalyzeBlockVisitor.__init__(self, tree)
        self.tree.senslist = senslist

    def visit_FunctionDef(self, node):
        self.refStack.push()
        for n in node.body:
            self.visit(n)
        self.tree.kind = _kind.ALWAYS_DECO
        self.refStack.pop()


class _AnalyzeFuncVisitor(_AnalyzeVisitor):

    def __init__(self, tree, args, keywords):
        _AnalyzeVisitor.__init__(self, tree)
        self.args = args
        self.keywords = keywords
        self.tree.hasReturn = False
        self.tree.returnObj = None

    def visit_FunctionDef(self, node):
        self.refStack.push()
        argnames = _get_argnames(node)
        for i, arg in enumerate(self.args):
            n = argnames[i]
            self.tree.symdict[n] = self.getObj(arg)
            self.tree.argnames.append(n)
        for kw in self.keywords:
            n = kw.arg
            self.tree.symdict[n] = self.getObj(kw.value)
            self.tree.argnames.append(n)
        for n, v in self.tree.symdict.items():
            if isinstance(v, (_Signal, (intbv, bitarray))):
                self.tree.sigdict[n] = v
        for stmt in node.body:
            self.visit(stmt)
        self.refStack.pop()
        if self.tree.hasYield:
            self.raiseError(node, _error.NotSupported,
                            "call to a generator function")
        if self.tree.kind == _kind.TASK:
            if self.tree.returnObj is not None:
                self.raiseError(node, _error.NotSupported,
                                "function with side effects and return value")
        else:
            if self.tree.returnObj is None:
                self.raiseError(node, _error.NotSupported,
                                "pure function without return value")

    def visit_Return(self, node):
        self.kind = _kind.DECLARATION
        if node.value is not None:
            self.visit(node.value)
        self.kind = _kind.NORMAL
        if node.value is None:
            obj = None
        elif isinstance(node.value, ast.Name) and node.value.id == 'None':
            obj = None
        elif (not PY2) and isinstance(node.value, ast.NameConstant):
            obj = node.value.value
        elif node.value.obj is not None:
            obj = node.value.obj
        else:
            self.raiseError(node, _error.ReturnTypeInfer)
        if isinstance(obj, (intbv, bitarray)) and len(obj) == 0:
            self.raiseError(node, _error.ReturnIntbvBitWidth)
        if self.tree.hasReturn:
            returnObj = self.tree.returnObj
            if isinstance(obj, type(returnObj)):
                pass
            elif isinstance(returnObj, type(obj)):
                self.tree.returnObj = obj
            else:
                self.raiseError(node, _error.ReturnTypeMismatch)
            if getNrBits(obj) != getNrBits(returnObj):
                self.raiseError(node, _error.ReturnNrBitsMismatch)
        else:
            self.tree.returnObj = obj
            self.tree.hasReturn = True


ismethod = inspect.ismethod


# inspect doc is wrong: ismethod checks both bound and unbound methods
def isboundmethod(m):
    method = ismethod(m)
    method_self = hasattr(m, '__self__') and m.__self__ is not None
    return method and method_self


def _analyzeTopFunc(func, *args, **kwargs):
    tree = _makeAST(func)
    v = _AnalyzeTopFuncVisitor(func, tree, *args, **kwargs)
    v.visit(tree)

    objs = []
    for name, obj in v.fullargdict.items():
        if not isinstance(obj, _Signal):
            objs.append((name, obj))

    # create ports for any signal in the top instance if it was buried in an
    # object passed as in argument
    # TODO: This will not work for nested objects in the top level
    for name, obj in objs:
        if _isMem(obj):
            m = _getMemInfo(obj)
            m.name = name
            v.argdict[name] = m
            v.argnames.append(name)
        elif hasattr(obj, '__dict__'):
            for attr, attrobj in vars(obj).items():
                if isinstance(attrobj, _Signal):
                    signame = attrobj._name
                    if not signame:
                        signame = name + '_' + attr
                        attrobj._name = signame
                    v.argdict[signame] = attrobj
                    v.argnames.append(signame)
                elif not isinstance(attrobj,
                                    (integer_types, float, EnumItemType)):
                    objs.append((name + '_' + attr, attrobj))

    return v


class _AnalyzeTopFuncVisitor(_AnalyzeVisitor):

    def __init__(self, func, tree, *args, **kwargs):
        self.func = func
        self.tree = tree
        self.args = args
        self.kwargs = kwargs
        self.name = None
        self.fullargdict = {}
        self.argdict = {}
        self.argnames = []

    def visit_FunctionDef(self, node):
        self.name = node.name
        self.argnames = _get_argnames(node)
        if isboundmethod(self.func):
            if not self.argnames[0] == 'self':
                self.raiseError(node, _error.NotSupported,
                                "first method argument name other than 'self'")
            # skip self
            self.argnames = self.argnames[1:]
            self.args = self.args[1:]
        i = -1
        for i, arg in enumerate(self.args):
            n = self.argnames[i]
            self.fullargdict[n] = arg
            if isinstance(arg, _Signal):
                self.argdict[n] = arg
            elif _isMem(arg):
                pass
                # self.raiseError(node, _error.ListAsPort, n)
        for n in self.argnames[i+1:]:
            if n in self.kwargs:
                arg = self.kwargs[n]
                self.fullargdict[n] = arg
                if isinstance(arg, _Signal):
                    self.argdict[n] = arg
                elif _isMem(arg):
                    pass
                    # self.raiseError(node, _error.ListAsPort, n)
        self.argnames = [n for n in self.argnames if n in self.argdict]
