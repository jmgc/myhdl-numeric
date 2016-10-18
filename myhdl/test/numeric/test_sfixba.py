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

""" Run the sfixba unit tests. """

from __future__ import print_function, division

import sys

from myhdl._compat import long, integer_types, bit_length

import unittest
from unittest import TestCase
import operator
from copy import copy, deepcopy

from myhdl import sfixba, fixmath
from myhdl import sintba
from math import floor, fmod, ldexp
from decimal import Decimal, ROUND_HALF_EVEN

import warnings
import random
from random import randrange

random.seed(2)  # random, but deterministic
maxint = sys.maxsize


def truediv_round(value, value_format):
    if value < 0:
        neg = True
        tmp = -value
    else:
        neg = False
        tmp = value

    tmp = ldexp(floor(ldexp(tmp, -value_format.low + value_format.guard_bits)),
                -value_format.guard_bits)
    str_tmp = '{0:.4f}'.format(tmp)
    d = Decimal(str_tmp).quantize(0, rounding=ROUND_HALF_EVEN)
    tmp = ldexp(float(d), value_format.low)
    if neg:
        return -tmp
    else:
        return tmp


def resize(value, value_format):
    val = float(value)
    lim = ldexp(1.0, value_format.high - 1)
    margin = ldexp(1.0, value_format.high)

    rounding = False

    if value_format.overflow == fixmath.overflows.saturate:
        if val >= lim:
            val = lim - ldexp(1.0, value_format.low)
        elif val < -lim:
            val = -lim
        else:
            rounding = True
    elif value_format.overflow == fixmath.overflows.wrap:
        if val < -lim or val >= lim:
            val = fmod(val, margin)
        if val < -lim:
            val += margin
        elif val > lim:
            val -= margin
        rounding = True

    if rounding and value_format.rounding == fixmath.roundings.round:
        tmp = ldexp(val, -value_format.low)
        str_tmp = '{0:.4f}'.format(tmp)
        d = Decimal(str_tmp).quantize(0, rounding=ROUND_HALF_EVEN)
        rtmp = float(d)
        #if (rtmp == 0.0) and tmp < 0 and tmp > -0.25:
        #    val = ldexp(-1.0, value_format.low)
        #else:
        #    val = ldexp(rtmp, value_format.low)
        val = ldexp(rtmp, value_format.low)
    elif value_format.rounding == fixmath.roundings.truncate:
        tmp = ldexp(val, -value_format.low)
        tmp = float(floor(tmp))
        val = ldexp(tmp, value_format.low)

    if isinstance(value, integer_types):
        return long(val)
    else:
        return val


def wrap(val, value_format):
    length = value_format._high - value_format._low
    lim = long(1) << (length - 1)
    if val & lim:
        tmp = long(-1)
    else:
        tmp = long(0)
    wrap = lim - 1
    val &= wrap
    tmp &= ~wrap
    return tmp | val


