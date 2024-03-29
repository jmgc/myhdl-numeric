
import ast
import itertools
from types import FunctionType

from ._util import _flatten
from ._enum import EnumType
from ._Signal import SignalType
from .numeric._conversion import numeric_functions_dict, \
    numeric_attributes_dict


class Data():
    pass


def _resolveRefs(symdict, arg):
    gens = _flatten(arg)
    data = Data()
    data.symdict = symdict
    v = _AttrRefTransformer(data)
    for gen in gens:
        v.visit(gen.ast)
    return data.objlist


# TODO: Refactor this into two separate nodetransformers, since _resolveRefs
# needs only the names, not the objects


def _suffixer(name, used_names):
    lower_used_names = [used_name.lower() for used_name in used_names]
    suffixed_names = (name+'_renamed{0}'.format(i) for i in itertools.count())
    new_names = itertools.chain([name], suffixed_names)
    return next(s for s in new_names if s not in lower_used_names)


class _AttrRefTransformer(ast.NodeTransformer):
    def __init__(self, data):
        self.data = data
        self.data.objlist = []
        self.myhdl_types = (EnumType, SignalType)
        self.name_map = {}

    def visit_Attribute(self, node):
        self.generic_visit(node)

        reserved = ('next',  'posedge',  'negedge',  'max',  'min',  'val',
                    'signed')
        if node.attr in reserved:
            return node
        elif node.attr in numeric_attributes_dict:
            return node
        elif node.attr in numeric_functions_dict.values():
            return node

        # Don't handle subscripts for now.
        if not isinstance(node.value, ast.Name):
            return node

        # Don't handle locals
        if node.value.id not in self.data.symdict:
            return node

        obj = self.data.symdict[node.value.id]
        # Don't handle enums and functions, handle signals as long as it
        # is a new attribute
        if isinstance(obj, (EnumType, FunctionType)):
            return node
        elif isinstance(obj, SignalType):
            if hasattr(SignalType, node.attr):
                return node

        try:
            attrobj = getattr(obj, node.attr)
        except AttributeError as e:
            info = '\nFile "%s", line %s\n    ' % \
                   (self.data.ast.sourcefile, self.data.ast.lineoffset + node.lineno)
            raise AttributeError(info + str(e))

        orig_name = node.value.id + '.' + node.attr
        if orig_name not in self.name_map:
            base_name = node.value.id + '_' + node.attr
            self.name_map[orig_name] = _suffixer(base_name, self.data.symdict)

        new_name = self.name_map[orig_name]
        self.data.symdict[new_name] = attrobj
        self.data.objlist.append(new_name)
        new_node = ast.Name(id=new_name, ctx=node.value.ctx)

        return ast.copy_location(new_node, node)

    def visit_FunctionDef(self, node):
        nodes = _flatten(node.body, node.args)
        for n in nodes:
            self.visit(n)
        return node
