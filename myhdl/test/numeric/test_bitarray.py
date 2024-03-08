#  This file is part of the myhdl_numeric library, a Python package for using
#  Python as a Hardware Description Language. It is fully based on the
#  MyHDL test files written by Jan Decaluwe:
#
#  Copyright (C) 2015 Jase M. Gomez
#
#  The myhdl_numeric library is free software; you can redistribute it and/or
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

""" Run the bitarray unit tests. """



from sys import maxsize as maxint

import unittest
from unittest import TestCase
import random
from random import randrange
random.seed(2)  # random, but deterministic

import operator
import warnings

from myhdl import bitarray

def wrap(val, format):
    length = format._high - format._low
    mask = (1 << length) - 1
    val &= mask
    return val

class TestBitVectorInit(TestCase):
    def testDefaultValue(self):
        result = bitarray()
        self.assertEqual(result._val, 0)
        self.assertEqual(result._high, 1)
        self.assertEqual(result._low, 0)

    def testHighLow(self):
        result = bitarray(high=7, low=2)
        self.assertEqual(result._val, 0)
        self.assertEqual(result._high, 7)
        self.assertEqual(result._low, 2)

    def testIntValue(self):
        result = bitarray(9)
        self.assertEqual(result._val, 9)
        self.assertEqual(result._high, 4)
        self.assertEqual(result._low, 0)

    def testIntValueHigh(self):
        result = bitarray(34, 5)
        self.assertEqual(result._val, 34)
        self.assertEqual(result._high, 5)
        self.assertEqual(result._low, -1)

    def testIntValueLow(self):
        result = bitarray(128, low=-5)
        self.assertEqual(result._val, 128)
        self.assertEqual(result._high, 3)
        self.assertEqual(result._low, -5)

    def testIntValueHighLow(self):
        result = bitarray(93, 7, -1)
        self.assertEqual(result._val, 93)
        self.assertEqual(result._high, 7)
        self.assertEqual(result._low, -1)

    def testIntWrongHighLow(self):
        warnings.filterwarnings('error')
        self.assertRaises(RuntimeWarning, bitarray, 1023, 5, 3)
        warnings.resetwarnings()

    def testStrValue(self):
        result = bitarray("1101")
        self.assertEqual(result._val, 13)
        self.assertEqual(result._high, 4)
        self.assertEqual(result._low, 0)

    def testStrValueHigh(self):
        result = bitarray("0101", 5)
        self.assertEqual(result._val, 5)
        self.assertEqual(result._high, 5)
        self.assertEqual(result._low, 1)

    def testStrValueLow(self):
        result = bitarray("1001", low=-5)
        self.assertEqual(result._val, 9)
        self.assertEqual(result._high, -1)
        self.assertEqual(result._low, -5)

    def testStrValueHighLow(self):
        result = bitarray("11001", 7, 2)
        self.assertEqual(result._val, 25)
        self.assertEqual(result._high, 7)
        self.assertEqual(result._low, 2)

    def testStrWrongHighLow(self):
        warnings.filterwarnings('error')
        self.assertRaises(RuntimeWarning, bitarray, "11001", 5, 3)
        warnings.resetwarnings()

    def testBitVector(self):
        initial = bitarray("11001", 7, 2)
        result = bitarray(initial)
        self.assertEqual(result._val, initial._val)
        self.assertEqual(result._high, initial._high)
        self.assertEqual(result._low, initial._low)


def getItem(s, i):
    ext = '0' * (i - len(s) + 1)
    exts = ext + s
    si = len(exts) - 1 - i
    return exts[si]


def getSlice(s, i, j):
    ext = '0' * (i - len(s) + 1)
    exts = ext + s
    si = len(exts) - i
    sj = len(exts) - j
    return exts[si:sj]

def getSliceLeftOpen(s, j):
    ext = '0' * (j - len(s) + 1)
    exts = ext + s
    if j:
        return exts[:-j]
    else:
        return exts

def setItem(s, i, val):
    ext = '0' * (i - len(s) + 1)
    exts = ext + s
    si = len(exts) - 1 - i
    return exts[:si] + val + exts[si + 1:]

def setSlice(s, i, j, val):
    si = len(s) - i
    sj = len(s) - j
    return s[:si] + val + s[sj:]

