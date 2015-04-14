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

""" Run the uintba unit tests. """

from __future__ import print_function, division

import sys

from myhdl._compat import long, integer_types

import unittest
from unittest import TestCase
import random
from random import randrange
random.seed(2)  # random, but deterministic
maxint = sys.maxsize
import operator
from copy import copy, deepcopy

from myhdl import uintba

import warnings


def wrap(val, format):
    length = format._high - format._low
    mask = (1 << length) - 1
    val = val.__index__()
    val &= mask
    return val

class TestUIntBaInit(TestCase):
    def testDefaultValue(self):
        self.assertEqual(uintba(), 0)


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
    ext = '0' * (i - len(s) + 1)
    exts = ext + s
    si = len(exts) - i
    sj = len(exts) - j
    return exts[:si] + val[si - sj:] + exts[sj:]


def setSliceLeftOpen(s, j, val):
    return setSlice(s, len(s), j, val)


class TestUIntBaIndexing(TestCase):

    def seqsSetup(self):
        seqs = ["0", "1", "000", "111", "010001", "110010010",
                "011010001110010"]
        seqs.extend(["0101010101", "1010101010", "00000000000",
                     "11111111111111"])
        seqs.append("11100101001001101000101011011101001101")
        seqs.append("00101011101001011111010100010100100101010001001")
        self.seqs = seqs
        seqv = ["0", "1", "10", "101", "1111", "1010"]
        seqv.extend(["11001", "00111010", "100111100"])
        seqv.append("0110101001111010101110011010011")
        seqv.append("1101101010101101010101011001101101001100110011")
        self.seqv = seqv

    def testGetItem(self):
        warnings.filterwarnings('error')
        self.seqsSetup()
        for s in self.seqs:
            n = long(s, 2)
            ba = uintba(n, 128)
            bai = ~ba
            for i in range(len(s) + 20):
                ref = long(getItem(s, i), 2)
                res = ba[i]
                resi = bai[i]
                self.assertEqual(res, ref)
                self.assertEqual(type(res), bool)
                self.assertEqual(resi, ref ^ 1)
                self.assertEqual(type(resi), bool)
        warnings.resetwarnings()

    def testGetSlice(self):
        warnings.filterwarnings('error')
        self.seqsSetup()
        for s in self.seqs:
            n = long(s, 2)
            ba = uintba(n, 128)
            bai = ~ba
            for i in range(1, len(s) + 20):
                for j in range(0, len(s) + 20):
                    try:
                        res = ba[i:j]
                        resi = bai[i:j]
                    except RuntimeWarning:
                        self.assertTrue(i <= j)
                        continue
                    ref = long(getSlice(s, i, j), 2)
                    self.assertEqual(res, ref)
                    self.assertEqual(type(res), uintba)
                    mask = (2 ** (i - j)) - 1
                    self.assertEqual(resi, ref ^ mask)
                    self.assertEqual(type(resi), uintba)
        warnings.resetwarnings()

    def testGetSliceLeftOpen(self):
        warnings.filterwarnings('error')
        self.seqsSetup()
        for s in self.seqs:
            n = long(s, 2)
            ba = uintba(n, len(s))
            bai = uintba(~n & ((1 << len(s)) - 1), len(s))
            for j in range(0, len(s)):
                res = ba[:j]
                resi = bai[:j]
                ref = long(getSliceLeftOpen(s, j), 2)
                self.assertEqual(res, ref)
                self.assertEqual(type(res), uintba)
                self.assertEqual(resi + ref, (-1) & ((1 << len(res)) - 1))
                self.assertEqual(type(res), uintba)
        warnings.resetwarnings()

    def testSetItem(self):
        warnings.filterwarnings('error')
        self.seqsSetup()
        for s in self.seqs:
            n = long(s, 2)
            for it in (int, uintba):
                for i in range(len(s) + 20):
                    # print i
                    ba0 = uintba(n, 128)
                    ba1 = uintba(n, 128)
                    ba0i = ~ba0
                    ba1i = ~ba1
                    ba0[i] = it(0)
                    ba1[i] = it(1)
                    ba0i[i] = it(0)
                    ba1i[i] = it(1)
                    ref0 = long(setItem(s, i, '0'), 2)
                    ref1 = long(setItem(s, i, '1'), 2)
                    ref0i = ~long(setItem(s, i, '1'), 2)
                    ref1i = ~long(setItem(s, i, '0'), 2)
                    self.assertEqual(ba0, ref0)
                    self.assertEqual(ba1, ref1)
                    self.assertEqual(ba0i, wrap(ref0i, ba0i))
                    self.assertEqual(ba1i, wrap(ref1i, ba1i))
        warnings.resetwarnings()

    def testSetSlice(self):
        warnings.filterwarnings('error')
        self.seqsSetup()
        toggle = 0
        for s in self.seqs:
            n = long(s, 2)
            for i in range(1, len(s) + 5):
                for j in range(0, i):
                    for v in self.seqv:
                        ext = '0' * (i - j - len(v))
                        extv = ext + v
                        ba = uintba(n, 128)
                        val = long(v, 2)
                        toggle ^= 1
                        if toggle:
                            val = uintba(val)
                        try:
                            ba[i:j] = val
                        except RuntimeWarning:
                            if isinstance(val, integer_types):
                                self.assertTrue((bit_length(val) > (i - j)) \
                                                or (bit_length(-1 - val) > \
                                                    (i - j)))
                            else:
                                self.assertTrue((len(val) != (i - j)) or \
                                                (len(-1 - val) != (i - j)))
                            continue
                        else:
                            ref = long(setSlice(s, i, j, extv), 2)
                            self.assertEqual(ba, ref)
        warnings.resetwarnings()

    def testSetSliceLeftOpen(self):
        warnings.filterwarnings('error')
        self.seqsSetup()
        toggle = 0
        for s in self.seqs:
            n = long(s, 2)
            for j in range(0, len(s)):
                for v in self.seqv:
                    ba = uintba(n, len(s))
                    bai = ~ba
                    val = long(v, 2)
                    toggle ^= 1
                    if toggle:
                        val = uintba(val)
                    try:
                        ba[:j] = val
                        bai[:j] = wrap(1 - val - 2, bai[:j])  # Workaraound for -1 - val
                    except RuntimeWarning:
                        if isinstance(val, integer_types):
                            self.assertTrue((bit_length(val) > \
                                             (len(ba) - j)) or \
                                            (bit_length(-1 - val) > \
                                             (len(bai) - j - 1)))
                        else:
                            self.assertTrue((len(val) != (len(ba) - j)) or \
                                            (len(1 - val - 2) != (len(bai) - j)))
                    else:
                        ref = long(setSliceLeftOpen(s, j, v), 2)
                        self.assertEqual(ba, wrap(ref, ba))
                        refi = ~long(setSliceLeftOpen(s, j, v), 2)
                        self.assertEqual(bai, wrap(refi, bai))
        warnings.resetwarnings()

