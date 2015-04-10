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
from __future__ import absolute_import, print_function
import unittest
from myhdl import *

import warnings

def PlainIntbv():
    '''Test a plain intbv instance with .signed() 

    ----+----+----+----+----+----+----+----
       -3   -2   -1    0    1    2    3

                      min  max
                           min  max
                 min       max
                 min            max
            min            max
            min       max
            min  max
          neither min nor max is set
          only max is set
          only min is set

    '''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # in the following cases the .signed() function should classify the
    # value of the intbv instance as unsigned and return the 2's
    # complement value of the bits as specified by _nrbits.
    #

    @instance
    def logic():

        print("Plain Instance Test")

        yield delay(10)
        # intbv with positive range, pos number, and msb not set
        # Expect the number to be returned
        a1 = uintba(0x3b, 8)
        b1 = sintba(a1, 8)
        print("b1: ", b1)
        assert b1 == 0x3b
 
        # intbv with positive range, pos number, and msb set, return signed()
        # test various bit patterns to see that the 2's complement
        # conversion works correct
        # Expect the number to be converted to a negative number
        a2 = uintba(7, 3)
        b2 = sintba(a2, 3)
        print("b2: ", b2)
        assert b2 == -1
  
        a3 = uintba(6, 3)
        b3 = sintba(a3, 3)
        print("b3: ", b3)
        assert b3 == -2
  
        a4 = uintba(5, 3)
        b4 = sintba(a4, 3)
        print("b4: ", b4)
        assert b4 == -3
  
        # set bit #3 and increase the range so that the set bit is considered
        # the sign bit. Here min = 0
        # Expect to return -4
        a5 = uintba(4, 3)
        b5 = sintba(a5, 3)
        print("b5: ", b5)
        assert b5 == -4
   
        # here it is not the sign bit anymore
        # Expect the value to be 4
        a6 = uintba(4, 4)
        b6 = sintba(a6, 4)
        print("b6: ", b6)
        assert b6 == 4
   
        # intbv with positive range, value = 0, return signed()
        # Expect the number to be returned
        a7 = uintba(0, 3)
        b7 = sintba(a7, 3)
        print("b7: ", b7)
        assert b7 == 0
   
   
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # in these cases the .signed() function should classify the
        # value of the intbv instance as signed and return the value as is
        #
   
   
        # set bit #3 and increase the range that the set bit is actually the
        # msb, but due to the negative range not considered signed
        # Expect to return 4
        a8 = uintba(4, 4)
        b8 = sintba(a8)
        print("b8: ", b8)
        assert b8 == 4
   
        # intbv with negative range, pos number, and msb set, return signed()
        # Expect the number to returned as is
        a9 = uintba(7, 3)
        b9 = sintba(a9)
        print("b9: ", b9)
        assert b9 == -1
  
        # intbv with symmetric (min = -max) range, neg value,
        # return signed()
        # Expect value returned as is
        a10 = sintba(-4, 3)
        b10 = uintba(a10, 4)
        print("b10: ", b10)
        assert b10 == 4

    return logic


def SlicedSigned():
    '''Test a slice with .signed()

    This test can actually be simplified, as a slice will always have
    min=0 and max > min, which will result in an intbv instance that
    will be considered unsigned by the intbv.signed() function.
    '''
    @instance
    def logic():
        b = sintba(4, 4)
        a = uintba(4, 4)
        print("SLicedSigned test")
        yield delay(10)
        b[:] = a[4:]
        assert b == 4

        b[3:0] = a[3:]
        assert b == 4
        b[4:1] = a[3:]
        assert b == -8 # msb is set with 3 bits sliced

    return logic


def SignedConcat():
    '''Test the .signed() function with the concatenate function'''

    @instance
    def logic():
        print("Signed Concat test")
        yield delay(10)
        
        # concat 3 bits
        # Expect the signed function to return a negative value
        a = uintba(0, 3)
        a[:] = concat(True, True, True)
        assert a == 7
        assert sintba(a) == -1
        assert sintba(concat(True, True, True)) == -1

        # concat a 3 bit intbv with msb set and two bits
        # Expect a negative number
        b = uintba(5, 3)
        assert sintba(concat(b, True, True)) == -9
        
    return logic

class Test(unittest.TestCase):
#     def test_PlainIntbvTestBench(self):
#         #tb_fsm = traceSignals(delayBufferTestBench)
#         #sim = Simulation(tb_fsm)
#         sim = Simulation(SignedConcat())
#         sim.run()

    def test_PlainIntbv(self):
        self.assertEqual(conversion.verify(PlainIntbv), 0)
            
    def test_SlicedSigned(self):
        self.assertEqual(conversion.verify(SlicedSigned), 0)
           
    def test_SignedConcat(self):
        self.assertEqual(conversion.verify(SignedConcat), 0)
        
if __name__ == "__main__":
    unittest.main()