class TestSFixBaInit(TestCase):
    def testDefaultValue(self):
        warnings.filterwarnings('error')
        value = sfixba()
        self.assertEqual(value.internal, 0, "Wrong value")
        self.assertEqual(value.high, 1, "Wrong high value")
        self.assertEqual(value.low, 0, "Wrong low value")
        self.assertEqual(value.max, 1, "Wrong maximum value")
        self.assertEqual(value.min, -1, "Wrong minimum value")
        self.assertEqual(str(value), ".", "Wrong binary string")

    def testPIntValue(self):
        warnings.filterwarnings('error')
        value = sfixba(5)
        self.assertEqual(value, 5)
        self.assertEqual(value.high, 4, "Wrong high value")
        self.assertEqual(value.low, 0, "Wrong low value")
        self.assertEqual(value.max, 8, "Wrong maximum value")
        self.assertEqual(value.min, -8, "Wrong minimum value")
        self.assertEqual(str(value), "0101", "Wrong binary string "
                         "high={0}, low={1}".format(value.high, value.low))

    def testMIntValue(self):
        warnings.filterwarnings('error')
        value = sfixba(-5)
        self.assertEqual(value, -5)
        self.assertEqual(value.high, 4, "Wrong high value")
        self.assertEqual(value.low, 0, "Wrong low value")
        self.assertEqual(value.max, 8, "Wrong maximum value")
        self.assertEqual(value.min, -8, "Wrong minimum value")
        self.assertEqual(str(value), "1011", "Wrong binary string "
                         "high={0}, low={1}".format(value.high, value.low))

    def testIntPLowValue(self):
        warnings.filterwarnings('error')
        value = sfixba(17, low=3)
        self.assertEqual(value.internal, 2)
        self.assertEqual(value.high, 9, "Wrong high value")
        self.assertEqual(value.low, 3, "Wrong low value")
        self.assertEqual(value.max, 32, "Wrong maximum value")
        self.assertEqual(value.min, -32, "Wrong minimum value")
        self.assertEqual(str(value), "000010", "Wrong binary string")

    def testIntSLowValue(self):
        warnings.filterwarnings('error')
        value = sfixba(-17).scalb(-3)
        self.assertEqual(value.internal, -17)
        self.assertEqual(value.high, 3, "Wrong high value")
        self.assertEqual(value.low, -3, "Wrong low value")
        self.assertEqual(value.max, 32, "Wrong maximum value")
        self.assertEqual(value.min, -32, "Wrong minimum value")
        self.assertEqual(int(value), -(17 >> 3))
        self.assertEqual(float(value), -17/8.)

    def testIntPHighValue(self):
        warnings.filterwarnings('error')
        value = sfixba(17, high=9).resize(9, 3)
        self.assertEqual(value.internal, 2)
        self.assertEqual(value.high, 9, "Wrong high value")
        self.assertEqual(value.low, 3, "Wrong low value")
        self.assertEqual(value.max, 32, "Wrong maximum value")
        self.assertEqual(value.min, -32, "Wrong minimum value")
        self.assertEqual(value, 16)

    def testIntSHighValue(self):
        warnings.filterwarnings('error')
        value = sfixba(-17, high=7).scalb(-3)
        self.assertEqual(value.internal, -17)
        self.assertEqual(value.high, 4, "Wrong high value")
        self.assertEqual(value.low, -3, "Wrong low value")
        self.assertEqual(value.max, 64, "Wrong maximum value")
        self.assertEqual(value.min, -64, "Wrong minimum value")

    def testIntHighLowValue(self):
        warnings.filterwarnings('error')
        value = sfixba(17, high=12, low=0).scalb(3)
        self.assertEqual(value.internal, 17)
        self.assertEqual(value.high, 15, "Wrong high value")
        self.assertEqual(value.low, 3, "Wrong low value")
        self.assertEqual(value.max, 2048, "Wrong maximum value")
        self.assertEqual(value.min, -2048, "Wrong minimum value")

    def testIntOverflow(self):
        warnings.filterwarnings('error')
        self.assertRaises(RuntimeWarning, sfixba, -17, high=1, low=-3)

    def testFloatValue(self):
        warnings.filterwarnings('error')
        value = sfixba(0.0)
        self.assertEqual(value._val, 0, "Wrong value")
        self.assertEqual(value.high, 1, "Wrong high value")
        self.assertEqual(value.low, 0, "Wrong low value")
        self.assertEqual(value.max, 1, "Wrong maximum value")
        self.assertEqual(value.min, -1, "Wrong minimum value")

    def testNFloatValue(self):
        warnings.filterwarnings('error')
        value = sfixba(-0.333984375)
        self.assertEqual(value._val, -171, "Wrong value %d" % value._val)
        self.assertEqual(value.high, 0, "Wrong high value %d" % value.high)
        self.assertEqual(value.low, -9, "Wrong low value %d" % value.low)
        self.assertEqual(value.max, 256, "Wrong maximum value %d" % value.max)
        self.assertEqual(value.min, -256, "Wrong minimum value %d" % value.min)
        self.assertEqual(float(value), -0.333984375, "Wrong minimum value %d" %
                         float(value))

    def testFloatPInfValue(self):
        warnings.filterwarnings('error')
        value = sfixba(float('inf'))
        self.assertEqual(value._val, 1, "Wrong value %d" % value._val)
        self.assertEqual(value.high, 1, "Wrong high value %d" % value.high)
        self.assertEqual(value.low, -1, "Wrong low value %d" % value.low)
        self.assertEqual(value.max, 2, "Wrong maximum value %d" % value.max)
        self.assertEqual(value.min, -2, "Wrong minimum value %d" % value.min)

    def testFloatNInfValue(self):
        warnings.filterwarnings('error')
        value = sfixba(-float('inf'))
        self.assertEqual(value._val, -2, "Wrong value %d" % value._val)
        self.assertEqual(value.high, 1, "Wrong high value %d" % value.high)
        self.assertEqual(value.low, -1, "Wrong low value %d" % value.low)
        self.assertEqual(value.max, 2, "Wrong maximum value %d" % value.max)
        self.assertEqual(value.min, -2, "Wrong minimum value %d" % value.min)

    def testFloatPInfValueMargin(self):
        warnings.filterwarnings('error')
        value = sfixba(float('inf'), 3, -5)
        self.assertEqual(value._val, 127, "Wrong value %d" % value._val)
        self.assertEqual(value.high, 3, "Wrong high value %d" % value.high)
        self.assertEqual(value.low, -5, "Wrong low value %d" % value.low)
        self.assertEqual(value.max, 128, "Wrong maximum value %d" % value.max)
        self.assertEqual(value.min, -128, "Wrong minimum value %d" % value.min)

    def testFloatNInfValueMargin(self):
        warnings.filterwarnings('error')
        value = sfixba(-float('inf'), 7, -8)
        self.assertEqual(value._val, -16384, "Wrong value %d" % value._val)
        self.assertEqual(value.high, 7, "Wrong high value %d" % value.high)
        self.assertEqual(value.low, -8, "Wrong low value %d" % value.low)
        self.assertEqual(value.max, 16384,
                         "Wrong maximum value %d" % value.max)
        self.assertEqual(value.min, -16384,
                         "Wrong minimum value %d" % value.min)

    def testPFloatValue(self):
        warnings.filterwarnings('error')
        value = sfixba(5.)
        self.assertEqual(value, 5)
        self.assertEqual(value.high, 4, "Wrong high value")
        self.assertEqual(value.low, 0, "Wrong low value")
        self.assertEqual(value.max, 8, "Wrong maximum value")
        self.assertEqual(value.min, -8, "Wrong minimum value")

    def testMFloatValue(self):
        warnings.filterwarnings('error')
        value = sfixba(-5.)
        self.assertEqual(value.internal, -5)
        self.assertEqual(value.high, 4, "Wrong high value")
        self.assertEqual(value.low, 0, "Wrong low value")
        self.assertEqual(value.max, 8, "Wrong maximum value")
        self.assertEqual(value.min, -8, "Wrong minimum value")
        self.assertEqual(float(value), -5.)

    def testLargeFloatValue(self):
        warnings.filterwarnings('error')
        f = 2.**.5
        i_f = 6369051672525773
        result = "010110101000001001111001100110011111110011101111001101"
        cases = (-6, -5, 0, 50, 56, 57, 0)
        f_values = [f * (2 ** i) for i in cases]
        f_values[-1] = -f
        i_values = [i_f for _ in cases]
        i_values[-1] = -i_f
        b_check = ("+0b" + '.' + '00000' + result[1:],
                   "+0b" + '.' + '0000' + result[1:],
                   "+0b" + result[1:2] + '.' + result[2:],
                   "+0b" + result[1:52] + '.' + result[52:],
                   "+0b" + result[1:] + '0000.',
                   "+0b" + result[1:] + '00000.',
                   "-0b" + result[1:2] + '.' + result[2:])
        h_check = ("+0x.05a827999fcef34",
                   "+0x.0b504f333f9de68",
                   "+0x1.6a09e667f3bcd",
                   "+0x5a827999fcef3.4",
                   "+0x16a09e667f3bcd0.",
                   "+0x2d413cccfe779a0.",
                   "-0x1.6a09e667f3bcd")
        for i, f_value, i_value, b, h in zip(cases, f_values, i_values,
                                             b_check, h_check):
            value = sfixba(f_value)
            self.assertEqual(value.internal, i_value)
            self.assertEqual(value.high, 2 + i, "Wrong high value")
            self.assertEqual(value.low, -52 + i, "Wrong low value")
            self.assertEqual(value.max, 9007199254740992,
                             "Wrong maximum value")
            self.assertEqual(value.min, -9007199254740992,
                             "Wrong minimum value")
            self.assertEqual(value.bin(), b,
                             "Wrong binary string, {0}".format(i))
            self.assertEqual(value.hex(), h,
                             "Wrong hex string")
            self.assertEqual(float(value), f_value)
            for j in range(value.low, value.high):
                for k in range(value.low, j - 1):
                    data = value.resize(j, k)
                    check = resize(f_value, data)
                    if float(data) != check:
                        check = resize(f_value, data)
                    self.assertEqual(float(data), check, "value: {0}, "
                                     "fix: {1}, float(fix): {2}, float: {3}, "
                                     "high:{4}, low: {5}".format(f_value,
                                                                 data,
                                                                 float(data),
                                                                 check, j, k))

    def testResize(self):
        for delta in range(-5, 0):
            for i in range(0, 8):
                for j in range(delta, i-1):
                    for k in range(-128, 128):
                        f_value = ldexp(k, delta)
                        value = sfixba(k).scalb(delta)

                        data = value.resize(i, j)
                        check = resize(f_value, data)
                        self.assertEqual(data, check, "integer: {0}, "
                                         "delta: {1}, i: {2}, "
                                         "j: {3}, data: {4}, "
                                         "float: {5}".format(k, delta, i,
                                                             j,
                                                             data,
                                                             check))

    def testFloatPLowValue(self):
        warnings.filterwarnings('error')
        f_value = 17.0
        low = 3
        value = sfixba(f_value, low=low)
        i_value = int(round(f_value*(2.0 ** -low)))
        self.assertEqual(value.internal,  i_value,
                         "Wrong value {0}, {1}".format(value, i_value))
        self.assertEqual(value.high, 6, "Wrong high value")
        self.assertEqual(value.low, 3, "Wrong low value")
        self.assertEqual(value.max, 4, "Wrong maximum value")
        self.assertEqual(value.min, -4, "Wrong minimum value")
        self.assertEqual(str(value), "010", "Wrong binary string")
        self.assertEqual(value.hex(), "+0x10.", "Wrong hexadecimal string")

    def testFloatSLowValue(self):
        warnings.filterwarnings('error')
        value = sfixba(-17., low=-3)
        self.assertEqual(value.internal, (-17) << 3)
        self.assertEqual(value.high, 6, "Wrong high value")
        self.assertEqual(value.low, -3, "Wrong low value")
        self.assertEqual(value.max, 256, "Wrong maximum value")
        self.assertEqual(value.min, -256, "Wrong minimum value")

    def testFloatRoundingValue(self):
        warnings.filterwarnings('error')
        for guard_bits in range(1, 6):
            step = 5 ** guard_bits
            scale = 10 ** guard_bits
            maths = fixmath(rounding=fixmath.roundings.round,
                            guard_bits=guard_bits)
            for i in range(-10 * scale, 10 * scale, step):
                f = i/float(scale)
                value = sfixba(f, high=7, low=0, maths=maths)
                check = resize(f, value)
                self.assertEqual(value, check,
                                 "Incorrect rounding: "
                                 "{0}, {1}, {2}, {3}".format(f, check.hex(),
                                                             value.hex(),
                                                             guard_bits))
                self.assertEqual(value.high, 7, "Wrong high value")
                self.assertEqual(value.low, 0, "Wrong low value")
                self.assertEqual(value.max, 64, "Wrong maximum value")
                self.assertEqual(value.min, -64, "Wrong minimum value")

    def testSFixBaRoundingValue(self):
        warnings.filterwarnings('error')
        maths = fixmath(rounding=fixmath.roundings.round)
        for i in range(-2000, 2000, 125):
            f = i/1000.
            f_value = sfixba(f, high=7, low=-8)
            value = sfixba(f_value, high=7, low=0, maths=maths)
            check = f_value.resize(value)
            self.assertEqual(value, check,
                             "Incorrect rounding: " \
                             "{0}, {1}, {2}".format(f, check.hex(),
                                                 value.hex()))
            self.assertEqual(value.high, 7, "Wrong high value")
            self.assertEqual(value.low, 0, "Wrong low value")
            self.assertEqual(value.max, 64, "Wrong maximum value")
            self.assertEqual(value.min, -64, "Wrong minimum value")

    def testFloatTruncateValue(self):
        warnings.filterwarnings('error')
        maths = fixmath(rounding=fixmath.roundings.truncate)
        for i in range(-2000, 2000):
            f = (int((i/1000.)*8)/8.)
            value = sfixba(f, high=7, low=0, maths=maths)
            check = int(ldexp(f, 4)) >> 4
            if value != check:
                value = sfixba(f, high=7, low=0, maths=maths)
            self.assertEqual(value, check,
                             "Incorrect truncate: {0}, {1}, {2}"
                             .format(f.hex(), hex(check), value.hex()))
            self.assertEqual(value.high, 7, "Wrong high value")
            self.assertEqual(value.low, 0, "Wrong low value")
            self.assertEqual(value.max, 64, "Wrong maximum value")
            self.assertEqual(value.min, -64, "Wrong minimum value")

    def testFloatSaturateValue(self):
        warnings.filterwarnings('error')
        for i in range(-100, 100):
            f = float(i)
            value = sfixba(f, high=5, low=0,
                           maths=fixmath(overflow=fixmath.overflows.saturate))
            if i > 15.:
                r = 15
            elif i <= -16.:
                r = -16
            else:
                r = i
            self.assertEqual(value, r,
                             "Incorrect saturation: "
                             "sat({0})={1}, {2}".format(i, r, value.hex()))
            self.assertEqual(value.high, 5, "Wrong high value")
            self.assertEqual(value.low, 0, "Wrong low value")
            self.assertEqual(value.max, 16, "Wrong maximum value")
            self.assertEqual(value.min, -16, "Wrong minimum value")

    def testBitVectorSaturateValue(self):
        warnings.filterwarnings('error')
        for i in range(-100, 100):
            f = float(i)
            f_value = sfixba(f, high=9, low=0)
            value = sfixba(f_value, high=5, low=0,
                           maths=fixmath(overflow=fixmath.overflows.saturate))
            if i > 15.:
                r = 15
            elif i <= -16.:
                r = -16
            else:
                r = i

            self.assertEqual(value, r,
                             "Incorrect saturation: "
                             "sat({0})={1}, {2}".format(i, r, value.hex()))
            self.assertEqual(value.high, 5, "Wrong high value")
            self.assertEqual(value.low, 0, "Wrong low value")
            self.assertEqual(value.max, 16, "Wrong maximum value")
            self.assertEqual(value.min, -16, "Wrong minimum value")

    def testFloatSHighValue(self):
        warnings.filterwarnings('error')
        value = sfixba(-17, 6, 0).scalb(-3)
        self.assertEqual(value.internal, -17)
        self.assertEqual(value.high, 3, "Wrong high value")
        self.assertEqual(value.low, -3, "Wrong low value")
        self.assertEqual(value.max, 32, "Wrong maximum value")
        self.assertEqual(value.min, -32, "Wrong minimum value")

    def testFloatHighLowValue(self):
        warnings.filterwarnings('error')
        value = sfixba(17, high=15, low=3)
        self.assertEqual(value, 16)
        self.assertEqual(value.high, 15, "Wrong high value")
        self.assertEqual(value.low, 3, "Wrong low value")
        self.assertEqual(value.max, 2048, "Wrong maximum value")
        self.assertEqual(value.min, -2048, "Wrong minimum value")

    def testFloatOverflow(self):
        warnings.filterwarnings('error')
        self.assertRaises(RuntimeWarning, sfixba, -17, high=1, low=-3)

    def testStrValue(self):
        warnings.filterwarnings('error')
        value = sfixba("0000000000000000000.11001101100111000")
        self.assertEqual(value.internal, 105272)
        self.assertEqual(value.high, 19, "Wrong high value")
        self.assertEqual(value.low, -17, "Wrong low value")
        self.assertEqual(value.hex(), "+0x00000.cd9c0")


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