class TestUIntBaAsInt(TestCase):

    def seqSetup(self, imin, imax, jmin=0, jmax=None):
        warnings.filterwarnings('error')
        seqi = [imin, imin, 12, 34]
        seqj = [jmin, 12, jmin, 34]
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
        warnings.resetwarnings()

    def binaryCheck(self, op, imin=0, imax=None, jmin=0, jmax=None):
        warnings.filterwarnings('error')
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bi = uintba(abs(long(i)), 128)
            bj = uintba(abs(j), 128)
            ref = op(long(i), j)
            try:
                try:
                    r1 = op(bi, j)
                    r2 = op(long(i), bj)
                    self.assertEqual(type(r1), uintba)
                    self.assertEqual(type(r2), uintba)
                    self.assertEqual(r1, wrap(ref, r1),
                                     "Different results " \
                                     "{0}, {1}, {2}".format(r1, wrap(ref, r1),
                                                         op))
                    self.assertEqual(r2, wrap(ref, r2),
                                     "Different results " \
                                     "{0}, {1}, {2}".format(r2, wrap(ref, r2),
                                                         op))
                except TypeError:
                    self.assertTrue(op in (operator.truediv,
                                           operator.pow,
                                           operator.and_, operator.or_,
                                           operator.xor))
                else:
                    r3 = op(bi, bj)
                    self.assertEqual(type(r3), uintba)
                    self.assertEqual(r3, wrap(ref, r3),
                                     "Different results " \
                                     "{0}, {1}, {2}".format(r3, wrap(ref, r3),
                                                         op))
            except TypeError:
                self.assertTrue(op in (operator.truediv, operator.itruediv,
                                       operator.pow, operator.ipow))
        warnings.resetwarnings()

    def augmentedAssignCheck(self, op, imin=0, imax=None, jmin=0, jmax=None):
        warnings.filterwarnings('error')
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bj = uintba(j, 128)
            ref = long(i)
            ref = op(ref, j)
            r1 = bi1 = uintba(long(i), 128)
            try:
                try:
                    r1 = op(r1, j)
                    r2 = long(i)
                    r2 = op(r2, bj)
                    self.assertEqual(type(r1), uintba)
                    self.assertEqual(r1, wrap(ref, r1))
                    self.assertTrue(r1 is bi1)
                    self.assertEqual(type(r2), uintba)
                    self.assertEqual(r2, wrap(ref, r2))
                except TypeError:
                    self.assertTrue(op in (operator.iand, operator.ior,
                                           operator.ixor,
                                           operator.truediv, operator.itruediv,
                                           operator.pow, operator.ipow))
                else:
                    r3 = bi3 = uintba(long(i), 128)
                    r3 = op(r3, bj)
                    self.assertEqual(type(r3), uintba)
                    self.assertEqual(r3, wrap(ref, r3))
                    self.assertTrue(r3 is bi3)
            except RuntimeWarning:
                self.assertTrue(len(r3) != len(bj))
            except TypeError:
                self.assertTrue(op in (operator.truediv, operator.itruediv,
                                    operator.pow, operator.ipow))
        warnings.resetwarnings()

    def unaryCheck(self, op, imin=0, imax=None):
        warnings.filterwarnings('error')
        self.seqSetup(imin=imin, imax=imax)
        for i in self.seqi:
            bi = uintba(abs(i))
            ref = op(abs(i))
            try:
                r1 = op(bi)
            except TypeError:
                self.assertEqual(op, operator.neg)
            else:
                self.assertEqual(type(r1), uintba)
                self.assertEqual(r1, wrap(ref, r1))
        warnings.resetwarnings()

    def conversionCheck(self, op, imin=0, imax=None):
        warnings.filterwarnings('error')
        self.seqSetup(imin=imin, imax=imax)
        for i in self.seqi:
            bi = uintba(i)
            ref = op(long(i))
            r1 = op(bi)
            self.assertEqual(type(r1), type(ref))
            self.assertEqual(r1, ref)
        warnings.resetwarnings()

    def comparisonCheck(self, op, imin=0, imax=None, jmin=0, jmax=None):
        warnings.filterwarnings('error')
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bi = uintba(i)
            bj = uintba(j)
            ref = op(i, j)
            r1 = op(bi, j)
            r2 = op(i, bj)
            r3 = op(bi, bj)
            self.assertEqual(r1, ref)
            self.assertEqual(r2, ref)
            self.assertEqual(r3, ref)
        warnings.resetwarnings()

    def testAdd(self):
        self.binaryCheck(operator.add)

    def testSub(self):
        self.binaryCheck(operator.sub)

    def testMul(self):
        self.binaryCheck(operator.mul, imax=maxint)  # XXX doesn't work for long i???

    def testDiv(self):
        self.binaryCheck(operator.truediv, jmin=1)

    def testFloorDiv(self):
        self.binaryCheck(operator.floordiv, jmin=1)

    def testMod(self):
        self.binaryCheck(operator.mod, jmin=1)

    def testPow(self):
        self.binaryCheck(operator.pow, jmax=64)

    def testLShift(self):
        self.binaryCheck(operator.lshift, jmax=256)

    def testRShift(self):
        self.binaryCheck(operator.rshift, jmax=256)

    def testAnd(self):
        self.binaryCheck(operator.and_)

    def testOr(self):
        self.binaryCheck(operator.or_)

    def testXor(self):
        self.binaryCheck(operator.xor)

    def testIAdd(self):
        self.augmentedAssignCheck(operator.iadd)

    def testISub(self):
        self.augmentedAssignCheck(operator.isub)

    def testIMul(self):
        self.augmentedAssignCheck(operator.imul, imax=maxint)  # XXX doesn't work for long i???

    def testIFloorDiv(self):
        self.augmentedAssignCheck(operator.ifloordiv, jmin=1)

    def testIMod(self):
        self.augmentedAssignCheck(operator.imod, jmin=1)

    def testIPow(self):
        self.augmentedAssignCheck(operator.ipow, jmax=64)

    def testIAnd(self):
        self.augmentedAssignCheck(operator.iand)

    def testIOr(self):
        self.augmentedAssignCheck(operator.ior)

    def testIXor(self):
        self.augmentedAssignCheck(operator.ixor)

    def testILShift(self):
        self.augmentedAssignCheck(operator.ilshift, jmax=64)

    def testIRShift(self):
        self.augmentedAssignCheck(operator.irshift, jmax=64)

    def testNeg(self):
        self.unaryCheck(operator.neg)

    def testPos(self):
        self.unaryCheck(operator.pos)

    def testAbs(self):
        self.unaryCheck(operator.abs)

    def testInvert(self):
        self.unaryCheck(operator.inv)

    def testInt(self):
        self.conversionCheck(int, imax=maxint)

    def testLong(self):
        self.conversionCheck(long)

    def testFloat(self):
        self.conversionCheck(float)

    # XXX __complex__ seems redundant ??? (complex() works as such?)

    def testOct(self):
        self.conversionCheck(oct)

    def testHex(self):
        self.conversionCheck(hex)

    def testLt(self):
        self.comparisonCheck(operator.lt)

    def testLe(self):
        self.comparisonCheck(operator.le)

    def testGt(self):
        self.comparisonCheck(operator.gt)

    def testGe(self):
        self.comparisonCheck(operator.ge)

    def testEq(self):
        self.comparisonCheck(operator.eq)

    def testNe(self):
        self.comparisonCheck(operator.ne)


