

import sys
import types
from ast import PyCF_ONLY_AST

PYPY = hasattr(sys, 'pypy_translation_info')

_identity = lambda x: x


def ast_parse(s):
    return compile(s, '<string>', 'exec', PyCF_ONLY_AST)