class TestSFixBaIndexing(TestCase):

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
        offset = -64
        for s in self.seqs:
            n = long(s, 2)
            ba = sfixba(n, 64 - offset, 0).scalb(offset)
            bai = sfixba(~n, 64 - offset, 0).scalb(offset)
            for i in range(len(s) + 20):
                ref = long(getItem(s, i), 2)
                res = ba[i + offset]
                resi = bai[i + offset]
                self.assertEqual(res, ref)
                self.assertEqual(type(res), bool)
                self.assertEqual(resi, ref ^ 1)
                self.assertEqual(type(resi), bool)

    def testGetSlice(self):
        warnings.filterwarnings('error')
        self.seqsSetup()
        offset = -64
        for s in self.seqs:
            n = long(s, 2)
            ba = sfixba(n, 64 - offset, 0).scalb(offset)
            bai = ~ba
            for i in range(1, len(s) + 20):
                for j in range(0, i):
                    try:
                        res = ba[i + offset:j + offset]
                        resi = bai[i + offset:j + offset]
                    except RuntimeWarning:
                        self.assertTrue(i <= j)
                        continue
                    ref = long(getSlice(s, i, j), 2)
                    self.assertEqual(res, wrap(ref, res))
                    self.assertEqual(type(res), sfixba)
                    self.assertEqual(resi, wrap(~ref, resi))
                    self.assertEqual(type(resi), sfixba)

    def testGetSliceLeftOpen(self):
        warnings.filterwarnings('error')
        self.seqsSetup()
        for s in self.seqs:
            ba = sfixba(s, len(s) + 1, 0)
            bai = ~ba
            for j in range(0, len(s)):
                res = ba[:j]
                resi = bai[:j]
                ref = long(getSliceLeftOpen(s, j), 2)
                res_sum = resi + ref
                self.assertEqual(res, resize(ref, res))
                self.assertEqual(type(res), sfixba)
                if res_sum != -1:
                    resi + ref
                self.assertEqual(res_sum, -1, "Incorrect "
                                 "result: " +
                                 "{0}, {1}, {2}".format(repr(resi),
                                                        repr(ref), -1))
                self.assertEqual(type(res), sfixba)

    def testSetItem(self):
        warnings.filterwarnings('error')
        self.seqsSetup()
        for s in self.seqs:
            n = long(s, 2)
            for it in (int, sfixba):
                for i in range(len(s) + 20):
                    # print i
                    ba0 = sfixba(n, 128, 0)
                    ba1 = sfixba(n, 128, 0)
                    ba0i = sfixba(~n, 128, 0)
                    ba1i = sfixba(~n, 128, 0)
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
                    self.assertEqual(ba0i, ref0i)
                    self.assertEqual(ba1i, ref1i)

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
                        ba = sfixba(n, 128, 0)
                        val = long(v, 2)
                        toggle ^= 1
                        if toggle:
                            val = sfixba(val)
                        try:
                            ba[i:j] = val
                        except RuntimeWarning:
                            if isinstance(val, integer_types):
                                self.assertTrue((bit_length(val) > (i - j)) or
                                                (bit_length(-1 - val) >
                                                 (i - j)))
                            else:
                                self.assertTrue((len(val) != (i - j)) or \
                                                (len(-1 - val) != (i - j)))
                            continue
                        else:
                            ref = long(setSlice(s, i, j, extv), 2)
                            if ba != ref:
                                ba[i:j] = val
                                str(ba)
                            self.assertEqual(ba, ref)

    def testSetSliceLeftOpen(self):
        warnings.filterwarnings('error')
        self.seqsSetup()
        toggle = 0
        for s in self.seqs:
            for j in range(0, len(s)):
                for v in self.seqv:
                    ba = sfixba(s)
                    bai = ~ba
                    val = long(v, 2)
                    toggle ^= 1
                    if toggle:
                        val = sfixba(val)
                    try:
                        ba[:j] = val
                        bai[:j] = -1 - val
                    except RuntimeWarning:
                        if isinstance(val, integer_types):
                            self.assertTrue((bit_length(val) >
                                             (ba.high - j)) or
                                            (bit_length(-1-val) >
                                             (bai.high - j - 1)))
                        else:
                            self.assertTrue((len(val) != (ba.high - j)) or
                                            (len(-1-val) != (bai.high - j)))
                    else:
                        ref = long(setSliceLeftOpen(s, j, v), 2)
                        self.assertEqual(ba, wrap(ref, ba),
                                         "Different value: " +
                                         "{0}, {1}".format(ba, ref))
                        refi = ~long(setSliceLeftOpen(s, j, v), 2)
                        self.assertEqual(bai, wrap(refi, bai),
                                         "Different value: " +
                                         "{0}, {1}".format(bai, refi))


