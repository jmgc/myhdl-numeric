MyHDL 1.0dev 
============

[![Join the chat at https://gitter.im/jandecaluwe/myhdl](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/jandecaluwe/myhdl?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

[![Documentation Status](https://readthedocs.org/projects/myhdl/badge/?version=stable)](http://docs.myhdl.org/en/stable/manual)
[![Documentation Status](https://readthedocs.org/projects/myhdl/badge/?version=master)](http://docs.myhdl.org/en/latest/manual)
[![Build Status](https://travis-ci.org/jmgc/myhdl-numeric.svg?branch=numeric)](https://travis-ci.org/jmgc/myhdl-numeric)

What is MyHDL-numeric?
----------------------

MyHDL-numeric is an enhancement of the [MyHDL](http://www.myhdl.org)
package which provides support for **multiple VHDL entities**
([MEP110](http://dev.myhdl.org/meps/mep-110.html))
and **fixed-point numbers** ([MEP111](http://dev.myhdl.org/meps/mep-111.html)).

The **fixed-point numbers** are based on the bit-array class, that
provides support for three new types: ``sintba`` (signed integer), ``uintba``
(unsigned integer) and ``sfixba`` (signed fixed point).

Presently it only supports these new types on VHDL, and makes use of the
IEEE fixed_pkg available on VHDL-2008. If this version is not available,
it can also make use of the proposed implementation available for VHDL-93.
You can find the sources under the ``vhdl`` directory. The implementation
also takes into account the correction presented in
[DOI: 10.13140/RG.2.2.33860.42884](https://dx.doi.org/10.13140/RG.2.2.33860.42884).

An example of the numeric enhancement can be found under the directory
``example/cordic``.

License
-------
MyHDL is available under the LGPL license.  See ``LICENSE.txt``.

Installation
------------
If you have superuser power, you can install MyHDL-numeric as follows:

```
python setup.py install
```

This will install the package in the appropriate site-wide Python
package location.

Otherwise, you can install it in a personal directory, e.g. as
follows:

```
python setup.py install --home=$HOME
```

In this case, be sure to add the appropriate install dir to the
``$PYTHONPATH``.

If necessary, consult the distutils documentation in the standard
Python library if necessary for more details;
or contact me.

You can test the proper installation as follows:

```
cd myhdl/test/core
py.test
```

To install co-simulation support:

Go to the directory ``cosimulation/<platform>`` for your target platform
and following the instructions in the ``README.txt`` file.