def setSliceLeftOpen(s, j, val):
    ext = '0' * (j - len(s) + 1)
    exts = ext + s
    if j:
        return val + exts[-j:]
    else:
        return val

class TestBitVectorIndexing(TestCase):
    def seqsSetup(self):
        seqs = [("0", 0),
                ("1", -1),
                ("000", 1),
                ("111", -5),
                ("010001", 0),
                ("110010010", 1),
                ("011010001110010", -7)]
        seqs.extend([("0101010101", -5),
                     ("1010101010", -3),
                     ("00000000000", 0),
                     ("11111111111111", -6)])
        seqs.append(("11100101001001101000101011011101001101", -15))
        seqs.append(("00101011101001011111010100010100100101010001001", 0))
        self.seqs = seqs
        seqv = [("0", 0),
                ("1", -1),
                ("10", 1),
                ("101", -5),
                ("1111", -2),
                ("1010", 0)]
        seqv.extend([("11001", 1),
                     ("00111010", -1),
                     ("100111100", 0)])
        seqv.append(("0110101001111010101110011010011", -10))
        seqv.append(("1101101010101101010101011001101101001100110011", -15))
        self.seqv = seqv

    def testGetItem(self):
        self.seqsSetup()
        for s, low in self.seqs:
            ba = bitarray(s, len(s) + low, low)
            for i in range(len(s) + 20):
                ref = int(getItem(s, i), 2)
                idx = i + low
                try:
                    res = ba[idx]
                except IndexError:
                    assert idx >= ba.high or idx < ba.low
                else:
                    self.assertEqual(res, ref)
                    self.assertEqual(type(res), bool)

    def testGetSlice(self):
        self.seqsSetup()
        for s, low in self.seqs:
            ba = bitarray(s, len(s) + low, low)
            for i in range(low + 1, len(s) + low):
                for j in range(low, i):
                    try:
                        res = ba[i:j]
                    except ValueError:
                        self.assertTrue(i <= j)
                        continue
                    ref = getSlice(s, i - low, j - low)
                    if res.__index__() != int(ref,2):
                        res = ba[i:j]
                    self.assertEqual(res.__index__(), int(ref,2))
                    self.assertEqual(len(res), len(ref))
                    self.assertEqual(type(res), bitarray)

    def testGetSliceLeftOpen(self):
        self.seqsSetup()
        for s, low in self.seqs:
            ba = bitarray(s, low=low)
            for j in range(low, len(s) + low):
                res = ba[:j]
                ref = getSliceLeftOpen(s, j - low)
                self.assertEqual(res.__index__(), int(ref, 2))
                self.assertEqual(len(res), len(ref))
                self.assertEqual(type(res), bitarray)


    def testSetItem(self):
        warnings.filterwarnings('error')
        self.seqsSetup()
        for s, low in self.seqs:
            for it in (int, bitarray):
                for i in range(low, len(s) + low):
                    # print i
                    ba0 = bitarray(s, low=low)
                    ba1 = bitarray(s, low=low)
                    ba0[i] = it(0)
                    ba1[i] = it(1)
                    ref0 = setItem(s, i - low, '0')
                    ref1 = setItem(s, i - low, '1')
                    self.assertEqual(ba0.__index__(), int(ref0, 2))
                    self.assertEqual(ba1.__index__(), int(ref1, 2))
                    self.assertEqual(len(ba0), len(ref0))
                    self.assertEqual(len(ba1), len(ref1))
        warnings.resetwarnings()

    def testSetSlice(self):
        self.seqsSetup()
        toggle = 0
        for s, s_low in self.seqs:
            for i in range(s_low + 1, len(s) + s_low):
                for j in range(s_low, i):
                    for v, v_low in self.seqv:
                        ba = bitarray(s, low=s_low)
                        if len(v) < (i - j):
                            continue
                        s_v = v[:i - j]
                        val = s_v
                        toggle ^= 1
                        if toggle:
                            val = bitarray(s_v, low=v_low)
                        try:
                            ba[i:j] = val
                        except ValueError:
                            self.assertTrue(i <= j or len(val) != (i - j))
                            continue
                        else:
                            ref = setSlice(s, i - s_low, j - s_low, s_v)
                            if ba != ref:
                                ba[i:j] = val
                                setSlice(s, i - s_low, j - s_low, s_v)
                            self.assertEqual(ba.__index__(), int(ref, 2))
                            self.assertEqual(len(ba), len(ref))

    def testSetSliceLeftOpen(self):
        self.seqsSetup()
        toggle = 0
        for s, s_low in self.seqs:
            for j in range(s_low, len(s) + s_low):
                for v, v_low in self.seqv:
                    ba = bitarray(s, low=s_low)
                    s_v = v[:ba.high - j]
                    val = s_v
                    toggle ^= 1
                    if toggle:
                        val = bitarray(s_v, low=v_low)
                    if len(s_v) != (ba.high - j):
                        continue
                    ba[:j] = val
                    s_ref = setSliceLeftOpen(s, j - s_low, s_v)
                    ref = int(s_ref, 2)
                    self.assertEqual(ba.__index__(), ref)
                    self.assertEqual(len(ba), len(s_ref))

