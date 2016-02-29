""" myhdl's distribution and installation script. """

from __future__ import print_function
import ast
import fnmatch
import re
import os
import sys

from collections import defaultdict

if sys.version_info < (2, 6) or (3, 0) <= sys.version_info < (3, 4):
    raise RuntimeError("Python version 2.6, 2.7 or >= 3.4 required.")


# Prefer setuptools over distutils
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('myhdl/_version.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

data_root = 'share/myhdl'
cosim_data = defaultdict(list)
for base, dir, files in os.walk('cosimulation'):
    for pat in ('*.c', 'Makefile*', '*.py', '*.v', '*.txt'):
        good = fnmatch.filter(files, pat)
        if good:
            cosim_data[base].extend(os.path.join(base, f) for f in good)

setup(
    name="myhdl-numeric",
    version=version,
    description="MyHDL including fixed point functionality",
    long_description="See home page.",
    author="Jose M. Gomez",
    author_email="chemoki@gmail.com",
    url="https://github.com/jmgc/myhdl-numeric",
      packages=['myhdl', 'myhdl.conversion', 'myhdl.numeric'],
    data_files=[(os.path.join(data_root, k), v) for k, v in cosim_data.items()],
    license="LGPL",
    platforms='any',
    keywords="HDL ASIC FPGA hardware design",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)',
        'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ]
)