class TestSFixBaAsInt(TestCase):

    def seqSetup(self, imin, imax, jmin=0, jmax=None):
        seqi = [imin, imin, 12, 34]
        seqj = [jmin, 12, jmin, 34]
        if not imax and not jmax:
            l = 222222222
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

    def binaryMathCheck(self, op, imin=0, imax=None, jmin=0, jmax=None):
        warnings.filterwarnings('error')
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bi = sfixba(long(i), 32, 0)
            bj = sfixba(j, 32, 0)
            ref1 = op(resize(i, bj), j)
            ref2 = op(long(i), resize(j, bi))
            ref3 = op(long(i), j)
            try:
                try:
                    r1 = op(bi, j)
                    self.assertEqual(type(r1), sfixba)
                    self.assertEqual(r1, ref1,
                                     "Different results "
                                     "{0} {1} {2} = {3}, {4}".format(int(bi),
                                                                     op, j,
                                                                     int(r1),
                                                                     ref1))
                    r2 = op(i, bj)
                    self.assertEqual(type(r2), sfixba)
                    self.assertEqual(r2, ref2,
                                     "Different results "
                                     "{0} {1} {2} = {3}, {4}".format(i, op,
                                                                     int(bj),
                                                                     int(r2),
                                                                     ref2))
                except TypeError:
                    self.assertTrue(op in (operator.truediv,
                                           operator.pow))
                else:
                    r3 = op(bi, bj)
                    self.assertEqual(type(r3), sfixba)
                    self.assertEqual(r3, resize(ref3, r3),
                                     "Different results "
                                     "{0} {1} {2} = {3}, {4}".format(bi, op,
                                                                     bj,
                                                                     int(r3),
                                                                     ref3))
            except TypeError:
                self.assertTrue(op in (operator.truediv, operator.itruediv,
                                       operator.pow, operator.ipow))
        warnings.resetwarnings()

    def binaryTrueDivCheck(self, op, imin=0, imax=None, jmin=0, jmax=None):
        warnings.filterwarnings('error')
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bi = sfixba(long(i), 32, 0)
            bj = sfixba(j, 32, 0)
            r1 = op(bi, j)
            ref1 = truediv_round(op(resize(i, bj), j), r1)
            if r1 != ref1:
                op(bi, j)
            self.assertEqual(type(r1), sfixba)
            self.assertEqual(r1, ref1,
                             "Different results "
                             "{0} {1} {2} = {3}, {4}".format(float(bi),
                                                             op, j,
                                                             float(r1),
                                                             ref1))
            r2 = op(i, bj)
            ref2 = truediv_round(op(long(i), resize(j, bi)), r2)
            self.assertEqual(type(r2), sfixba)
            self.assertEqual(r2, ref2,
                             "Different results "
                             "{0} {1} {2} = {3}, {4}".format(i, op,
                                                             int(bj),
                                                             int(r2),
                                                             ref2))
            r3 = op(bi, bj)
            ref3 = truediv_round(op(long(i), j), r3)
            self.assertEqual(type(r3), sfixba)
            self.assertEqual(r3, resize(ref3, r3),
                             "Different results "
                             "{0} {1} {2} = {3}, {4}".format(bi, op, bj,
                                                             int(r3), ref3))
        warnings.resetwarnings()

    def binaryShiftCheck(self, op, imin=0, imax=None, jmin=0, jmax=None):
        warnings.filterwarnings('error')
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bi = sfixba(i, 64, 0)
            bj = sfixba(j, 64, 0)
            ref = op(long(i), j)
            r1 = op(bi, j)
            self.assertEqual(type(r1), sfixba)
            self.assertEqual(r1, ref,
                             "Different results "
                             "{0} {1} {2} = {3}, {4}".format(bi, op, j,
                                                             r1, ref))
            try:
                r2 = op(bi, bj)
            except:
                pass
            else:
                self.fail("Shifting of an sfixba by an sfixba should not "
                          "pass")
            try:
                r3 = op(i, bj)
            except:
                pass
            else:
                self.fail("Shifting of an integer by an sfixba should not "
                          "pass")
        warnings.resetwarnings()

    def binaryLogicalCheck(self, op, imin=0, imax=None, jmin=0, jmax=None):
        warnings.filterwarnings('error')
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bi = sfixba(i, 64, 0)
            bj = sfixba(j, 64, 0)
            ref = op(i, j)
            r1 = op(bi, bj)
            if r1 != ref:
                op(bi, bj)
            self.assertEqual(type(r1), sfixba)
            self.assertEqual(r1, ref,
                             "Different results "
                             "{0} {1} {2} = {3}, {4}".format(bi, op, j,
                                                             r1, ref))
            try:
                r2 = op(bi, j)
            except:
                pass
            else:
                self.fail("Logical between an sfixba and an int should not "
                          "pass")
            try:
                r3 = op(i, bj)
            except:
                pass
            else:
                self.fail("Logical between an int and an sfixba should not "
                          "pass")
        warnings.resetwarnings()

    def augmentedMathAssignCheck(self, op, imin=0, imax=None,
                                 jmin=0, jmax=None):
        warnings.filterwarnings('error')
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bj = sfixba(j, 32, 0)
            ref = long(i)
            ref = op(ref, j)
            r1 = bi1 = sfixba(i, 32, 0)
            try:
                try:
                    r1 = op(r1, j)
                    r2 = long(i)
                    r2 = op(r2, bj)
                    self.assertEqual(type(r1), sfixba)
                    self.assertEqual(r1, resize(ref, r1))
                    self.assertTrue(r1 is bi1)
                    self.assertEqual(type(r2), sfixba)
                    self.assertEqual(r2, resize(ref, r2))
                except TypeError:
                    self.assertTrue(op in (operator.iand, operator.ior,
                                           operator.ixor,
                                           operator.truediv, operator.itruediv,
                                           operator.pow, operator.ipow))
                else:
                    r3 = bi3 = sfixba(long(i), 32, 0)
                    r3 = op(r3, bj)
                    self.assertEqual(type(r3), sfixba)
                    self.assertEqual(r3, resize(ref, r3))
                    self.assertTrue(r3 is bi3)
            except RuntimeWarning:
                self.assertTrue(len(r3) != len(bj))
            except TypeError:
                self.assertTrue(op in (operator.truediv, operator.itruediv,
                                       operator.pow, operator.ipow))
        warnings.resetwarnings()

    def augmentedTrueDivAssignCheck(self, op, imin=0, imax=None,
                                    jmin=0, jmax=None):
        warnings.filterwarnings('error')
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bj = sfixba(j, 32, 0)
            ref = long(i)
            ref = op(ref, j)
            r1 = bi1 = sfixba(i, 32, 0)
            try:
                try:
                    r1 = op(r1, j)
                    r2 = long(i)
                    r2 = op(r2, bj)
                    self.assertEqual(type(r1), sfixba)
                    self.assertEqual(r1, truediv_round(ref, r1))
                    self.assertTrue(r1 is bi1)
                    self.assertEqual(type(r2), sfixba)
                    self.assertEqual(r2, truediv_round(ref, r2))
                except TypeError:
                    self.assertTrue(op in (operator.iand, operator.ior,
                                           operator.ixor,
                                           operator.truediv, operator.itruediv,
                                           operator.pow, operator.ipow))
                else:
                    r3 = bi3 = sfixba(long(i), 32, 0)
                    r3 = op(r3, bj)
                    self.assertEqual(type(r3), sfixba)
                    self.assertEqual(r3, truediv_round(ref, r3))
                    self.assertTrue(r3 is bi3)
            except RuntimeWarning:
                self.assertTrue(len(r3) != len(bj))
            except TypeError:
                self.assertTrue(op in (operator.truediv, operator.itruediv,
                                       operator.pow, operator.ipow))
        warnings.resetwarnings()

    def augmentedShiftAssignCheck(self, op, imin=0, imax=None,
                                  jmin=0, jmax=None):
        warnings.filterwarnings('error')
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bj = sintba(j, 128)
            ref = long(i)
            ref = op(ref, j)
            r1 = bi1 = sintba(long(i), 128)
            try:
                try:
                    r1 = op(r1, j)
                    r2 = long(i)
                    r2 = op(r2, bj)
                    self.assertEqual(type(r1), sintba)
                    self.assertEqual(r1, wrap(ref, r1))
                    self.assertTrue(r1 is bi1)
                    self.assertEqual(type(r2), sintba)
                    self.assertEqual(r2, wrap(ref, r2))
                except TypeError:
                    self.assertTrue(op in (operator.iand, operator.ior,
                                           operator.ixor,
                                           operator.truediv, operator.itruediv,
                                           operator.pow, operator.ipow))
                else:
                    r3 = bi3 = sintba(long(i), 128)
                    r3 = op(r3, bj)
                    self.assertEqual(type(r3), sintba)
                    self.assertEqual(r3, wrap(ref, r3))
                    self.assertTrue(r3 is bi3)
            except RuntimeWarning:
                self.assertTrue(len(r3) != len(bj))
            except TypeError:
                self.assertTrue(op in (operator.truediv, operator.itruediv,
                                       operator.pow, operator.ipow))
        warnings.resetwarnings()

    def augmentedLogicalAssignCheck(self, op, imin=0, imax=None,
                                    jmin=0, jmax=None):
        warnings.filterwarnings('error')
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bj = sintba(j, 128)
            ref = long(i)
            ref = op(ref, j)
            r1 = bi1 = sintba(long(i), 128)
            try:
                try:
                    r1 = op(r1, j)
                    r2 = long(i)
                    r2 = op(r2, bj)
                    self.assertEqual(type(r1), sintba)
                    self.assertEqual(r1, wrap(ref, r1))
                    self.assertTrue(r1 is bi1)
                    self.assertEqual(type(r2), sintba)
                    self.assertEqual(r2, wrap(ref, r2))
                except TypeError:
                    self.assertTrue(op in (operator.iand, operator.ior,
                                           operator.ixor,
                                           operator.truediv, operator.itruediv,
                                           operator.pow, operator.ipow))
                else:
                    r3 = bi3 = sintba(long(i), 128)
                    r3 = op(r3, bj)
                    self.assertEqual(type(r3), sintba)
                    self.assertEqual(r3, wrap(ref, r3))
                    self.assertTrue(r3 is bi3)
            except RuntimeWarning:
                self.assertTrue(len(r3) != len(bj))
            except TypeError:
                self.assertTrue(op in (operator.truediv, operator.itruediv,
                                       operator.pow, operator.ipow))
        warnings.resetwarnings()

    def unaryCheck(self, op, imin=0, imax=None):
        self.seqSetup(imin=imin, imax=imax)
        for i in self.seqi:
            bi = sfixba(i)
            ref = op(i)
            r1 = op(bi)
            self.assertEqual(type(r1), sfixba)
            self.assertEqual(r1, ref)

    def conversionCheck(self, op, imin=0, imax=None):
        self.seqSetup(imin=imin, imax=imax)
        for i in self.seqi:
            bi = sfixba(i)
            ref = op(long(i))
            r1 = op(bi)
            self.assertEqual(type(r1), type(ref))
            self.assertEqual(r1, ref)

    def comparisonCheck(self, op, imin=0, imax=None, jmin=0, jmax=None):
        self.seqSetup(imin=imin, imax=imax, jmin=jmin, jmax=jmax)
        for i, j in zip(self.seqi, self.seqj):
            bi = sfixba(i)
            bj = sfixba(j)
            ref = op(i, j)
            ri = resize(i, bj)
            rj = resize(j, bi)
            r1 = op(bi, j)
            r2 = op(i, bj)
            r3 = op(bi, bj)
            self.assertEqual(r1, op(i, rj), "bi, j, i, rj: "
                             "{0}, {1}, {2}, {3}".format(bi, j, i, rj))
            self.assertEqual(r2, op(ri, j), "i, bj, ri, j: "
                             "{0}, {1}, {2}, {3}".format(i, bj, ri, j))
            self.assertEqual(r3, ref, "bi, bj, i, j: "
                             "{0}, {1}, {2}, {3}".format(bi, bj, i, j))

    def testAdd(self):
        self.binaryMathCheck(operator.add, imin=-512, imax=512,
                             jmin=-512, jmax=512)

    def testSub(self):
        self.binaryMathCheck(operator.sub, imin=-512, imax=512,
                             jmin=-512, jmax=512)

    def testMul(self):
        self.binaryMathCheck(operator.mul, imin=-512, imax=512,
                             jmin=-512, jmax=512)

    def testTrueDiv(self):
        self.binaryTrueDivCheck(operator.truediv, imin=-512, imax=512,
                                jmin=1, jmax=512)
        self.binaryTrueDivCheck(operator.truediv, imin=-512, imax=512,
                                jmin=-512, jmax=-1)

    def testFloorDiv(self):
        self.binaryMathCheck(operator.floordiv, imin=-512, imax=512,
                             jmin=1, jmax=512)
        self.binaryMathCheck(operator.floordiv, imin=-512, imax=512,
                             jmin=-512, jmax=-1)

    def testMod(self):
        self.binaryMathCheck(operator.mod, imin=-512, imax=512,
                             jmin=1, jmax=512)
        self.binaryMathCheck(operator.mod, imin=-512, imax=512,
                             jmin=-512, jmax=-1)

    def testPow(self):
        self.binaryMathCheck(operator.pow, imin=-512, imax=-1,
                             jmin=-8, jmax=8)
        self.binaryMathCheck(operator.pow, imin=1, imax=512,
                             jmin=-8, jmax=8)

    def testLShift(self):
        self.binaryShiftCheck(operator.lshift, imin=-512, imax=512,
                              jmin=0, jmax=32)

    def testRShift(self):
        self.binaryShiftCheck(operator.rshift, imin=-512, imax=512,
                              jmin=0, jmax=32)

    def testAnd(self):
        self.binaryLogicalCheck(operator.and_, imin=-512, imax=512,
                                jmin=-512, jmax=512)

    def testOr(self):
        self.binaryLogicalCheck(operator.or_, imin=-512, imax=512,
                                jmin=-512, jmax=512)

    def testXor(self):
        self.binaryLogicalCheck(operator.xor, imin=-512, imax=512,
                                jmin=-512, jmax=512)

    def testIAdd(self):
        self.augmentedMathAssignCheck(operator.iadd, imin=-512, imax=512,
                                      jmin=-512, jmax=512)

    def testISub(self):
        self.augmentedMathAssignCheck(operator.isub, imin=-512, imax=512,
                                      jmin=-512, jmax=512)

    def testIMul(self):
        self.augmentedMathAssignCheck(operator.imul, imin=-512, imax=512,
                                      jmin=-512, jmax=512)

    def testIFloorDiv(self):
        self.augmentedMathAssignCheck(operator.ifloordiv, imin=-512, imax=512,
                                      jmin=1, jmax=512)
        self.augmentedMathAssignCheck(operator.ifloordiv, imin=-512, imax=512,
                                      jmin=-512, jmax=-1)

    def testITrueDiv(self):
        self.augmentedTrueDivAssignCheck(operator.ifloordiv, imin=-512,
                                         imax=512, jmin=1, jmax=512)
        self.augmentedTrueDivAssignCheck(operator.ifloordiv, imin=-512,
                                         imax=512, jmin=-512, jmax=-1)

    def testIMod(self):
        self.augmentedMathAssignCheck(operator.imod, imin=-512, imax=512,
                                      jmin=1, jmax=512)
        self.augmentedMathAssignCheck(operator.imod, imin=-512, imax=512,
                                      jmin=-512, jmax=-1)

    def testIPow(self):
        self.augmentedMathAssignCheck(operator.ipow, imin=-512, imax=-1,
                                      jmin=-8, jmax=8)
        self.augmentedMathAssignCheck(operator.ipow, imin=1, imax=512,
                                      jmin=-8, jmax=8)

    def testIAnd(self):
        self.augmentedLogicalAssignCheck(operator.iand, imin=-512, imax=512,
                                         jmin=-512, jmax=512)

    def testIOr(self):
        self.augmentedLogicalAssignCheck(operator.ior, imin=-512, imax=512,
                                         jmin=-512, jmax=512)

    def testIXor(self):
        self.augmentedLogicalAssignCheck(operator.ixor, imin=-512, imax=512,
                                         jmin=-512, jmax=512)

    def testILShift(self):
        self.augmentedShiftAssignCheck(operator.ilshift, imin=-512, imax=512,
                                       jmin=0, jmax=32)

    def testIRShift(self):
        self.augmentedShiftAssignCheck(operator.irshift, imin=-512, imax=512,
                                       jmin=0, jmax=32)

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

    def testOct(self):
        try:
            self.conversionCheck(oct)
        except TypeError:
            pass
        else:
            assert False

    def testHex(self):
        try:
            self.conversionCheck(hex)
        except TypeError:
            pass
        else:
            assert False

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


