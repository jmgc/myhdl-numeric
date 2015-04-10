from __future__ import print_function
from __future__ import division
import sys
import types
from ast import PyCF_ONLY_AST

PY2 = sys.version_info[0] == 2

_identity = lambda x: x
if not PY2:
    string_types = (str,)
    integer_types = (int,)
    long = int
    class_types = (type,)

    from io import StringIO
    import builtins
    
    def to_bytes(s):
        return s.encode()

    def to_str(b):
        return b.decode()
else:
    string_types = (str, unicode)
    integer_types = (int, long)
    long = long
    class_types = (type, types.ClassType)

    from cStringIO import StringIO
    import __builtin__ as builtins

    to_bytes = _identity
    to_str = _identity

def ast_parse(s):
     return compile(s, '<string>', 'exec', \
                    print_function.compiler_flag|division.compiler_flag|PyCF_ONLY_AST)