class TestBitVectorAsInt(TestCase):
    def seqSetup(self, imin, imax, jmin=0, jmax=None):
        seqi = [imin, imin, 12, 34]
        seqj = [jmin, 12  , jmin, 34]
        if not imax and not jmax:
            l = 2222222222222222222222222222
            seqi.append(l)
            seqj.append(l)
        # first some smaller ints
        for _ in range(100):
            ifirstmax = jfirstmax = 100000
            if imax:
                ifirstmax = min(imax, ifirstmax)
            if jmax:
                jfirstmax = min(jmax, jfirstmax)
            i = randrange(imin, ifirstmax)
            j = randrange(jmin, jfirstmax)
            seqi.append(i)
            seqj.append(j)
        # then some potentially longs
        for _ in range(100):
            if not imax:
                i = randrange(maxint) + randrange(maxint)
            else:
                i = randrange(imin, imax)
            if not jmax:
                j = randrange(maxint) + randrange(maxint)
            else:
                j = randrange(jmin, jmax)
            seqi.append(i)
            seqj.append(j)
        self.seqi = seqi
        self.seqj = seqj

    def binaryCheck(self, op, imin=0, imax=None, jmin=0, jmax=None):
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bi = bitarray(int(i), 32, -32)
            ref = op(int(i), j)
            r1 = op(bi, j)
            ref = wrap(ref, bi)
            self.assertEqual(r1.__index__(), ref)

    def augmentedAssignCheck(self, op, imin=0, imax=None, jmin=0, jmax=None):
        warnings.filterwarnings('error')
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bj = bitarray(j, 128, 0)
            ref = int(i)
            ref = op(ref, j)
            r1 = bi1 = bitarray(int(i), 128, 0)
            if op in (operator.ilshift, operator.irshift):
                r1 = op(r1, j)
            else:
                r1 = op(r1, bj)
            r2 = bi2 = bitarray(int(i), 128, 0)
            if op in (operator.ilshift, operator.irshift):
                r2 = op(r2, j)
            else:
                r2 = op(r2, bj)
            self.assertEqual(type(r1), bitarray)
            self.assertEqual(type(r2), bitarray)
            if r1._val != wrap(ref, r1):
                r1 = bi1 = bitarray(int(i), 128, 0)
                r1 = op(r1, bj)
            self.assertEqual(r1._val, wrap(ref, r1))
            self.assertEqual(r2._val, wrap(ref, r2))
            self.assertTrue(r1 is bi1)
            self.assertTrue(r2 is bi2)
        warnings.resetwarnings()

    def unaryCheck(self, op, imin=0, imax=None):
        self.seqSetup(imin=imin, imax=imax)
        for i in self.seqi:
            bi = bitarray(abs(i))
            ref = op(abs(i))
            try:
                r1 = op(bi)
            except (ValueError, TypeError):
                r1 = op(bi)
                print(i, bin(i), ref, bin(ref), r1)
                raise ValueError
            self.assertEqual(r1.__index__(), wrap(ref, r1))

    def conversionCheck(self, op, imin=0, imax=None):
        self.seqSetup(imin=imin, imax=imax)
        for i in self.seqi:
            bi = bitarray(i)
            ref = op(i)
            r1 = op(bi)
            self.assertEqual(type(r1), type(ref))
            self.assertEqual(r1, ref)

    def comparisonCheck(self, op, imin=0, imax=None, jmin=0, jmax=None):
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bi = bitarray(i)
            bj = bitarray(j)
            ref = op(i, j)
            r1 = op(bi, j)
            r2 = op(i, bj)
            r3 = op(bi, bj)
            self.assertEqual(r1, ref)
            self.assertEqual(r2, ref)
            self.assertEqual(r3, ref)

    def testAdd(self):
        self.assertRaises(TypeError, self.binaryCheck, (operator.add,))

    def testSub(self):
        self.assertRaises(TypeError, self.binaryCheck, (operator.sub,))

    def testMul(self):
        self.assertRaises(TypeError, self.binaryCheck, (operator.mul,))
        # XXX doesn't work for long i???

    def testDiv(self):
        self.assertRaises(TypeError, self.binaryCheck, (operator.truediv,))

    def testFloorDiv(self):
        self.assertRaises(TypeError, self.binaryCheck, (operator.floordiv,))

    def testMod(self):
        self.assertRaises(TypeError, self.binaryCheck, (operator.mod,))

    def testPow(self):
        self.assertRaises(TypeError, self.binaryCheck, (operator.pow,))

    def testLShift(self):
        self.binaryCheck(operator.lshift, jmax=256)

    def testRShift(self):
        self.assertRaises(TypeError, self.binaryCheck,
                          (operator.rshift,), {'jmax': 256})

    def testAnd(self):
        self.assertRaises(TypeError, self.binaryCheck,
                          (operator.and_,))

    def testOr(self):
        self.assertRaises(TypeError, self.binaryCheck,
                          (operator.or_,))

    def testXor(self):
        self.assertRaises(TypeError, self.binaryCheck, (operator.xor,))

    def testIAdd(self):
        self.assertRaises(TypeError, self.augmentedAssignCheck,
                          (operator.iadd,))

    def testISub(self):
        self.assertRaises(TypeError, self.augmentedAssignCheck,
                          (operator.isub,))

    def testIMul(self):
        self.assertRaises(TypeError, self.augmentedAssignCheck,
                          (operator.imul,))  # XXX doesn't work for long i???

    def testIFloorDiv(self):
        self.assertRaises(TypeError, self.augmentedAssignCheck,
                          (operator.ifloordiv,))

    def testIMod(self):
        self.assertRaises(TypeError, self.augmentedAssignCheck,
                          (operator.imod,))

    def testIPow(self):
        self.assertRaises(TypeError, self.augmentedAssignCheck,
                          (operator.ipow,))

    def testIAnd(self):
        self.augmentedAssignCheck(operator.iand)

    def testIOr(self):
        self.augmentedAssignCheck(operator.ior)

    def testIXor(self):
        self.augmentedAssignCheck(operator.ixor)

    def testILShift(self):
        self.augmentedAssignCheck(operator.ilshift, jmax=256)

    def testIRShift(self):
        self.augmentedAssignCheck(operator.irshift, jmax=256)

    def testNeg(self):
        self.assertRaises(TypeError, self.unaryCheck, (operator.neg,))

    def testPos(self):
        self.assertRaises(TypeError, self.unaryCheck, (operator.pos,))

    def testAbs(self):
        self.assertRaises(TypeError, self.unaryCheck, (operator.abs,))

    def testInvert(self):
        self.unaryCheck(operator.inv)

    def testInt(self):
        self.assertRaises(TypeError, self.conversionCheck, (int,))

    def testLong(self):
        self.assertRaises(TypeError, self.conversionCheck, (int,))

    def testFloat(self):
        self.assertRaises(TypeError, self.conversionCheck, (float,))

    # XXX __complex__ seems redundant ??? (complex() works as such?)

    def testOct(self):
        self.assertRaises(TypeError, self.conversionCheck, (oct,))

    def testHex(self):
        self.assertRaises(TypeError, self.conversionCheck, (hex,))

    def testLt(self):
        self.assertRaises(TypeError, self.comparisonCheck, (operator.lt,))
    def testLe(self):
        self.assertRaises(TypeError, self.comparisonCheck, (operator.le,))
    def testGt(self):
        self.assertRaises(TypeError, self.comparisonCheck, (operator.gt,))
    def testGe(self):
        self.assertRaises(TypeError, self.comparisonCheck, (operator.ge,))
    def testEq(self):
        self.assertRaises(TypeError, self.comparisonCheck, (operator.eq,))
    def testNe(self):
        self.assertRaises(TypeError, self.comparisonCheck, (operator.ne,))