class TestUIntBaBounds(TestCase):

    def testConstructor(self):
        warnings.filterwarnings('error')
        self.assertEqual(uintba(40, high=54), 40)
        self.assertEqual(uintba(25, high=16), 25)
        try:
            self.assertTrue(uintba(40, high=3) != 40)
        except RuntimeWarning:
            pass
        else:
            self.fail()
        try:
            self.assertTrue(uintba(25, high=3) != 25)
        except RuntimeWarning:
            pass
        else:
            self.fail()
        warnings.resetwarnings()

    def testSliceAssign(self):
        warnings.filterwarnings('error')
        a = uintba(high=10)
        for i in (0, 2, 13, 31):
            for k in (6, 9, 10):
                a[:] = 0
                a[k:] = i
                self.assertEqual(a, i & ((1 << len(a)) - 1))
        for i in (32, 63, 74, 116, 229):
            for k in (11, 12, 13):
                try:
                    a[k:] = i
                except IndexError:
                    pass
                else:
                    self.fail()
        a = uintba(5, 8)
        for v in (0, 2 ** 8 - 1, 100, 4096):
            try:
                a[:] = v
            except RuntimeWarning:
                self.assertTrue(bit_length(v) > len(a))
        warnings.resetwarnings()

    def checkBounds(self, i, j, op):
        warnings.filterwarnings('error')
        a = uintba(i)
        self.assertEqual(a, i)  # just to be sure
        try:
            op(a, long(j))
        except (ZeroDivisionError, RuntimeWarning):
            return  # prune
        except TypeError:
            self.assertTrue(op in (operator.iand, operator.ior,
                                   operator.ixor, operator.ipow,
                                   operator.itruediv))
        if not isinstance(a._val, integer_types):
            return  # prune
        if abs(a) > maxint * maxint:
            return  # keep it reasonable
        if a > i:
            b = uintba(i)
            for _ in (i + 1, a):
                b = uintba(i)
                b = op(b, long(j))
                self.assertEqual(b, wrap(op(i, j), b))
        elif a < i:
            b = uintba(i)
            op(b, long(j))  # should be ok
            for _ in (a + 1, i):
                b = uintba(i)
                b = op(b, long(j))
                self.assertEqual(b, wrap(op(i, j), b))
        else:  # a == i
            b = uintba(i)
            try:
                op(b, long(j))  # should be ok
            except TypeError:
                self.assertTrue(op in (operator.iand, operator.ior,
                                       operator.ixor, operator.ipow,
                                       operator.itruediv))
        warnings.resetwarnings()

    def checkOp(self, op):
        warnings.filterwarnings('error')
        for i in (0, 1, 2, 16, 129, 1025):
            for j in (0, 1, 2, 9, 123, 2340):
                self.checkBounds(i, j, op)
        warnings.resetwarnings()

    def testIAdd(self):
        self.checkOp(operator.iadd)

    def testISub(self):
        self.checkOp(operator.isub)

    def testIMul(self):
        self.checkOp(operator.imul)

    def testIFloorDiv(self):
        self.checkOp(operator.ifloordiv)

    def testIMod(self):
        self.checkOp(operator.imod)

    def testIPow(self):
        self.checkOp(operator.ipow)

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


class TestUIntBaCopy(TestCase):

    def testCopy(self):
        warnings.filterwarnings('error')
        for n in (uintba(), uintba(34), uintba(12), uintba(45),
                  uintba(23), uintba(35, 7)):
            a = uintba(n)
            b = copy(n)
            c = deepcopy(n)
            for m in (a, b, c):
                self.assertEqual(n, m)
                self.assertEqual(n._val, m._val)
                self.assertEqual(n.high, m.high)
                self.assertEqual(n.low, m.low)
                self.assertEqual(len(n), len(m))
        warnings.resetwarnings()

if __name__ == "__main__":
    unittest.main()
