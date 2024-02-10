from __future__ import print_function
from __future__ import division
import sys
import types
from ast import PyCF_ONLY_AST

PYPY = hasattr(sys, 'pypy_translation_info')

_identity = lambda x: x


def ast_parse(s):
    return compile(s, '<string>', 'exec', \
                   print_function.compiler_flag|division.compiler_flag|PyCF_ONLY_AST)