class TestBitVectorBounds(TestCase):

    def testConstructor(self):
        self.assertEqual(bitarray(40).__index__(), 40)
        self.assertEqual(bitarray(25).__index__(), 25)

    def testSliceAssign(self):
        warnings.filterwarnings('error')
        a = bitarray(high=10, low=0)
        for i in (24, 2, 13, 33):
            for k in (6, 9, 10):
                a[:] = 0
                a[k:] = abs(i)
                self.assertEqual(a.__index__(), i)
        for i in (-25, -128, 34, 35, 229):
            for k in (1, 3, 4):
                a = bitarray(high=10, low=0)
                try:
                    a[k:] = abs(i)
                except RuntimeWarning:
                    self.assertTrue(abs(i) >= (1 << k))
                else:
                    self.assertEqual(wrap(abs(i), a), a)
        a = bitarray(5, 8, 0)
        for v in (0, 2 ** 8 - 1, 100):
            a[:] = v
        for v in (2 ** 8, 0, 1000):
            a = bitarray(5, 8, 0)
            try:
                a[:] = v
            except RuntimeWarning:
                    self.assertTrue(v >= (1 << 8))
            else:
                self.assertEqual(a.__index__(), wrap(v, a))

        warnings.resetwarnings()

    def checkBounds(self, i, j, op):
        warnings.filterwarnings('error')
        a = bitarray(i, 32, -32)
        self.assertEqual(a.__index__(), i)  # just to be sure
        try:
            if op in (operator.irshift, operator.ilshift):
                a = op(a, int(j))
            else:
                a = op(a, bitarray(j, 32, -32))
        except (ZeroDivisionError, ValueError):
            return  # prune
        if not isinstance(a._val, int):
            return  # prune
        b = bitarray(i, 32, -32)
        if op in (operator.irshift, operator.ilshift):
            op(b, j)
        else:
            op(b, bitarray(j, 32, -32))  # should be ok
        warnings.resetwarnings()

    def checkOp(self, op):
        for i in (0, 1, -1, 2, -2, 16, -24, 129, -234, 1025, -15660):
            for j in (0, 1, -1, 2, -2, 9, -15, 123, -312, 2340, -23144):
                self.checkBounds(abs(i), abs(j), op)

    def testIAnd(self):
        self.checkOp(operator.iand)

    def testIOr(self):
        self.checkOp(operator.ior)

    def testIXor(self):
        self.checkOp(operator.ixor)

    def testILShift(self):
        self.checkOp(operator.ilshift)

    def testIRShift(self):
        self.checkOp(operator.irshift)

