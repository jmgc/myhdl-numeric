#!/usr/bin/env python
#  This file is part of the myhdl library, a Python package for using
#  Python as a Hardware Description Language.
#
#  Copyright (C) 2008 Jan Decaluwe
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

#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

""" Run the intbv.signed() unit tests. """
from __future__ import absolute_import, print_function, division
import unittest
from myhdl import *
from operator import add, sub, mul, truediv, floordiv, mod, abs, neg, pos

import warnings

def binary_operations(left, right, op):

    @instance
    def math_op():

        print("Plain Operation Test")

        yield delay(10)
        # intbv with positive range, pos number, and msb not set
        # Expect the number to be returned
        result = op(left, right)
        print("left + right: ", result)
 
    return math_op


class Test(unittest.TestCase):
#     def test_PlainIntbvTestBench(self):
#         #tb_fsm = traceSignals(delayBufferTestBench)
#         #sim = Simulation(tb_fsm)
#         sim = Simulation(SignedConcat())
#         sim.run()

    def vectors(self):
        self.lefts = (uintba(9, 8),
                      sintba(10, 6),
                      sintba(-10, 8),
                      sfixba(20, 4, -4),
                      sfixba(-13, 4, -3))
        self.rights = (uintba(3, 4),
                       sintba(9, 8),
                       sintba(-10, 5),
                       sfixba(1, 4, 0),
                       sfixba(13, 8, 3))
        self.bin_ops = (add,
                        sub,
                        mul,
                        truediv,
                        floordiv,
                        mod)

    def test_BinOperations(self):
        self.vectors()

        for left in self.lefts:
            for right in self.rights:
                for op in self.bin_ops:
                    self.assertEqual(conversion.verify(binary_operations,
                                                       left, right, op), 0)
            
        
if __name__ == "__main__":
    unittest.main()
