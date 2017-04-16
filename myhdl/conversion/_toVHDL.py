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
#
#  Support for fixed point numbers and multiple entities (c) Jose M. Gomez


""" myhdl toVHDL conversion module.

"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from myhdl._compat import PY2

import sys
import math
import os

import inspect
from datetime import datetime
# import compiler
# from compiler import ast as astNode
import ast
from types import GeneratorType
import warnings
from copy import copy
import string
from collections import namedtuple

from .._version import __version__
from .._enum import EnumItemType, EnumType
from .._intbv import intbv
from .._modbv import modbv
from .._concat import concat
from .._simulator import now
from .._Signal import posedge, negedge
from .._delay import delay
from .._misc import downrange
from .._bin import bin
from .._errors import ToVHDLError, ToVHDLWarning, ConversionError
from .._extractHierarchy import (_HierExtr, _isMem, _isRom, _getMemInfo,
                                 _UserVhdlCode, _userCodeMap, _MemInfo,
                                 _RomInfo, _Constant, _getRomInfo,
                                 _makeMemInfo, _makeRomInfo)
from .._instance import _Instantiator
from ..conversion._misc import _error, _kind, _context, \
    _ConversionMixin, _Label, _genUniqueSuffix, _isConstant
from ..conversion._analyze import _analyzeSigs, _analyzeMems, \
    _analyzeGens, _analyzeTopFunc, _Ram, _Rom, _enumTypeSet
from .._Signal import _Signal, _WaiterList, _SliceSignal, _isListOfSigs
from .._ShadowSignal import ConcatSignal
from ..conversion._toVHDLPackage import _package
from .._util import _flatten, _isTupleOfInts, _isTupleOfFloats
from .._compat import integer_types, class_types, StringIO
from .._ShadowSignal import _TristateSignal, _TristateDriver
from .._resolverefs import _suffixer
from ..numeric._bitarray import bitarray
from ..numeric._uintba import uintba
from ..numeric._sintba import sintba
from ..numeric._sfixba import sfixba, fixmath
from ..numeric._conversion import numeric_types, numeric_functions_dict, \
    numeric_attributes_dict
from collections import Callable

_version = __version__.replace('.', '')
_shortversion = _version.replace('dev', '')
_converting = 0
_profileFunc = None


class _GenerateHierarchy(object):
    def __init__(self):
        self.entities_list = []
        self.mem_types = {}
        self.enum_types = {}
        self.rom_types = {}
        self.sfixed = False

    def __call__(self, h, stdLogicPorts):
        p_entity_dict = {}
        p_offsprings_dict = {}
        p_v_entity_dict = {}
        entity_list = _flatten(h.hierarchy[:])
        absnames = h.absnames

        # Search the associated entities (components)
        for idx, p_entity in enumerate(entity_list):
            p_subentitylist = []
            frame = p_entity.frame

            for p_subentity in entity_list[idx:]:
                if id(p_subentity.frame.f_back) == id(frame):
                    p_subentitylist.append(p_subentity)
                    if p_subentity not in p_offsprings_dict:
                        p_offsprings_dict[p_subentity] = p_entity
                    else:
                        raise ToVHDLError("Offspring has two parents:"
                                          " %s-> %s, %s" %
                                          (p_subentity.name,
                                           p_entity.name,
                                           p_offsprings_dict[p_subentity].name)
                                          )

            p_entity_dict[p_entity] = p_subentitylist

        entity_list.reverse()

        entity_names = set()
        name_counter = 0

        objects_set = set()

        for p_entity in entity_list:
            sigs_list = []
            basename = p_entity.name

            components_list = []

            p_subentities = p_entity_dict[p_entity]

            if getattr(p_entity, 'func', False) is None:
                if p_entity not in p_offsprings_dict:
                    raise ToVHDLError(_error.NotSupported, "Top func: %s" %
                                      p_entity.name)

                p_parent_entity = p_offsprings_dict[p_entity]
                p_parent_subentities = p_entity_dict[p_parent_entity]
                p_parent_subentities.remove(p_entity)
                p_parent_subentities.extend(p_subentities)
                continue

            for p_subentity in p_subentities:
                new_name = "%s_%s" % (basename, p_subentity.name)
                if new_name in entity_names:
                    new_name = "%s_%s" % (new_name, name_counter)
                    name_counter += 1
                entity_names.add(new_name)
                p_subentity.name = new_name
                subentity = p_v_entity_dict[p_subentity]
                subentity.basename = basename
                subentity.name = p_subentity.name
                component = vhd_component(subentity.name, subentity)
                components_list.append(component)
                component._clean_signals(1)

            p_entity_obj = _flatten(p_entity.obj)
            # After having determined the signals and other elements, the
            # duplicated generators are deleted. It has to be done between
            # generating the signals and analyzing the top function to avoid
            # problems with interfaces.
            p_entity_obj_set = set(p_entity_obj)
            p_entity_obj = list(p_entity_obj_set - objects_set)
            objects_set.update(p_entity_obj)
            p_entity.obj = p_entity_obj

            self._check_generators(p_entity_obj)
            gen_list = _analyzeGens(p_entity_obj, absnames)
            sigs_list, mems_list = _analyzeSigs([p_entity], hdl='VHDL',
                                                initlevel=p_entity.level - 1)
            _annotateTypes(gen_list)

            elargs = self._instance_args(p_entity)

            # Infer interface
            intf = _analyzeTopFunc(p_entity.func, *elargs, **{})
            intf.name = p_entity.name

            # Updating the components ports
            for component in components_list:
                component._update()

            # Giving names to port to port signals
            values = inspect.getargvalues(p_entity.frame)
            names_list = []
            sigs_dict, mems_dict, _, _ = \
                self._flattenNames(values.locals.keys(), values.locals,
                                   names_list, sigs_list + mems_list)
            revert_sigs_list = []
            revert_mems_list = []
            for n, s in sigs_dict.items():
                if s._name is None:
                    s._name = n
                    revert_sigs_list.append(s)

            # Updating the slice signals
            for sig in sigs_dict.values():
                if sig._slicesigs:
                    for s in sig._slicesigs:
                        s._setName("VHDL")

            # Naming the signals members of a memory
            for n, m in mems_dict.items():
                m.name = n
                revert_mems_list.append(m)
                for idx, s in enumerate(m.mem):
                    s._name = "%s(%d)" % (n, idx)

            # Adding the local signals
            sigs_dict.update([(s._name, s) for s in sigs_list])
            # Adding the local mems. It must be done after naming the contents
            mems_dict.update([(m.name, m) for m in mems_list])

            self._sanity_checks(intf)

            self._update_assigns(sigs_dict.values())

            vhd_ports_dict, vhd_ports_convert = \
                self._revisePorts(intf, stdLogicPorts)

            self._update_mems(mems_dict.values())
            self._update_slices(sigs_dict.values())

            # Removing the ports signals
            for n in intf.argnames:
                if n in sigs_dict:
                    sigs_dict.pop(n)
            # Removing the ports arrays
            for n in intf.argnames:
                if n in mems_dict:
                    mems_dict.pop(n)

            vhd_signals_dict = dict((s.name, s) for s in vhd_ports_convert)

            for s in sigs_dict.values():
                vhd_obj = inferVhdlObj(s)
                v_s = vhd_signal(s._name, s, vhd_obj, s._used)
                v_s._read_base()
                vhd_signals_dict[s._name] = v_s
                if isinstance(vhd_obj, vhd_enum):
                    self.enum_types[vhd_obj._type] = vhd_obj
                elif isinstance(vhd_obj, vhd_sfixed):
                    self.sfixed = True

            for mem in mems_dict.values():
                vhd_obj = inferVhdlObj(mem)
                v_s = vhd_signal(mem.name, mem, vhd_obj, mem._used)
                v_s._read_base()
                vhd_signals_dict[mem.name] = v_s
                self.mem_types[vhd_obj.toStr(False)] = vhd_obj
                if isinstance(vhd_obj, vhd_array):
                    if isinstance(vhd_obj.type, vhd_enum):
                        self.enum_types[vhd_obj.type._type] = vhd_obj.type
                    elif isinstance(vhd_obj.type, vhd_sfixed):
                        self.sfixed = True

            vhd_consts_dict = {}
            for name, const in p_entity.constdict.items():
                if isinstance(const, _Constant):
                    value = const
                    const = value.value
                else:
                    value = _Constant(name, const)
                vhd_obj = inferVhdlObj(const)
                name = name.upper()
                value.name = name
                vhd_consts_dict[name] = vhd_constant(name,
                                                     value,
                                                     vhd_obj,
                                                     False)
                if isinstance(vhd_obj, vhd_enum):
                    vhd_obj._type._setName(const._name)
                    self.enum_types[vhd_obj._type] = vhd_obj

            for name, rom in p_entity.romdict.items():
                vhd_obj = inferVhdlObj(rom)
                rom.orig_name = name
                name = name.upper()
                rom.name = name
                vhd_consts_dict[name] = vhd_constant(name,
                                                     rom,
                                                     vhd_obj,
                                                     False)
                self.rom_types[vhd_obj.toStr(False)] = vhd_obj
                if isinstance(vhd_obj, vhd_array):
                    if isinstance(vhd_obj.type, vhd_enum):
                        vhd_obj.type._type._setName(rom.name)
                        self.enum_types[vhd_obj.type._type] = vhd_obj

            components_list.sort(key=lambda x: x.name)
            architecture = vhd_architecture(list(sigs_dict.keys()) +
                                            list(mems_dict.keys()),
                                            vhd_signals_dict,
                                            vhd_consts_dict,
                                            components_list=components_list)

            entity = vhd_entity(p_entity.name, intf.argnames, vhd_ports_dict,
                                p_entity, p_entity.level, architecture)
            architecture.entity = entity

            for port in entity.ports_dict.values():
                port.entity = entity

            for signal in architecture.sigs_dict.values():
                signal.entity = entity
                signal.architecture = architecture

            process_list = []

            for generator in gen_list:
                if isinstance(generator, _UserVhdlCode):
                    process = vhd_process([], {}, generator, entity,
                                          architecture)
                else:
                    varlist = list(generator.vardict.keys())
                    varlist.sort()
                    vhd_vars_dict = {}
                    for name, var in generator.vardict.items():
                        vhd_obj = inferVhdlObj(var)
                        if isinstance(vhd_obj, vhd_enum):
                            self.enum_types[vhd_obj._type] = vhd_obj
                        vhd_vars_dict[name] = \
                            vhd_variable(name, var, vhd_obj, entity=entity,
                                         used=True, architecture=architecture)
                    process = vhd_process(varlist, vhd_vars_dict, generator,
                                          entity, architecture)
                    for var in vhd_vars_dict.values():
                        var.process = process

                process_list.append(process)

            process_list.reverse()
            architecture.process_list = process_list

            for component in architecture.components_list:
                for element in component.entity.ports_dict.values():
                    element._read_base()
                    sig = element.signal
                    if isinstance(sig, _MemInfo):
                        name = sig.name
                        assign = False
                    else:
                        name = sig._name
                        assign = sig._assign
                    if (not element.read) and (element.direction == "out"):
                        s_dict = dict(intf.argdict)
                        for n, s in s_dict.items():
                            if isinstance(s, _Signal) and \
                                    (s._assign is not None) and \
                                    name == s._assign._name and s._name:
                                name = n
                                break
                        else:
                            name = "open"
                            warnings.warn("%s: %s.%s" % (_error.UnusedPort,
                                                         component.name,
                                                         element.name),
                                          category=ToVHDLWarning
                                          )
                    elif (not element.driven) and (element.direction == "in"):
                        if isinstance(assign, _Signal) and \
                                assign._name is not None:
                            name = assign._name
                        else:
                            # If the port is an array and has to be intialized to a value,
                            # it must be done by a helping signal
                            if isinstance(element.vhd_type, vhd_array):
                                array_name = element.name
                                used_names = architecture.sigs_list + \
                                    list(architecture.const_dict.keys())
                                print(used_names)
                                array_name = _suffixer(array_name, used_names)
                                array_signal = vhd_signal(array_name, element.signal,
                                                          element.vhd_type, entity, architecture)
                                array_signal.assign = element.assign
                                array_signal.signal_conversion = copy(element.signal_conversion)
                                array_signal.signal_conversion[0].target = array_name
                                architecture.sigs_list.append(array_name)
                                architecture.sigs_dict[array_name] = array_signal
                                name = array_signal.name
                            else:
                                name = element.vhd_type.literal(element.internal)

                    component.ports_signals_dict[element.name] = name

                component.parent = entity
                component.architecture = architecture

            for s in revert_sigs_list:
                s._name = None
            for m in revert_mems_list:
                m.name = None

            p_v_entity_dict[p_entity] = entity
            self.entities_list.append(entity)

            entity._clean_signals()

        return self

    def _flattenNames(self, args_list, args_dict, names_list, existing_signals,
                      base_name=''):
        sigs_dict = {}
        mems_dict = {}
        const_dict = {}
        roms_dict = {}
        for name in args_list:
            if name not in args_dict:
                continue
            obj = args_dict[name]
            old_name = base_name + name
            if isinstance(obj, _Signal):
                if isinstance(obj, _SliceSignal):
                    continue
                if old_name in names_list:
                    arg_name = _suffixer(old_name, names_list)
                else:
                    arg_name = old_name
                id_obj = id(obj)
                for s in existing_signals:
                    if id(s) == id_obj:
                        break
                else:
                    sigs_dict[arg_name] = obj
                    names_list.append(arg_name)
            elif isinstance(obj, _Constant):
                if old_name in names_list:
                    arg_name = _suffixer(old_name, names_list)
                else:
                    arg_name = old_name
                const_dict[arg_name] = obj
                names_list.append(arg_name)
            elif isinstance(obj, (integer_types, float, EnumItemType)):
                if old_name in names_list:
                    arg_name = _suffixer(old_name, names_list)
                else:
                    arg_name = old_name
                const_dict[arg_name] = obj
                names_list.append(arg_name)
            elif _isListOfSigs(obj):
                if old_name in names_list:
                    arg_name = _suffixer(old_name, names_list)
                else:
                    arg_name = old_name
                id_obj = id(obj)
                for m in existing_signals:
                    if id(getattr(m, "mem", None)) == id_obj:
                        break
                else:
                    mems_dict[arg_name] = _makeMemInfo(obj)
                    names_list.append(arg_name)
            elif _isTupleOfInts(obj) or _isTupleOfFloats(obj):
                if old_name in names_list:
                    arg_name = _suffixer(old_name, names_list)
                else:
                    arg_name = old_name
                roms_dict[arg_name] = _makeRomInfo(arg_name, obj)
                names_list.append(arg_name)
            elif (not isinstance(obj, _Instantiator)) and \
                    hasattr(obj, '__dict__') and obj.__dict__ is not None:
                attr_list = list(obj.__dict__.keys())
                attr_list.sort()
                new_sigs, new_mems, new_const, new_roms = \
                    self._flattenNames(attr_list, obj.__dict__,
                                       names_list, existing_signals,
                                       old_name + '_')
                sigs_dict.update(new_sigs)
                mems_dict.update(new_mems)
                const_dict.update(new_const)
                roms_dict.update(new_roms)

        return sigs_dict, mems_dict, const_dict, roms_dict

    def _revisePorts(self, intf, stdLogicPorts):
        vhd_ports_dict = {}
        vhd_ports_convert = []

        for s in intf.argdict.values():
            if isinstance(s, _MemInfo):
                for sig in s.mem:
                    if not s._driven:
                        s._driven = sig._driven
                    if not s._read:
                        s._read = sig._read
            elif s._slicesigs:
                for sig in s._slicesigs:
                    if not sig._driven:
                        s._driven = sig._driven
                    if not s._read:
                        s._read = sig._read
            elif s._assign and s._assign is not None:
                sig = s._assign
                s._driven = "wire"
                sig._read = True

        for name, s in intf.argdict.items():
            vhd_obj = inferVhdlObj(s)
            port = vhd_port(name, s, vhd_obj)
            if isinstance(vhd_obj, vhd_enum):
                self.enum_types[vhd_obj._type] = vhd_obj
            elif isinstance(vhd_obj, vhd_sfixed):
                self.sfixed = True
            elif isinstance(vhd_obj, vhd_array):
                if isinstance(vhd_obj.type, vhd_sfixed):
                    self.sfixed = True
            # change name to convert to std_logic, or
            # make sure signal name is equal to its port name
            port_direction = None
            convert_port = False
            final_name = None
            if isinstance(s, _Signal):
                ds = s
            elif isinstance(s, _MemInfo):
                ds = s.elObj
            if stdLogicPorts and ds._type in (intbv, bitarray):
                final_name = port.name + "_num"
                convert_port = port.name
                vhd_ports_convert.append(vhd_signal(port.name, port.signal,
                                                    port.vhd_type, True))
                for sl in ds._slicesigs:
                    sl._setName('VHDL')
            else:
                final_name = port.name
            if s._driven and not (isinstance(s, _Signal) and
                                  isinstance(s._assign, _Signal) and
                                  s._assign._driven is None):
                if s._read:
                    if not isinstance(ds, _TristateSignal):
                        warnings.warn("%s: %s.%s" % (_error.OutputPortRead,
                                                     intf.name,
                                                     port.name),
                                      category=ToVHDLWarning
                                      )
                    port_direction = "inout"
                else:
                    port_direction = "out"
                s._used = True
            else:
                if not s._read:
                    warnings.warn("%s: %s.%s" % (_error.UnusedPort,
                                                 intf.name,
                                                 port.name),
                                  category=ToVHDLWarning
                                  )
                else:
                    s._used = True
                port_direction = "in"

            port.direction = port_direction
            port.name = final_name
            port.convert = convert_port
            vhd_ports_dict[name] = port
            if isinstance(port.signal, _MemInfo):
                self.mem_types[vhd_obj.toStr(False)] = vhd_obj

        # Indicate to the components that the signal is managed by the port
        for port in vhd_ports_dict.values():
            s = port.signal
            if port.direction == "in":
                s._driven = "reg"
            else:
                s._read = True

        return vhd_ports_dict, vhd_ports_convert

    def _update_mems(self, mems_list):
        _analyzeMems(mems_list, "VHDL")
        for s in mems_list:
            for sig in s.mem:
                if not sig._driven:
                    sig._driven = s._driven
                sig._read = s._read

    def _update_slices(self, sigs_list):
        for s in sigs_list:
            for sig in s._slicesigs:
                sig._setName("VHDL")
                if not sig._driven:
                    sig._driven = s._driven
                sig._read = s._read

    def _update_assigns(self, sigs_list):
        # Updating the assign signals
        for sig in sigs_list:
            if sig._assign and sig._assign._driven is not None:
                sig._driven = "wire"
                sig._assign._read = True

    def _check_generators(self, generator_list):
        for generator in generator_list:
            if not isinstance(generator, (GeneratorType, _Instantiator,
                                          _UserVhdlCode)):
                raise ToVHDLError(_error.ArgType, "%s" % generator)

    def _instance_args(self, instance):
        parent = instance.frame

        argcount = parent.f_code.co_argcount
        varnames = parent.f_code.co_varnames
        argnames = varnames[:argcount]

        topdict = instance.frame.f_locals

        instargs = []
        for argname in argnames:
            instargs.append(topdict[argname])

        return instargs

    def _sanity_checks(self, intf):
        # sanity checks on interface
        for port_name in intf.argnames:
            s = intf.argdict[port_name]
            if isinstance(s, _Signal):
                if s._name is None and not isinstance(s, _SliceSignal):
                    raise ToVHDLError(_error.ShadowingSignal,
                                      "%s.%s" % (intf.name, port_name))
                if s._inList is not None:
                    # raise ToVHDLError(_error.PortInList,
                    #                   "%s.%s" % (self.name, port.name))
                    pass


class vhd_slice(object):
    def __init__(self, start, stop=None):
        self.start = int(start)
        self.stop = None
        if stop is not None:
            self.stop = int(stop)

            if self.stop >= self.start:
                raise IndexError("The stop value must be always smaller than"
                                 "the start one")

    def toStr(self):
        if self.stop is None:
            return "(%d)" % self.start
        elif (self.start - 1) == self.stop:
            return "(%d)" % self.stop
        else:
            return "((%d - 1) downto %d)" % (self.start, self.stop)


class vhd_assign(object):
    def __init__(self, *args):
        l = len(args)
        if l == 2:
            self.target = args[0]
            self.source = args[1]
            self.target_slice = self.source_slice = None
        elif l == 3:
            self.target = args[0]
            self.target_slice = args[1]
            self.source = args[2]
            self.source_slice = None
        elif l == 4:
            self.target = args[0]
            self.target_slice = args[1]
            self.source = args[2]
            self.source_slice = args[3]
        else:
            raise TypeError("Only two, three or four parameters are allowed.")

    def toStr(self):
        target = self.target
        if self.target_slice is not None:
            target = "%s%s" % (target, self.target_slice.toStr())
        source = self.source
        if isinstance(source, list):
            if self.target_slice is not None or \
                    self.source_slice is not None:
                raise ToVHDLError("Slice not available in array assignment.")
            if len(source) > 1:
                lines = []
                initial_string = "%s <= (" % target
                indent_string = ' ' * len(initial_string)
                offset_string = ",\n%s" % indent_string
                for l in source:
                    lines.append("%s%s" % (initial_string, l))
                    initial_string = offset_string
                lines.append("\n%s);\n" % indent_string)
                return "".join(lines)
            else:
                return "%s <= (others => %s);" % (target, source[0])
        else:
            if self.source_slice is not None:
                source = "%s%s" % (source, self.source_slice.toStr())

            return "%s <= %s;\n" % (target, source)


class vhd_signal(object):
    def __init__(self, name, signal, vhd_type,
                 entity=None, architecture=None):
        self.name = name
        self.signal = signal
        self.vhd_type = vhd_type
        self.driven = None
        self.read = False
        self.entity = entity
        self.architecture = architecture
        self.assign = None
        self.internal = None
        self.signal_conversion = []

    @property
    def used(self):
        return self.signal._used or self.signal._read or self.signal._driven

    def _read_concat(self):
        sig = self.signal
        if sig._is_bitarray:
            ini = uintba(sig._initval, sig._nrbits)
        else:
            ini = intbv(sig._initval)[sig._nrbits:]
        hi = sig._nrbits
        for a in sig._args:
            if isinstance(a, bool):
                w = 1
            else:
                w = len(a)
            lo = hi - w
            target = sig._name
            if w == 1:
                if isinstance(a, _Signal):
                    # isinstance(a._type , bool): <- doesn't work
                    if a._type == bool:
                        target_slice = vhd_slice(lo)
                        source = a._name
                        source_slice = None
                    else:
                        target_slice = vhd_slice(lo)
                        source = a._name
                        source_slice = vhd_slice(0)
                else:
                    target_slice = vhd_slice(lo)
                    source = vhd_std_logic().literal(ini[lo])
                    source_slice = None
            else:
                if isinstance(a, _Signal):
                    target_slice = vhd_slice(hi, lo)
                    source = a._name
                    source_slice = None
                else:
                    target_slice = vhd_slice(hi, lo)
                    source = vhd_unsigned(w).literal(ini[hi:lo])
                    source_slice = None
            hi = lo
            self.signal_conversion.append(vhd_assign(target,
                                                     target_slice,
                                                     source,
                                                     source_slice))

    def _read_tristate(self):
        sig = self.signal
        for d in sig._drivers:
            if d._driven:
                self.signal_conversion.append(vhd_assign(sig._name, d._name))

    def _read_base(self):
        sig = self.signal
        if sig._driven:
            self.driven = sig._driven
        if sig._read:
            self.read = sig._read

        if isinstance(sig, _MemInfo):
            for s in self.signal.mem:
                if s._driven:
                    if self.driven == "reg":
                        self.driven = "reg"
                    else:
                        self.driven = "wire"
                if s._read:
                    self.read = s._read

            for s in self.signal.mem:
                s._driven = self.driven
                s._read = self.read

            self.internal = [s._init for s in self.signal.mem]
        else:
            self.internal = sig._init
            if sig._assign is not None:
                self.assign = sig._assign._name

        if self.driven:
            if not self.read and \
                    not isinstance(sig, _TristateDriver):
                warnings.warn("%s: %s" % (_error.UnreadSignal,
                                          self.name),
                              category=ToVHDLWarning
                              )
            if self.driven == "wire":
                if isinstance(sig, ConcatSignal):
                    self._read_concat()
                elif isinstance(sig, _TristateSignal):
                    self._read_tristate()
                elif self.assign is not None:
                    self.signal_conversion.append(vhd_assign(self.name,
                                                             self.assign))
            # the following line implements initial value assignments
            # print >> f, "%s %s%s = %s;" % (s._driven, r, s._name,
            # int(s._val))
        elif self.read:
            # the original exception
            # raise ToVHDLError(_error.UndrivenSignal, s._name)
            # changed to a warning and a continuous assignment to a wire
            warnings.warn("%s: %s" % (_error.UndrivenSignal,
                                      self.name),
                          category=ToVHDLWarning
                          )
            const_data = self.vhd_type.literal(self.internal)
            self.signal_conversion.append(vhd_assign(self.name, const_data))
            sig._driven = "reg"

    def _update(self):
        if isinstance(self.signal, _MemInfo):
            self.signal.name = self.name
            if self.driven:
                self.signal._driven = self.driven
            if self.used:
                self.signal._used = True
            if self.read:
                self.signal._read = self.read
            for idx, s in enumerate(self.signal.mem):
                s._name = "%s(%d)" % (self.name, idx)
                if self.used:
                    s._used = True
                if self.driven:
                    s._driven = self.driven
                if self.read:
                    s._read = self.read
                if not s._nrbits:
                    raise ConversionError(_error.UndefinedBitWidth, s._name)
                if not isinstance(s.val, type(self.signal.elObj.val)):
                    raise ConversionError(_error.InconsistentType, s._name)
                if s._nrbits != self.signal.elObj._nrbits:
                    raise ConversionError(_error.InconsistentBitWidth, s._name)
        else:
            self.signal._name = self.name
            if self.driven:
                self.signal._driven = self.driven
            if self.used:
                self.signal._used = True
            if self.signal._slicesigs:
                for s in self.signal._slicesigs:
                    s._setName("VHDL")


class vhd_port(vhd_signal):
    def __init__(self, name, signal, vhd_type, direction=None, entity=None):
        vhd_signal.__init__(self, name, signal, vhd_type, entity=entity)
        self.direction = direction
        self.convert = False

    def _update(self):
        if self.convert:
            name = self.convert
        else:
            name = self.name
        if isinstance(self.signal, _MemInfo):
            self.signal.name = name
            for idx, signal in enumerate(self.signal.mem):
                signal._name = "%s(%d)" % (name, idx)
                # signal._inList = self.signal
        else:
            self.signal._name = name
            if self.signal._slicesigs:
                for s in self.signal._slicesigs:
                    s._setName("VHDL")


class vhd_constant(object):
    def __init__(self, name, value, vhd_type,
                 used=False, entity=None, architecture=None):
        self.name = name
        self.value = value
        self.vhd_type = vhd_type
        self.entity = entity
        self.architecture = architecture

    @property
    def used(self):
        return self.value.used

    @used.setter
    def used(self, val):
        self.value.used = bool(val)

    def _update(self):
        self.value.name = self.name


class vhd_variable(object):
    def __init__(self, name, value, vhd_type,
                 used=False, entity=None, architecture=None, process=None):
        self.name = name
        self.value = value
        self.vhd_type = vhd_type
        self.used = used
        self.entity = entity
        self.architecture = architecture
        self.process = process


class vhd_entity(object):
    def __init__(self, name, ports_list, ports_dict, instance,
                 level=0, architecture=None):
        self.name = name
        self.basename = ''
        self.ports_list = ports_list
        self.ports_dict = ports_dict
        self.instance = instance
        self.level = level
        self.architecture = architecture

    def _update(self):
        self.architecture._update()

        for port in self.ports_dict.values():
            port._update()

    def _memory_update(self):
        mems = [m for m in [comp.entity.ports_dict.values()
                            for comp in self.architecture.components_list]
                if isinstance(m, _MemInfo)]

        return mems

    def _clean_signals(self, level=1):
        for port in self.ports_dict.values():
            port.signal._clear()

        if level > 0:
            self.architecture._clean_signals(level)


class vhd_architecture(object):
    def __init__(self, sigs_list, sigs_dict, const_dict,
                 process_list=[], components_list=[], entity=None):
        self.arch = ''
        self.sigs_list = sigs_list
        self.sigs_dict = sigs_dict
        self.const_dict = const_dict
        self.const_wires = []
        self.process_list = process_list
        self.components_list = components_list
        self.entity = entity
        self.signal_conversions = []

    def _clean_signal_names(self):
        for signal in self.sigs_dict.values():
            if isinstance(signal, _MemInfo):
                for signal in signal.mem:
                    signal._name = None
            else:
                signal.signal._name = None

    def _read_base(self):
        for s in self.sigs_dict.values():
            s._read_base()

    def _update(self):
        sorted_list = list(self.sigs_dict.values())
        sorted_list.sort(key=lambda x: not isinstance(x.signal, _MemInfo))
        for signal in sorted_list:
            signal._update()

        for const in self.const_dict.values():
            const._update()

        for component in self.components_list:
            component._update()

    def _generators(self):
        return [process.generator for process in self.process_list]

    def _clean_signals(self, level):
        for signal in self.sigs_dict.values():
            signal.signal._clear()

        for component in self.components_list:
            component._clean_signals(level)


class vhd_process(object):
    def __init__(self, vars_list, vars_dict,
                 generator=None, entity=None, architecture=None):
        self.vars_list = vars_list
        self.vars_dict = vars_dict
        self.generator = generator
        self.entity = entity
        self.architecture = architecture

    def _clean(self):
        if hasattr(self.generator, 'sigregs'):
            for signal in self.generator.sigregs:
                signal._name = None
                signal._driven = None
                signal._read = False
                if signal._inList is not None:
                    signal._inList._driven = None
                    signal._inList._read = False

        if hasattr(self.generator, 'symdict'):
            symdict = self.generator.symdict
            const_dict = self.architecture.const_dict
            for key in const_dict.keys():
                if key in symdict:
                    const_dict[key].used = True


class vhd_component(object):
    def __init__(self, name, entity, parent=None, architecture=None):
        self.name = name
        self.parent = parent
        self.entity = entity
        self.architecture = architecture
        self.ports_signals_dict = {}

    @property
    def ports_list(self):
        return self.entity.ports_list

    @property
    def ports_dict(self):
        return tuple(self.entity.ports_dict)

    def _update(self):
        for p in self.entity.ports_dict.values():
            # change name to convert to std_logic, or
            # make sure signal name is equal to its port name
            s = p.signal

            if p.direction == "in":
                s._read = True
                s._used = True
            elif p.direction == "out":
                s._driven = 'wire'
                s._used = True
            elif p.direction == "inout":
                s._driven = 'wire'
                s._read = True
                s._used = True

            if hasattr(s, '_inList') and s._inList:
                if s._read:
                    s._inList._read = s._read
                if s._driven:
                    s._inList._driven = s._driven
                if s._used:
                    s._inList._used = s._used
                for ds in s._inList.mem:
                    if s._read:
                        ds._read = s._read
                    if s._driven:
                        ds._driven = s._driven
                    if s._used:
                        ds._used = s._used

    def _get_signals(self):
        self._update()
        sigs_dict = dict([(name, self.entity.ports_dict[name].signal)
                          for name in self.entity.ports_list])
        sigs_list = self.entity.ports_list

        return sigs_list, sigs_dict

    def _clean_signals(self, level):
        self.entity._clean_signals(level - 1)


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
    Port = namedtuple('Port', ['name', 'portname', 'direction', 'convert',
                               'signal'])

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
                 "std_logic_ports",
                 "version",
                 "one_file",
                 "vhdl_files",
                 )

    def __init__(self):
        self.name = None
        self.directory = None
        self.component_declarations = None
        self.header = ''
        self.no_myhdl_header = False
        self.no_myhdl_package = False
        self.library = "work"
        self.use_clauses = None
        self.use_fixed_point = False
        self.architecture = "MyHDL"
        self.std_logic_ports = False
        self.version = 2008
        self.one_file = True
        self.vhdl_files = []

    def __call__(self, func, *args, **kwargs):
        global _converting
        if _converting:
            return func(*args, **kwargs)  # skip
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

        version = self.version

        one_file = bool(self.one_file)
        if 'oneFile' in kwargs:
            one_file = bool(kwargs.pop('oneFile'))

        if self.directory is None:
            directory = ''
            if one_file is False:
                directory = os.path.join(directory, name + "_dir")
                try:
                    os.mkdir(directory)
                except OSError as ose:
                    _converting = 0
                    raise ose
        else:
            directory = self.directory

        compDecls = self.component_declarations
        useClauses = self.use_clauses

        pname = "pck_%s_myhdl_%s.vhd" % (name, _shortversion)
        ppath = os.path.join(directory, pname)
        pfile = None
#        # write MyHDL package always during development, as it may change
#        pfile = None
#        if not os.path.isfile(ppath):
#            pfile = open(ppath, 'w')
        if not self.no_myhdl_package:
            pfile = open(ppath, 'w')

        try:
            h = _HierExtr(name, func, *args, **kwargs)
        finally:
            _converting = 0

        hier = h.hierarchy[:]
        hier.reverse()

        stdLogicPorts = self.std_logic_ports
        genHier = _GenerateHierarchy()
        hierarchy = genHier(h, stdLogicPorts)

        _enumTypeSet.clear()

        lib = self.library
        arch = self.architecture

        for entity in hierarchy.entities_list:
            entity.architecture.name = arch

        entities_files = []
        cpname = "pck_" + name

        fixed_point = hierarchy.sfixed

        sigs_list = []

        for entity in hierarchy.entities_list:
            sfile = StringIO()
            _genUniqueSuffix.reset()

            if len(entity.ports_list) == 0 and entity.level > 1:
                raise ToVHDLWarning("Entity without ports: %s" %
                                    entity.name)
            # Update the different elements to make every component behave
            # like a top function
            entity._update()

            doc = _makeDoc(inspect.getdoc(entity.instance.func))

            self._convert_filter(entity)

            gfile = StringIO()

            _writeModuleHeader(sfile, cpname, lib, useClauses,
                               version=version, fixed_point=fixed_point)
            _writeEntityHeader(sfile, entity, doc)
            _writeFuncDecls(sfile)
            _writeCompDecls(sfile, entity, lib)
            _writeUserCompDecls(sfile, compDecls)
            _writeSigDecls(sfile, entity.architecture)
            # Write to a memory buffer to ensure the constants are properly
            # managed
            _convertGens(entity.architecture, gfile)
            # Write the constans declarations.
            _writeConstants(sfile, entity.architecture)
            # Writting the processes
            sfile.write(gfile.getvalue())
            gfile.close()

            _writeCompUnits(sfile, entity)

            _writeModuleFooter(sfile, arch)

            sfile.write("\n")

            entities_files.append((entity.name, sfile.getvalue()))
            sfile.close()
            # clean-up properly #
            entity._clean_signals()

        complete_files = []

        sfile = StringIO()
        _writeCustomPackage(sfile, cpname, hierarchy, fixed_point)
        complete_files.append((cpname, sfile.getvalue()))
        sfile.close()

        complete_files.extend(entities_files)

        self.vhdl_files[:] = []

        if pfile:
            self.vhdl_files.append(ppath)

            _writeFileHeader(pfile, ppath)
            print(_package(version, fixed_point), file=pfile)
            pfile.close()

        if one_file:
            vpath = os.path.join(directory, "%s.vhd" % name)
            self.vhdl_files.append(vpath)
            with open(vpath, 'w') as vfile:
                _writeFileHeader(vfile, vpath)
                for file_name, contents in complete_files:
                    print(contents, file=vfile)
        else:
            for file_name, contents in complete_files:
                vpath = os.path.join(directory, "%s.vhd" % file_name)
                self.vhdl_files.append(vpath)
                with open(vpath, 'w') as vfile:
                    _writeFileHeader(vfile, vpath)
                    print(contents, file=vfile)

        for sig in sigs_list:
            sig._clear()

        return h.top

    def _reviseMems(self, full_mems, memlist):
        for m in memlist:
            if m.type is None:
                m.type = "t_array_%s%s" % (m.name, _genUniqueSuffix.next())

        full_mems.extend(memlist)

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
        self.std_logic_ports = False

    def _convert_filter(self, entity):
        # intended to be a entry point for other uses:
        #  code checking, optimizations, etc
        pass


toVHDL = _ToVHDLConvertor()

myhdl_header = """\
-- File: $filename
-- Generated by MyHDL-numeric $version
-- Date: $date
"""


def _writeFileHeader(f, fn):
    variables = dict(filename=fn,
                     version=__version__,
                     date=datetime.today().ctime()
                     )
    if toVHDL.header:
        print(string.Template(toVHDL.header).substitute(variables), file=f)
    if not toVHDL.no_myhdl_header:
        print(string.Template(myhdl_header).substitute(variables), file=f)
    print(file=f)


def _writeCustomPackage(f, name, hierarchy, fixed_point=False):
    print("library IEEE;", file=f)
    print("use IEEE.std_logic_1164.all;", file=f)
    print("use IEEE.numeric_std.all;", file=f)
    if fixed_point:
        print("use IEEE.fixed_float_types.all;", file=f)
        print("use IEEE.fixed_pkg.all;", file=f)
        print("use IEEE.math_real.all;", file=f)
    print(file=f)
    print("package %s is" % name, file=f)
    print(file=f)
    print("attribute enum_encoding: string;", file=f)
    print(file=f)
    if hierarchy.enum_types:
        sortedList = list(hierarchy.enum_types.values())
        sortedList.sort(key=lambda x: x._name.join(x._type._names))
        for t in sortedList:
            suf = _genUniqueSuffix.next()
            t._name = t._name + suf
        for t in sortedList:
            print("%s" % t.toStr(True), file=f)
            print(file=f)
    if hierarchy.mem_types:
        sortedList = list(hierarchy.mem_types.values())
        sortedList.sort(key=lambda x: x.toStr(False))
        for t in sortedList:
            print(file=f)
            print("%s;" % t.toStr(True), file=f)
    if hierarchy.rom_types:
        sortedList = list(hierarchy.rom_types.values())
        sortedList.sort(key=lambda x: x.toStr(False))
        for t in sortedList:
            print(file=f)
            print("%s;" % t.toStr(True), file=f)
    print(file=f)
    print("end package %s;" % name, file=f)
    print(file=f)


def _writeModuleHeader(f, pckName, lib, useClauses, version="93",
                       fixed_point=False):
    print("library IEEE;", file=f)
    print("use IEEE.std_logic_1164.all;", file=f)
    print("use IEEE.numeric_std.all;", file=f)
    if version == "93":
        print("use IEEE.standard_additions.all;", file=f)
        print("use IEEE.numeric_std_additions.all;", file=f)
    if fixed_point:
        print("use IEEE.fixed_float_types.all;", file=f)
        print("use IEEE.fixed_pkg.all;", file=f)
        print("use IEEE.math_real.all;", file=f)
    if version != "93":
        print("use std.env.all;", file=f)
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
    print("use %s.%s.all;" % (lib, pckName), file=f)
    print(file=f)


def _writeEntityHeader(f, entity, doc):
    print("entity %s is" % entity.name, file=f)
    if entity.ports_list:
        f.write("    port (")
        c = ''
        for portname in entity.ports_list:
            p = entity.ports_dict[portname]
            f.write("%s" % c)
            c = ';'
            _writePort(f, p, entity=True)
        f.write("\n    );\n")
    print("end entity %s;" % entity.name, file=f)
    print(doc, file=f)
    print(file=f)
    print("architecture %s of %s is" % (entity.architecture.name,
                                        entity.name), file=f)
    print(file=f)


def _writePort(f, port, entity=True):
    # change name to convert to std_logic, or
    # make sure signal name is equal to its port name
    if isinstance(port.vhd_type, (vhd_array, vhd_enum)):
        port_type = port.vhd_type.toStr(False)
    else:
        port_type = port.vhd_type.toStr(True)

    if port.convert:
        for sl in port.signal._slicesigs:
            sl._setName('VHDL')
        port_type = "std_logic_vector(%d downto 0)" % (port.vhd_type.size - 1)

    f.write("\n        %s: %s %s" % (port.name,
                                     port.direction,
                                     port_type))

    if port.convert and entity:
        port_conversions = port.entity.architecture.signal_conversions
        if port.direction in ("inout", "out"):
            port_conversions.append(vhd_assign(port.name,
                                               "%s(%s)" % ("std_logic_vector",
                                                           port.convert)))
            port.signal._read = True
        else:
            port_conversions.append(vhd_assign(port.convert,
                                               "%s(%s)" %
                                               (port.vhd_type.toStr(False),
                                                port.name)))
            port.signal._driven = "reg"


def _writeFuncDecls(f):
    return
    # print >> f, package


def _writeConstants(f, architecture):
    f.write("\n")
    # guess nice representation
    sorted_list = list(architecture.const_dict.values())
    sorted_list.sort(key=lambda x: x.name)

    indent_length = 4
    indent = " " * indent_length

    for c in sorted_list:
        if not c.used:
            continue
        if isinstance(c.value, _RomInfo):
            n = c.name
            t = c.vhd_type.toStr(False)
            str_rom = indent + "constant %s: %s := (" % (n, t)
            str_len = len(str_rom)
            str_indent = ',\n' + (' ' * str_len)
            for idx, v in enumerate(c.value.mem):
                f.write(str_rom)
                s = c.vhd_type.type.literal(v)
                f.write("%s => %s" % (idx, s))
                str_rom = str_indent
            f.write('\n' + (' ' * str_len) + ");\n")
        else:
            v = c.value.value
            n = c.name
            if n == '_':
                continue
            t = c.vhd_type.toStr(False)
            s = c.vhd_type.literal(v)
            f.write(indent)
            f.write("constant %s: %s := %s;\n" %
                    (n, t, s))
    f.write("\n")


def _writeTypeDefs(f):
    f.write("\n")
    sortedList = list(_enumTypeSet)
    sortedList.sort(key=lambda x: x._name)
    for t in sortedList:
        f.write("%s\n" % t._toVHDL())
    f.write("\n")


def _writeSigDecls(f, architecture):
    sorted_list = list(architecture.sigs_dict.values())
    sorted_list.sort(key=lambda s: s.name)
    for signal in sorted_list:
        if not signal.used:
            continue

        if isinstance(signal.vhd_type, (vhd_array, vhd_enum)):
            print("    signal %s: %s;" % (signal.name,
                                          signal.vhd_type.toStr(False)),
                  file=f)
        else:
            print("    signal %s: %s;" % (signal.name,
                                          signal.vhd_type.toStr(True)),
                  file=f)
        if signal.signal_conversion:
            architecture.signal_conversions.extend(signal.signal_conversion)
    print(file=f)


def _writeCompDecls(f, entity, lib):
    components_list = entity.architecture.components_list

    for component in components_list:
        f.write("    component %s" % component.name)
        f.write(" port (")
        c = ''
        for port_name in component.entity.ports_list:
            p = component.entity.ports_dict[port_name]
            f.write("%s" % c)
            c = ';'
            _writePort(f, p, False)
        f.write("\n        );\n")
        f.write("    end component;\n\n")
        f.write("    for all : %s\n"
                "        use entity %s.%s(%s);\n\n" %
                (component.name, lib, component.name,
                 component.entity.architecture.name))


def _checkPort(port):
    if isinstance(port.signal, _Signal):
        name = port.signal._name
    else:
        name = port.signal.name
    read = port.signal._read
    mem = getattr(port.signal, '_inList', False)
    if mem:
        if mem._read:
            read = mem._read
    if port.direction == "out":
        if not read:
            name = "open"
    elif port.direction == "in":
        if (not name) and (not port.signal._driven):
            const_data = port.vhd_type.literal(port.internal)
            name = "%s" % const_data[1]
    return port.name, name


def _writeCompUnits(f, entity):
    for component in entity.architecture.components_list:
        if len(component.entity.ports_list) > 0:
            f.write("    U_%s : %s\n" % (component.name.upper(),
                                         component.name))
            f.write("        port map (")
            c = ''
            for port_name in component.entity.ports_list:
                f.write(c)
                c = ",\n                  "
                name = component.ports_signals_dict[port_name]
                f.write("%s => %s" % (port_name, name))
            f.write("\n                  );\n")
            f.write('\n')


def _writeUserCompDecls(f, compDecls):
    if compDecls is not None:
        print(compDecls, file=f)


def _writeModuleFooter(f, arch):
    print("end architecture %s;" % arch, file=f)


def _convertGens(architecture, vfile):
    genlist = [process.generator for process in architecture.process_list]
    constdict = dict((const.value.orig_name, const.value)
                     for const in architecture.const_dict.values())
    blockBuf = StringIO()
    funcBuf = StringIO()
    for tree in genlist:
        if isinstance(tree, _UserVhdlCode):
            blockBuf.write(str(tree))
            continue
        tree.constdict = constdict
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
        else:  # ALWAYS_COMB
            Visitor = _ConvertAlwaysCombVisitor
        v = Visitor(tree, blockBuf, funcBuf)
        v.visit(tree)
    lines = funcBuf.getvalue()
    for line in lines.split("\n"):
        vfile.write("    %s\n" % line)
    funcBuf.close()
    print("begin", file=vfile)
    print(file=vfile)
    for assign in architecture.signal_conversions:
        print("    %s" % assign.toStr(), file=vfile)
    print(file=vfile)
    lines = blockBuf.getvalue()
    for line in lines.split("\n"):
        vfile.write("    %s\n" % line)
    blockBuf.close()


opmap = {
    ast.Add:        '+',
    ast.Sub:        '-',
    ast.Mult:       '*',
    ast.Div:        '/',
    ast.Mod:        'mod',
    ast.Pow:        '**',
    ast.LShift:     'shift_left',
    ast.RShift:     'shift_right',
    ast.BitOr:      'or',
    ast.BitAnd:     'and',
    ast.BitXor:     'xor',
    ast.FloorDiv:   '/',
    ast.Div:        '/',
    ast.Invert:     'not ',
    ast.Not:        'not ',
    ast.UAdd:       '+',
    ast.USub:       '-',
    ast.Eq:         '=',
    ast.Gt:         '>',
    ast.GtE:        '>=',
    ast.Lt:         '<',
    ast.LtE:        '<=',
    ast.NotEq:      '/=',
    ast.And:        'and',
    ast.Or:         'or',
}


class _ConvertVisitor(ast.NodeVisitor, _ConversionMixin):

    def __init__(self, tree, buf):
        self.constdict = tree.constdict
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
        for _ in range(nr):
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
            s = "%s" % float(obj)
        else:
            s = "(- %s)" % abs(float(obj))
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
                        pre, suf = "c_f2f(", ", %s, %s, %s, %s)" % \
                            (vhd.size[0], vhd.size[1],
                             vhd.overflow, vhd.rounding)
            elif isinstance(ori, vhd_unsigned):
                if vhd.trunc or ori.trunc:
                    pre, suf = "t_u2f(", ", %s, %s)" % \
                        (vhd.size[0], vhd.size[1])
                else:
                    pre, suf = "c_u2f(", ", %s, %s, %s, %s)" % \
                               (vhd.size[0], vhd.size[1], vhd.overflow, vhd.rounding)
            elif isinstance(ori, vhd_signed):
                if vhd.trunc or ori.trunc:
                    pre, suf = "t_s2f(", ", %s, %s)" % (vhd.size[0],
                                                        vhd.size[1])
                else:
                    pre, suf = "c_s2f(", ", %s, %s, %s, %s)" % \
                        (vhd.size[0], vhd.size[1], vhd.overflow, vhd.rounding)
            elif isinstance(ori, vhd_std_logic):
                pre, suf = "c_l2f(", ", %s, %s)" % (vhd.size[0],
                                                    vhd.size[1])
            elif isinstance(ori, vhd_string):
                pre, suf = "c_str2f(", ", %s, %s)" % \
                            (vhd.size[0], vhd.size[1])
            elif isinstance(ori, vhd_real):
                pre, suf = "to_sfixed(", ", %s, %s)" % (vhd.size[0],
                                                        vhd.size[1])
            else:
                pre, suf = "c_i2f(", ", %s, %s, %s, %s)" % \
                    (vhd.size[0], vhd.size[1], vhd.overflow, vhd.rounding)
        elif isinstance(vhd, vhd_boolean):
            if not isinstance(ori, vhd_boolean):
                pre, suf = "bool(", ")"
        elif isinstance(vhd, vhd_std_logic):
            if not isinstance(ori, vhd_std_logic):
                if isinstance(ori, vhd_unsigned):
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
        if n >= 2 ** 30:
            size = int(math.ceil(math.log(n + 1, 2))) + 1  # sign bit!
            self.write("%s'sd" % size)

    def writeDeclaration(self, obj, name, kind="", direction="", endchar=";",
                         constr=True):
        if isinstance(obj, EnumItemType):
            tipe = obj._type._name
        elif isinstance(obj, _Ram):
            tipe = "t_array_%s" % name
            elt = inferVhdlObj(obj.elObj).toStr(True)
            self.write("type %s is array(0 to %s) of %s;" %
                       (tipe, obj.depth - 1, elt))
            self.writeline()
        else:
            vhd = inferVhdlObj(obj)
            if isinstance(vhd, vhd_enum):
                tipe = obj._val._type._name
            else:
                tipe = vhd.toStr(constr)
        if kind:
            kind += " "
        if direction:
            direction += " "
        self.write("%s%s: %s%s%s" % (kind, name, direction, tipe, endchar))

    def writeDeclarations(self):
        if self.tree.hasPrint:
            self.writeline()
            self.write("variable print: line;")
        for name, obj in self.tree.vardict.items():
            if isinstance(obj, _loopInt):
                continue  # hack for loop vars
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
        if isinstance(node.op, ast.USub) and \
                isinstance(node.operand, ast.Num):
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
        assert node.attr == 'next', ast.dump(node)
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
                if node.obj < 0:
                    self.write("(%s)" % node.obj)
                else:
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
        if isinstance(node.value, ast.ListComp):
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
            self.write(' <= ')
            if hasattr(lhs, "id") and lhs.id in self.tree.vardict:
                msg = "Variable treated as signal (%s)" % lhs.id
                if isinstance(self.SigAss, str):
                    msg += ", or incorrect attribute used for signal (%s)" % \
                        self.SigAss
                raise ToVHDLError(msg)
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
        left, op, right = node.target, node.op, node.value
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
            pre, suf = self.inferCast(node.vhd, node.vhdOri)
            self.write(pre)
            self.write(int(val))
            self.write(suf)
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
                    self.raiseError(node, _error.UnsupportedType,
                                    "Strings with length > 1")
                else:
                    node.args[0].s = ord(node.args[0].s)
        elif f in integer_types:
            opening, closing = '', ''
            pre, suf = self.inferCast(node.vhd, node.vhdOri)
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
        elif f == intbv.signed:  # note equality comparison
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
            self.write(" * 1 ns")
            return
        elif f is concat:
            pre, suf = self.inferCast(node.vhd, node.vhdOri)
            opening, closing = "unsigned'(", ")"
            sep = " & "
        elif hasattr(node, 'tree'):
            pre, suf = self.inferCast(node.vhd, node.tree.vhd)
            fname = node.tree.name
        elif f in numeric_functions_dict:
            pre, suf = self.inferCast(node.vhd, node.vhdOri)
            fname = numeric_functions_dict[f]
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
            if not hasattr(node.tree, 'constdict'):
                node.tree.constdict = self.tree.constdict
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
        op, right = node.ops[0], node.comparators[0]
        if isinstance(op, (ast.In, ast.NotIn)):
            if isinstance(op, ast.NotIn):
                in_pre = "%s (" % opmap[ast.Not]
                in_suf = ")"
            else:
                in_pre = "("
                in_suf = ")"

            isRomInfo = False
            if isinstance(right, ast.Tuple):
                items = right.elts
            elif isinstance(right, ast.Name) and \
                    right.id in self.constdict:
                c = self.constdict[right.id]
                n = c.name
                items = c.mem
                t_pre, t_suf = self.inferCast(right.vhd.type,
                                              right.vhdOri.type)
                isRomInfo = True
            else:
                raise ToVHDLError("'in' rigth operand not valid. It "
                                  "must be a tuple: %s" %
                                  ast.dump(node))
            operand = " or"
            self.write(in_pre)
            for idx, item in enumerate(items):
                if idx + 1 >= len(items):
                    operand = ""
                self.write(pre)
                self.visit(node.left)
                self.write(" %s " % opmap[ast.Eq])
                if isRomInfo:
                    self.write(t_pre)
                    self.write("%s(%d)" % (n, idx))
                    self.write(t_suf)
                else:
                    self.visit(item)
                self.write(suf)
                self.write(operand)
                if idx + 1 < len(items):
                    self.writeline()
                    self.write("        ")
            self.write(in_suf)
        else:
            self.write(pre)
            self.visit(node.left)
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
            if abs(n) < 2 ** 31:
                self.write("to_unsigned(%d, %s)" % (n, node.vhd.size))
            else:
                self.write('unsigned\'("%s")' % bin(n, node.vhd.size))
        elif isinstance(node.vhd, vhd_signed):
            if abs(n) < 2 ** 31:
                self.write("to_signed(%d, %s)" % (n, node.vhd.size))
            else:
                self.write('signed\'("%s")' % bin(n, node.vhd.size))
        elif isinstance(node.vhd, vhd_sfixed):
            if isinstance(n, integer_types):
                if node.vhd.size[0] < 0:
                    v = "0"
                else:
                    v = bin(n, node.vhd.size[0] + 1)
                self.write('my_resize(c_str2f("%s"), %s, %s)' %
                           (v, node.vhd.size[0], node.vhd.size[1]))
            else:
                self.write('to_sfixed(%s, %s, %s)' %
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
        self.write("%s'(\"%s\")" % (typemark, str(node.s).replace('"', '""')))

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
        # propagate the node's vhd attribute
        node.body.vhd = node.orelse.vhd = node.vhd
        self.write('tern_op(')
        self.write('cond => ')
        self.visit(node.test)
        self.write(', if_true => ')
        self.visit(node.body)
        self.write(', if_false => ')
        self.visit(node.orelse)
        self.write(')')

    def visit_For(self, node):
        self.labelStack.append(node.breakLabel)
        self.labelStack.append(node.loopLabel)
        var = node.target.id
        # Take care of wildcard name '_'
        if var == '_':
            var = 'i'
            while var in self.tree.symdict:
                var += 'i'
            if "_" in self.tree.vardict:
                v = self.tree.vardict['_']
            self.tree.vardict[var] = v
        cf = node.iter
        f = self.getObj(cf.func)
        args = cf.args
        assert len(args) <= 3
        self.require(node, len(args) < 3, "explicit step not supported")
        if f is range:
            op = 'to'
            if len(args) == 1:
                start, stop, step = None, args[0], None
            elif len(args) == 2:
                start, stop, step = args[0], args[1], None
            else:
                start, stop, step = args
        else:  # downrange
            op = 'downto'
            if len(args) == 1:
                start, stop, step = args[0], None, None
            elif len(args) == 2:
                start, stop, step = args[0], args[1], None
            else:
                start, stop, step = args
        assert step is None
# #        if node.breakLabel.isActive:
# #             self.write("begin: %s" % node.breakLabel)
# #             self.writeline()
# #         if node.loopLabel.isActive:
# #             self.write("%s: " % node.loopLabel)
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
            comment = ""
            pre = "when"
            suf = " |"
            for idx, (_, item) in enumerate(test.case):
                if isinstance(item, EnumItemType):
                    itemRepr = item._toVHDL()
                elif hasattr(obj, '_nrbits'):
                    itemRepr = self.BitRepr(item, obj)
                else:
                    itemRepr = i
                if idx + 1 >= len(test.case):
                    suf = " =>%s" % comment
                self.writeline()
                self.write("%s %s%s" % (pre, itemRepr, suf))
                pre = "    "
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
        pass  # do nothing

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

    def setName(self, node):
        self.write(node.id)

    def getName(self, node):
        constdict = self.tree.constdict
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
            if isinstance(node.vhd, vhd_std_logic):
                s = "'Z'"
            else:
                if type(node.vhd.size) is tuple:
                    length = node.vhd.size[0] - node.vhd.size[1] + 1
                else:
                    length = node.vhd.size
                s = '"%s"' % ('Z' * length)
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
            if isinstance(vhd, vhd_std_logic) and \
                    isinstance(node.vhd, vhd_boolean):
                s = "(%s = '1')" % n
            else:
                s = n
        elif n in self.tree.symdict:
            obj = self.tree.symdict[n]
            s = n
            if isinstance(obj, bool):
                if n in constdict and obj == constdict[n].value:
                    if isinstance(node.vhd, vhd_std_logic):
                        s = "stdl(%s)" % int(obj)
                    else:
                        s = "bool(%s)" % int(obj)
                else:
                    if isinstance(node.vhd, vhd_std_logic):
                        s = "'%s'" % int(obj)
                    else:
                        s = "%s" % obj
            elif isinstance(obj, integer_types):
                if n in constdict and obj == constdict[n].value:
                    name = constdict[n].name
                    if isinstance(node.vhd, (vhd_int, vhd_real)):
                        if abs(obj) < 2 ** 31:
                            s = name
                            constdict[n].used = True
                        else:
                            s = self.IntRepr(obj)
                    elif isinstance(node.vhd, vhd_boolean):
                        s = "bool(%s)" % name
                        constdict[n].used = True
                    elif isinstance(node.vhd, vhd_std_logic):
                        s = "stdl(%s)" % name
                        constdict[n].used = True
                    elif isinstance(node.vhd, vhd_unsigned):
                        if abs(obj) < 2 ** 31:
                            s = "to_unsigned(%s, %s)" % (name, node.vhd.size)
                            constdict[n].used = True
                        else:
                            s = 'unsigned\'("%s")' % bin(obj, node.vhd.size)
                    elif isinstance(node.vhd, vhd_signed):
                        if abs(obj) < 2 ** 31:
                            s = "to_signed(%s, %s)" % (name, node.vhd.size)
                            constdict[n].used = True
                        else:
                            s = 'signed\'("%s")' % bin(obj, node.vhd.size)
                    elif isinstance(node.vhd, vhd_sfixed):
                        high = node.vhd.size[0]
                        if high <= 0:
                            high = 0
                        s = 'my_resize(to_sfixed(%s, %s, 0), %s, %s, %s, %s)' % \
                            (name, high,
                             node.vhd.size[0], node.vhd.size[1],
                             node.vhd.overflow, node.vhd.rounding)
                        constdict[n].used = True
                else:
                    if isinstance(node.vhd, vhd_int):
                        s = self.IntRepr(obj)
                    elif isinstance(node.vhd, vhd_boolean):
                        s = "%s" % bool(obj)
                    elif isinstance(node.vhd, vhd_std_logic):
                        s = "'%s'" % int(obj)
                    elif isinstance(node.vhd, vhd_unsigned):
                        if abs(obj) < 2 ** 31:
                            s = "to_unsigned(%s, %s)" % (obj, node.vhd.size)
                        else:
                            s = 'unsigned\'("%s")' % bin(obj, node.vhd.size)
                    elif isinstance(node.vhd, vhd_signed):
                        if abs(obj) < 2 ** 31:
                            s = "to_signed(%s, %s)" % (obj, node.vhd.size)
                        else:
                            s = 'signed\'("%s")' % bin(obj, node.vhd.size)
                    elif isinstance(node.vhd, vhd_sfixed):
                        s = "c_str2f(%s, %s, %s)" % \
                                (bin(obj, node.vhd.size[0] -
                                     node.vhd.size[1] + 1),
                                 node.vhd.size[0], node.vhd.size[1])
            elif isinstance(obj, float):
                if n in constdict and obj == constdict[n].value:
                    if isinstance(node.vhd, vhd_real):
                        s = n
                    elif isinstance(node.vhd, vhd_sfixed):
                        s = "to_sfixed(%s, %s, %s)" % (n, node.vhd.size[0],
                                                       node.vhd.size[1])
                    constdict[n].used = True
                else:
                    if isinstance(node.vhd, vhd_real):
                        s = self.RealRepr(obj)
                    elif isinstance(node.vhd, vhd_sfixed):
                        s = "to_sfixed(%s, %s, %s)" % (obj, node.vhd.size[0],
                                                       node.vhd.size[1])
            elif isinstance(obj, _Signal):
                s = str(obj)
                #ori = inferVhdlObj(obj)
                pre, suf = self.inferCast(node.vhd, node.vhdOri)
                s = "%s%s%s" % (pre, s, suf)
                obj.used = True
            elif _isMem(obj):
                m = _getMemInfo(obj)
                assert m.name
                s = m.name
                m.used = True
            elif _isRom(obj):
                m = _getRomInfo(obj)
                assert m.name
                s = m.name
                m.used = True
            elif isinstance(obj, EnumItemType):
                if n in constdict and obj == constdict[n].value:
                    s = n
                    constdict[n].used = True
                else:
                    s = obj._toVHDL()
            elif (type(obj) in class_types) and issubclass(obj, Exception):
                s = n
            else:
                self.raiseError(node, _error.UnsupportedType,
                                "%s, %s" % (n, type(obj)))
        else:
            raise ToVHDLError(_error.NotSupported, "name ref: %s" % n)
        self.write(s)

    def visit_Pass(self, node):
        self.write("null;")

    def visit_Print(self, node):
        argnr = 0
        for s in node.format:
            if isinstance(s, str):
                self.write('write(print, string\'("%s"));' % s.replace('"', '""'))
            else:
                a = node.args[argnr]
                argnr += 1
                if s.conv is int:
                    a.vhd = vhd_int()
                else:
                    # if isinstance(a.vhdOri, vhd_vector):
                    #    a.vhd = vhd_int()
                    if isinstance(a.vhdOri, vhd_std_logic):
                        a.vhd = vhd_boolean()
                    elif isinstance(a.vhdOri, vhd_enum):
                        a.vhd = vhd_string()
                self.write("write(print, ")
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
        self.write("writeline(output, print);")

    def visit_Raise(self, node):
        self.write('finish_simulation;')

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
        if isinstance(node.value.vhd, vhd_signed) and \
                isinstance(node.ctx, ast.Load) and \
                node.value.vhd.from_intbv:
            pre = pre + "unsigned("
            suf = ")" + suf
        elif isinstance(node.value.vhd, vhd_sfixed) and \
                isinstance(node.ctx, ast.Load):
            pre = pre + "slice("
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
        # assert len(node.subs) == 1
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
        assert self.context is not None
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
            bt = delay
        assert bt
        for e in senslist:
            if not isinstance(e, bt):
                self.raiseError(ifnode, "base type error in sensitivity list")
        if len(senslist) >= 2 and bt == _WaiterList:
            # ifnode = node.code.nodes[0]
            # print ifnode
            assert isinstance(ifnode, ast.If)
            asyncEdges = []
            for test, _ in ifnode.tests:
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
        singleEdge = (len(senslist) == 1) and isinstance(senslist[0],
                                                         _WaiterList)
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
            ''' reduce spelled out list items like [*name*(0), *name*(1),
            ..., *name*(n)] to just *name*'''
            r = []
            for item in senslist:
                name = item._name.split('(', 1)[0]
                if name not in r:
                    # note that the list now contains names
                    # and not Signals, but we are interested
                    # in the strings anyway ...
                    r.append(name)
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
        singleEdge = (len(senslist) == 1) and isinstance(senslist[0],
                                                         _WaiterList)
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
        if abs(init) < 2 ** 31:
            v = '%sto_%s(%d, %s)%s' % (pre, vhd_tipe, init, tipe.size, suf)
        else:
            v = '%s%s\'("%s")%s' % (pre, vhd_tipe, bin(init, tipe.size), suf)
    elif isinstance(tipe, vhd_signed):
        vhd_tipe = tipe.toStr(False)
        if abs(init) < 2 ** 31:
            v = '%sto_%s(%d, %s)%s' % (pre, vhd_tipe, init, tipe.size, suf)
        else:
            v = '%s%s\'("%s")%s' % (pre, vhd_tipe, bin(init, tipe.size), suf)
    elif isinstance(tipe, vhd_sfixed):
        vhd_tipe = tipe.toStr(False)
        high = tipe.size[0]
        low = tipe.size[1]
        v = '%sc_str2f("%s", %s, %s)%s' % (pre,
                                           bin(init.internal,
                                               tipe.size[0] -
                                               tipe.size[1] + 1),
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
            self.writeDeclaration(obj, name, direction="in", constr=False,
                                  endchar="")

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
            output_port = name in self.tree.outputs
            input_port = name in self.tree.inputs
            inout_port = input_port and output_port
            direction = (inout_port and "inout") or \
                (output_port and "out") or "in"
            self.writeline()
            self.writeDeclaration(obj, name, direction=direction,
                                  constr=False, endchar="")

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
        self._name = ''
        self.size = size
        self.trunc = False
        self.from_intbv = False

    def __str__(self):
        return self._name

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, self.size)

    def maybeNegative(self):
        return False

    def inferBinaryOpCast(self, node, left, right, op):
        pass

    def _not_implemented(self, other):
        return NotImplemented


class vhd_int(vhd_type):
    def __init__(self, size=-1):
        vhd_type.__init__(self, size)
        self._name = 'int'

    def toStr(self, constr=True):
        return "integer"

    def literal(self, value):
        limit = 1 << 31
        if value >= limit or value < -limit:
            raise ToVHDLError("Not representable integer value: %d" % value)
        s = str(int(value))
        sign = ''
        if value < 0:
            sign = '-'
        for i in range(4, 31):
            if abs(value) == 2 ** i:
                s = "%s(2**%s)" % (sign, i)
                break
            if abs(value) == 2 ** i - 1:
                s = "%s((2**%s)-1)" % (sign, i)
                break

        return s

    def _direct(self, other):
        if isinstance(other, vhd_int):
            return vhd_int()
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
    def __init__(self, size=1):
        vhd_type.__init__(self, size)
        self._name = 'nat'

    def toStr(self, constr=True):
        return "natural"

    def literal(self, value):
        limit = 1 << 32
        if value >= limit or value < 0:
            raise ToVHDLError("Not representable natural value: %d" % value)
        s = str(int(value))
        for i in range(4, 31):
            if abs(value) == 1 << i:
                s = "(2**%s)" % i
                break
            if abs(value) == (1 << i) - 1:
                s = "((2**%s)-1)" % i
                break

        return s

    def _direct(self, other):
        if isinstance(other, vhd_nat):
            return vhd_nat()
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
    def __init__(self, size=-1):
        vhd_type.__init__(self, size)
        self._name = 'real'

    def toStr(self, constr=True):
        return "real"

    def literal(self, value):
        return str(float(value))

    def _direct(self, other):
        if isinstance(other, (vhd_real, vhd_int)):
            return vhd_real()
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


class vhd_physical(vhd_type):
    def __init__(self):
        vhd_type.__init__(self)
        self._name = 'physical'

    def _direct(self, other):
        if isinstance(other, type(self)):
            return copy(self)
        else:
            return NotImplemented

    def _physical(self, other):
        if isinstance(other, (type(self), vhd_int, vhd_real)):
            return copy(self)
        else:
            return NotImplemented

    __add__ = __sub__ = __radd__ = __rsub__ = _physical
    __mul__ = __rmul__ = __floordiv__ = __truediv__ = __mod__ = _physical
    __pow__ = __rpow__ = vhd_type._not_implemented
    __rfloordiv__ = __rtruediv = __rmod__ = vhd_type._not_implemented
    __and__ = __rand__ = __or__ = __ror__ = vhd_type._not_implemented
    __xor__ = __rxor__ = vhd_type._not_implemented

    def __abs__(self):
        return copy(self)

    def __pos__(self):
        return copy(self)

    def __neg__(self):
        return copy(self)

    def __inv__(self):
        return NotImplemented

    def maybeNegative(self):
        return True


class vhd_time(vhd_physical):
    def __init__(self):
        vhd_type.__init__(self)
        self._name = "time"

    def toStr(self, constr=True):
        return "time"


class vhd_string(vhd_type):
    def __init__(self):
        vhd_type.__init__(self)
        self._name = 'string'

    pass


class vhd_enum(vhd_type):
    def __init__(self, tipe):
        vhd_type.__init__(self)
        self._type = tipe
        self._name = "enum_%s" % tipe.__dict__['_name']

    def literal(self, value):
        return str(value)

    def toStr(self, constr=True):
        if constr:
            return self._type._toVHDL()
        else:
            return self._type.__dict__['_name']


class vhd_std_logic(vhd_type):
    def __init__(self, size=0):
        vhd_type.__init__(self)
        self.size = 1
        self._name = "std_logic"

    def toStr(self, constr=True):
        return 'std_logic'

    def literal(self, value):
        if isinstance(value, (intbv, uintba)):
            value = value[0]
        s = str(int(bool(value)))

        return "'%s'" % s

    def _logical(self, other):
        if isinstance(other, (vhd_std_logic, vhd_boolean)):
            return vhd_std_logic()
        else:
            return NotImplemented

    __add__ = __sub__ = __mul__ = __floordiv__ = __truediv__ = \
        vhd_type._not_implemented
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

    def literal(self, value):
        return "'%s'" % bool(value)

    def toStr(self, constr=True):
        return 'boolean'

    def _logical(self, other):
        if isinstance(other, vhd_boolean):
            return vhd_boolean()
        else:
            return NotImplemented

    __add__ = __sub__ = __mul__ = __floordiv__ = __truediv__ = \
        vhd_type._not_implemented
    __mod__ = vhd_type._not_implemented
    __radd__ = __rsub__ = __rmul__ = __rfloordiv__ = \
        vhd_type._not_implemented
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
    def __init__(self, size=0):
        vhd_type.__init__(self, size)
        self._name = 'vector_%s' % size

    def _logical(self, other):
        if isinstance(other, vhd_int):
            result = copy(self)
        elif isinstance(other, vhd_vector):
            high = max(other.size, self.size)
            result = type(self)(high)
        else:
            return NotImplemented
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
    def __init__(self, size=0):
        vhd_type.__init__(self, size)
        self._name = 'unsigned_%s' % size

    def literal(self, value):
        return '"%s"' % bin(value, self.size)

    def toStr(self, constr=True):
        if constr:
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
            return vhd_unsigned(2 * self.size)
        elif isinstance(other, vhd_int):
            return vhd_signed(2 * self.size)
        elif isinstance(other, vhd_unsigned):
            return vhd_unsigned(self.size + other.size)
        else:
            return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, vhd_nat):
            return vhd_unsigned(2 * self.size)
        elif isinstance(other, vhd_int):
            return vhd_signed(2 * self.size)
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
        return vhd_signed(self.size + 1)


class vhd_signed(vhd_vector):
    def __init__(self, size=0):
        vhd_type.__init__(self, size)
        self._name = 'signed_%s' % size

    def literal(self, value):
        return '"%s"' % bin(value, self.size)

    def toStr(self, constr=True):
        if constr:
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
            return vhd_signed(2 * self.size)
        elif isinstance(other, vhd_signed):
            return vhd_signed(self.size + other.size)
        else:
            return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, vhd_int):
            return vhd_signed(2 * self.size)
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
    def __init__(self, size=(0, 0),
                 fixed_wrap=False, fixed_truncate=False, guard_bits=3):
        # The initial values are based on the Vhdl Fixed Point standard.
        vhd_type.__init__(self, size)
        if size[0] < 0:
            high = "n%d" % (-size[0])
        elif size[0] > 0:
            high = "p%d" % (size[0])
        else:
            high = "0"

        if size[1] < 0:
            low = "n%d" % (-size[1])
        elif size[1] > 0:
            low = "p%d" % (size[1])
        else:
            low = "0"

        self._name = "sfixed_%s_%s" % (high, low)
        self.overflow = "fixed_wrap" if fixed_wrap else "fixed_saturate"
        self.rounding = "fixed_truncate" if fixed_truncate else "fixed_round"
        self._guard_bits = guard_bits

    def literal(self, value):
        return '"%s"' % bin(sfixba(value, self.size[0] + 1,
                                   self.size[1]).scalb(-self.size[1]),
                            self.size[0] - self.size[1] + 1)

    def toStr(self, constr=True):
        if constr:
            return "sfixed(%s downto %s)" % (self.size[0], self.size[1])
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
            high = max(other.size - 1, self.size[0])
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
                elif isinstance(op, (ast.Mod, ast.FloorDiv, ast.Div)):
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
                                  "unexpected operand %s for %s" %
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


class vhd_array(object):
    def __init__(self, length, tipe):
        self._name = "t_array_%s_%s" % (length, tipe)
        self.high = length - 1
        self.type = tipe

    def literal(self, values):
        return [self.type.literal(value) for value in values]

    def toStr(self, constr=True):
        if constr:
            t = self.type
            if isinstance(t, vhd_enum):
                return "type %s is array(0 to %s) of %s" % \
                    (self._name, self.high, self.type.toStr(False))
            else:
                return "type %s is array(0 to %s) of %s" % \
                    (self._name, self.high, self.type.toStr(True))
        else:
            return self._name

    def maybeNegative(self):
        return self.type.maybeNegative()


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
    elif (isinstance(obj, _Signal) and issubclass(obj._type, bitarray)) or \
            isinstance(obj, bitarray):
        if isinstance(obj, _Signal):
            if isinstance(obj, _TristateSignal):
                obj = obj._orival
            elif isinstance(obj, _TristateDriver):
                obj = obj._sig._orival
            else:
                obj = obj._init
        if isinstance(obj, uintba):
            vhd = vhd_unsigned
        elif isinstance(obj, sintba):
            vhd = vhd_signed
        elif isinstance(obj, sfixba):
            vhd = vhd_sfixed
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
    elif isinstance(obj, (_MemInfo, _RomInfo, _Rom)):
        vhd = vhd_array
    return vhd


def inferVhdlObj(obj):
    vhd = inferVhdlClass(obj)
    if vhd is None:
        return vhd
    elif issubclass(vhd, (vhd_unsigned, vhd_signed)):
        vhd = vhd(size=len(obj))
        if (isinstance(obj, _Signal) and obj._type is intbv) or \
                isinstance(obj, intbv):
            vhd.from_intbv = True
    elif issubclass(vhd, vhd_sfixed):
        high = getattr(obj, 'high', False)
        low = getattr(obj, 'low', False)
        # vhd_sfixed represents the vhdl element, so the sizes are
        # represented in the same format.
        fixed_truncate = getattr(obj, 'rounding', fixmath.roundings.round)
        fixed_wrap = getattr(obj, 'overflow', fixmath.overflows.saturate)
        fixed_guard_bits = getattr(obj, 'guard_bits', 3)

        vhd = vhd_sfixed(size=(high - 1, low),
                         fixed_truncate=
                         fixed_truncate == fixmath.roundings.truncate,
                         fixed_wrap=
                         fixed_wrap == fixmath.overflows.wrap,
                         guard_bits=
                         fixed_guard_bits
                         )
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
    elif issubclass(vhd, vhd_array):
        vhd = vhd(obj.depth, inferVhdlObj(obj.elObj))
    else:
        raise ToVHDLError('Unknown Type: %s' % vhd)
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
        elif f == intbv.signed:  # note equality comparison
            # this comes from a getattr
            node.vhd = vhd_signed(fn.value.vhd.size)
        elif hasattr(node, 'tree'):
            v = _AnnotateTypesVisitor(node.tree)
            v.visit(node.tree)
            node.vhd = node.tree.vhd = inferVhdlObj(node.tree.returnObj)
        node.vhdOri = copy(node.vhd)

    def inferCompareType(self, left, right):
        l = left.vhd
        r = right.vhd

        # Case for the in operator
        if isinstance(r, vhd_array):
            r = r.type

        if isinstance(l, vhd_sfixed):
            if isinstance(r, vhd_signed):
                r = vhd_sfixed((r.size - 1, 0))
            elif isinstance(r, vhd_unsigned):
                r = vhd_sfixed((r.size, 0))
            elif isinstance(r, vhd_nat):
                r = vhd_int(1)
        elif isinstance(r, vhd_sfixed):
            if isinstance(l, vhd_signed):
                l = vhd_sfixed((l.size - 1, 0))
            elif isinstance(l, vhd_unsigned):
                l = vhd_sfixed((l.size, 0))
            elif isinstance(l, vhd_nat):
                l = vhd_int(1)
        elif isinstance(l, vhd_std_logic) or \
                isinstance(r, vhd_std_logic):
            l = r = vhd_std_logic()
        elif isinstance(l, vhd_unsigned) and \
                maybeNegative(r):
            l = vhd_signed(l.size + 1)
        elif maybeNegative(l) and \
                isinstance(r, vhd_unsigned):
            r = vhd_signed(r.size + 1)
        left.vhd = l
        # Case for the in operator
        if isinstance(right.vhd, vhd_array):
            right.vhd.type = r
        else:
            right.vhd = r

    def visit_Compare(self, node):
        node.vhd = vhd_boolean()
        self.generic_visit(node)
        left, right = node.left, node.comparators[0]
        if left.vhd is None:
            raise ToVHDLError("None cannot be compared: %s" % ast.dump(node))
        if isinstance(node.ops[0], (ast.In, ast.NotIn)):
            values = node.comparators[0]
            if isinstance(values, ast.Tuple):
                for right in values.elts:
                    self.inferCompareType(left, right)
                node.vhdOri = copy(node.vhd)
                return
            elif isinstance(values, ast.Name) and \
                    isinstance(values.vhdOri, vhd_array):
                right = values
            else:
                raise ToVHDLError("In is not a valid operand: %s" %
                                  ast.dump(node))
        self.inferCompareType(left, right)
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

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, (ast.LShift, ast.RShift)):
            self.inferShiftType(node)
        elif isinstance(node.op, (ast.BitAnd, ast.BitOr, ast.BitXor)):
            self.inferBitOpType(node)
            # format string
        elif isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Str):
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
        for test, _ in node.tests:
            test.vhd = vhd_boolean()

    def visit_IfExp(self, node):
        self.generic_visit(node)
        node.test.vhd = vhd_boolean()

    def visit_ListComp(self, node):
        pass  # do nothing

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
        if node.value.vhd.from_intbv and not isinstance(node.ctx, ast.Store):
            node.vhd = vhd_unsigned(lower - upper)
        else:
            if issubclass(t, vhd_sfixed):
                node.vhd = t((lower - upper - 1, 0))
            else:
                node.vhd = t(lower - upper)

        node.vhdOri = copy(node.vhd)

    def accessIndex(self, node):
        self.generic_visit(node)
        node.vhd = vhd_std_logic()  # XXX default
        node.slice.value.vhd = vhd_int()
        obj = node.value.obj
        if isinstance(obj, list):
            assert len(obj)
            node.vhd = inferVhdlObj(obj[0])
        elif isinstance(obj, _Ram):
            node.vhd = inferVhdlObj(obj.elObj)
        elif isinstance(obj, _Rom):
            node.vhd = inferVhdlObj(obj.rom[0])
        elif isinstance(obj, (intbv, bitarray)):
            node.vhd = vhd_std_logic()
        node.vhdOri = copy(node.vhd)

    def visit_UnaryOp(self, node):
        self.visit(node.operand)
        node.vhd = copy(node.operand.vhd)
        if isinstance(node.op, ast.Not):
            # postpone this optimization until initial values are written
            # if isinstance(node.operand.vhd, vhd_std_logic):
            #     node.vhd = vhd_std_logic()
            # else:
            #     node.vhd = node.operand.vhd = vhd_boolean()
            node.vhd = node.operand.vhd = vhd_boolean()
        elif isinstance(node.op, ast.USub):
            node.vhd = -node.vhd
            if node.vhd is NotImplemented:
                print(node.vhd)
                print(ast.dump(node))
        elif isinstance(node.op, ast.Invert):
            if isinstance(node.vhd, (vhd_int, vhd_real)):
                raise ToVHDLError(_error.NotSupported,
                                  "Cannot invert natural or "
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