# class TestSFixBaBounds(TestCase):
#   
#     def testConstructor(self):
#         warnings.filterwarnings('error')
#         self.assertEqual(sintba(40, high=54), 40)
#         self.assertEqual(sintba(-25, high=16), -25)
#         try:
#             self.assertTrue(sintba(40, high=3) != 40)
#         except RuntimeWarning:
#             pass
#         else:
#             self.fail()
#         try:
#             self.assertTrue(sintba(-25, high=3) != -25)
#         except RuntimeWarning:
#             pass
#         else:
#             self.fail()
#         warnings.resetwarnings()
#   
#     def testSliceAssign(self):
#         warnings.filterwarnings('error')
#         a = sfixba(high=10, low=0)
#         for i in (0, 2, 13, 31):
#             for k in (7, 9, 10):
#                 a[:] = 0
#                 a[k:] = i
#                 self.assertEqual(a, i & ((1 << len(a)) - 1))
#         for i in (32, 63, 74, 116, 229):
#             for k in (11, 12, 13):
#                 try:
#                     a[k:] = i
#                 except RuntimeWarning:
#                     pass
#                 else:
#                     self.fail()
#         a = sfixba(5, 14, 0)
#         for v in (0, 2 ** 8 - 1, 100, -1000, 4096):
#             a[:] = v
#   
#     def checkBounds(self, i, j, op, resized=True):
#         warnings.filterwarnings('error')
#         a = sfixba(i)
#         self.assertEqual(a, i) # just to be sure
#         try:
#             op(a, long(j))
#         except (ZeroDivisionError, ValueError):
#             return # prune
#         if not isinstance(a._val, (int, long)):
#             return # prune
#         if abs(a) > maxint * maxint:
#             return # keep it reasonable
#         if a > i:
#             b = sfixba(i)
#             for _ in (i+1, a):
#                 b = sfixba(i)
#                 b = op(b, long(j))
#                 if resized:
#                     if op in (operator.ifloordiv, operator.imod):
#                         ref = b.resize(op(float(i), float(b.resize(j))))
#                     else:
#                         ref = b.resize(op(i, b.resize(j)))
#                 else:
#                     ref = op(i, j)
#                 self.assertEqual(b, ref, "Wrong result: " \
#                                  "{}({}, {}) = {}, {}".format(op, i, j,
#                                                               ref, b))
#         elif a < i :
#             b = sfixba(i)
#             b = op(b, long(j)) # should be ok
#             for _ in (a+1, i):
#                 b = sfixba(i)
#                 b = op(b, j)
#                 if resized:
#                     if op in (operator.ifloordiv, operator.imod):
#                         ref = b.resize(op(float(i), float(b.resize(j))))
#                     else:
#                         ref = b.resize(op(i, b.resize(j)))
#                 else:
#                     ref = op(i, j)
#                 if b != ref:
#                     b = sfixba(i)
#                     b = op(b, j)
#                 self.assertEqual(b, ref, "Wrong result: " \
#                                  "{}({}, {}) = {}, {}".format(op, i, j,
#                                                               ref, b))
#         else: # a == i
#             b = sfixba(i)
#             op(b, long(j))
#   
#     def checkOp(self, op, resized=True):
#         warnings.filterwarnings('error')
#         for i in (0, 1, 2, 16, 129, 1025):
#             for j in (0, 1, 2, 9, 123, 2340):
#                 self.checkBounds(i, j, op, resized)
#   
#     def testIAdd(self):
#         self.checkOp(operator.iadd)
#   
#     def testISub(self):
#         self.checkOp(operator.isub)
#   
#     def testIMul(self):
#         self.checkOp(operator.imul)
#   
#     def testIFloorDiv(self):
#         self.checkOp(operator.ifloordiv)
#   
#     def testIMod(self):
#         self.checkOp(operator.imod)
#   
#     def testIPow(self):
#         self.assertRaises(TypeError, self.checkOp, operator.ipow)
#   
#     def testIAnd(self):
#         self.checkOp(operator.iand, resized=False)
#   
# #    def testIOr(self):
# #        self.checkOp(operator.ior)
#   
# #    def testIXor(self):
# #        self.checkOp(operator.ixor)
#   
#     def testILShift(self):
#         self.checkOp(operator.ilshift)
#   
#     def testIRShift(self):
#         self.checkOp(operator.irshift)


class TestSFixBaCopy(TestCase):

    def testCopy(self):
        for n in (sfixba(), sfixba(34), sfixba(12), sfixba(45),
                  sfixba(23), sfixba(-35, 7)):
            a = sfixba(n)
            b = copy(n)
            c = deepcopy(n)
            for m in (a, b, c):
                if n != m:
                    a = sfixba(n)
                    b = copy(a)
                    c = deepcopy(a)
                self.assertEqual(n, m)
                self.assertEqual(n.internal, m.internal)
                self.assertEqual(n.high, m.high)
                self.assertEqual(n.low, m.low)
                self.assertEqual(len(n), len(m))


if __name__ == "__main__":
    unittest.main()