class TestBitVectorBinary(TestCase):

    def seqSetup(self, imin, imax, jmin=0, jmax=None):
        seqi = [imin, imin, 12, 34]
        seqj = [jmin, 12  , jmin, 34]
        if not imax and not jmax:
            l = 2222222222222222222222222222
            seqi.append(l)
            seqj.append(l)
        # first some smaller ints
        for _ in range(100):
            ifirstmax = jfirstmax = 100000
            if imax:
                ifirstmax = min(imax, ifirstmax)
            if jmax:
                jfirstmax = min(jmax, jfirstmax)
            i = randrange(imin, ifirstmax)
            j = randrange(jmin, jfirstmax)
            seqi.append(i)
            seqj.append(j)
        # then some potentially longs
        for _ in range(100):
            if not imax:
                i = randrange(maxint) + randrange(maxint)
            else:
                i = randrange(imin, imax)
            if not jmax:
                j = randrange(maxint) + randrange(maxint)
            else:
                j = randrange(jmin, jmax)
            seqi.append(i)
            seqj.append(j)
        self.seqi = seqi
        self.seqj = seqj


class TestBitVectorCopy(TestCase):
    def testAndReduced(self):
        values = ((0, False, False, False),
                  (1, False, True, True),
                  (27, False, True, False),
                  (127, False, True, True),
                  (511, True, True, False))
        for value, and_val, or_val, xor_val in values:
            result = bitarray(value, 9, 0)
            self.assertEqual(result.and_reduce(), and_val)
            self.assertEqual(result.or_reduce(), or_val)
            self.assertEqual(result.xor_reduce(), xor_val)

if __name__ == "__main__":
    unittest.main()
