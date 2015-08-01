from __future__ import print_function
from __future__ import division
import sys
import types
from ast import PyCF_ONLY_AST

PY2 = sys.version_info[0] == 2
PYPY = hasattr(sys, 'pypy_translation_info')

_identity = lambda x: x

if not PY2:
    string_types = (str,)
    integer_types = (int,)
    long = int
    class_types = (type,)

    from io import StringIO
    from os import set_inheritable
    import builtins
    def to_bytes(s):
        return s.encode()

    def to_str(b):
        return b.decode()

    def bit_length(b):
        return b.bit_length()
else:
    string_types = (str, unicode)
    integer_types = (int, long)
    long = long
    class_types = (type, types.ClassType)

    from cStringIO import StringIO
    import __builtin__ as builtins

    to_bytes = _identity
    to_str = _identity

    def bit_length(b):
        n = 0
        value = abs(b)
        while ((value >> n) != 0):
            n += 1
        return n

    def set_inheritable(fd, inheritable):
        # This implementation of set_inheritable is based on a code sample in
        # [PEP 0446](https://www.python.org/dev/peps/pep-0446/) and on the
        # CPython implementation of that proposal which can be browsed [here]
        # (hg.python.org/releasing/3.4/file/8671f89107c8/Modules/posixmodule.c#l11130)
        if sys.platform == "win32":
            import msvcrt
            import ctypes.windll.kernel32 as kernel32

            HANDLE_FLAG_INHERIT = 1

            if kernel32.SetHandleInformation(msvcrt.get_osfhandle(fd),
                                             HANDLE_FLAG_INHERIT,
                                             1 if inheritable else 0) == 0:
                raise IOError("Failed on HANDLE_FLAG_INHERIT")
        else:
            import fcntl

            fd_flags = fcntl.fcntl(fd, fcntl.F_GETFD)

            if inheritable:
                fd_flags &= ~fcntl.FD_CLOEXEC
            else:
                fd_flags |= fcntl.FD_CLOEXEC

            fcntl.fcntl(fd, fcntl.F_SETFD, fd_flags)

def ast_parse(s):
    return compile(s, '<string>', 'exec', \
                   print_function.compiler_flag|division.compiler_flag|PyCF_ONLY_AST)
