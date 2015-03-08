MyHDL 0.9
=========

[![Documentation Status](https://readthedocs.org/projects/myhdl/badge/?version=master)](http://docs.myhdl.org/en/latest/manual)
[![Build Status](https://travis-ci.org/jandecaluwe/myhdl.svg?branch=master)](https://travis-ci.org/jandecaluwe/myhdl)

What is MyHDL?
--------------
MyHDL is a free, open-source package for using Python as a hardware
description and verification language.

To find out whether MyHDL can be useful to you, please read:

[http://www.myhdl.org/start/why.html](http://www.myhdl.org/start/why.html)

License
-------
MyHDL is available under the LGPL license.  See LICENSE.txt.

Website
-------
The project website is located at http://www.myhdl.org

Documentation
-------------
The manual is available on-line:

   http://docs.myhdl.org/en/latest/manual

What's new
----------
To find out what's new in this release, please read:

[http://docs.myhdl.org/en/latest/whatsnew/0.8.html](http://docs.myhdl.org/en/latest/whatsnew/0.8.html)

Installation
------------
If you have superuser power, you can install MyHDL as follows:

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
$PYTHONPATH.

If necessary, consult the distutils documentation in the standard
Python library if necessary for more details;
or contact me.

You can test the proper installation as follows:

```
cd myhdl/test/core
python test_all.py
```

To install co-simulation support:

Go to the directory co-simulation/<platform> for your target platform
and following the instructions in the README.txt file.

