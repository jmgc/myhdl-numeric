"""
"""
# This file is part of the myhdl-numeric library.
#
# Copyright (C) 2015 Jose M. Gomez
#
# The test is simulated, analyzed and finally verified using a vhdl simulator.

import random

from myhdl import Signal, instance, always_seq, ResetSignal, delay, now, \
        StopSimulation, Simulation, conversion, traceSignals, enum
from myhdl import uintba, sintba, sfixba, fixmath
import math as m
import numpy as np
from unittest import TestCase
from random import randrange

random.seed(2)  # random, but deterministic

NRTESTS = 10


class CordicIf(object):

    """Interface that allows the access to the cordic module.

    Attributes:
        enable: enables the sqrt_mod calculation
        x_in: x input value
        y_in: y input value
        theta_in: theta input value
        clk: indicates a new result has been calculated
        x_out: x output value
        y_out: y output value
        theta_out: theta output value
    """

    def __init__(self, vector_high, vector_low,
                 angle_high=None, angle_low=None):
        if angle_high is None:
            angle_high = vector_high
        if angle_low is None:
            angle_low = vector_low
        self.enable = Signal(False)
        self.x_in = Signal(sfixba(0, vector_high, vector_low))
        self.y_in = Signal(sfixba(0, vector_high, vector_low))
        self.theta_in = Signal(sfixba(0, angle_high, angle_low))
        self.clk = Signal(False)
        self.x_out = Signal(sfixba(0, vector_high, vector_low))
        self.y_out = Signal(sfixba(0, vector_high, vector_low))
        self.theta_out = Signal(sfixba(0, angle_high, angle_low))

cordic_modes = enum('ROTATING',
                    'VECTORING')
"""Cordic Module modes

    Attributes:
        ROTATING: Rotates a vector an angle
        VECTORING: Recovers the angle and the module of a vector
"""

def cordic_mod(reset, clk, values, mode=cordic_modes.ROTATING):
    """ Cordic root calculation module

    It follows a successive approximation algorithm and a square operation
    to calculate the square root.

    Arguments:
        reset
        clk: clock
        values: input/output interface that allows to provide/retrieve
          data to/from the cordic module. It follows the interface
          :py:class:`ISSControl.iss_base_data.CordicIf`
    """

    assert values.x_in.high == values.y_in.high
    assert values.x_in.low == values.y_in.low
    assert values.x_out.high >= values.x_in.high
    assert values.y_out.high >= values.y_in.high
    assert values.x_out.low <= values.x_in.low
    assert values.y_out.low <= values.y_in.low
    assert values.theta_out.high >= values.theta_in.high
    assert values.theta_out.low <= values.theta_in.low

    GUARD_BITS = fixmath().guard_bits
    length = max(len(values.x_in), len(values.y_in),
                 len(values.theta_in))
    OFFSET_BITS = GUARD_BITS + m.ceil(m.log(length, 2))
    BITS = length + OFFSET_BITS
    HALF = 1.0
    QUARTER = HALF / 2.0
    indexes = range(0, BITS)

    atanval = Signal(sfixba(0, 2, -BITS))
    arctantab = tuple([int(sfixba(m.atan(2.**-idx)/m.pi, atanval.val)[:])
                       for idx in indexes])
    cos_scale = Signal(sfixba(0, 2, -BITS))

    COSCALE = float(np.prod(1. /
                            np.sqrt(1 +
                                    np.power(2.,
                                             -2 *
                                             np.array(indexes)
                                             ))))

    pTx = Signal(sfixba(0, values.x_in.high, values.x_in.high - BITS))
    pTy = Signal(sfixba(0, values.y_in.high, values.y_in.high - BITS))
    pTheta = Signal(sfixba(0, 2, - BITS,
                           overflow=fixmath.overflows.wrap))

    pTx_shift = Signal(sfixba(0, pTx.val))
    pTy_shift = Signal(sfixba(0, pTy.val))

    lhs = Signal(sfixba(pTx.val))
    result = Signal(lhs.val*cos_scale.val)

    pCounter = Signal(sintba(BITS))

    t_states = enum('CORDIC_INIT',
                    'CORDIC_START',
                    'CORDIC_SHIFT',
                    'CORDIC_CALC',
                    'CORDIC_NEXT',
                    'CORDIC_COS',
                    'CORDIC_SIN',
                    'CORDIC_RESULT',
                    'CORDIC_END')

    state = Signal(t_states.CORDIC_INIT)

    @always_seq(clk.posedge, reset)
    def fsm():

        cos_scale.next = COSCALE

        if not values.enable:
            state.next = t_states.CORDIC_INIT
            values.clk.next = False
        else:

            if state == t_states.CORDIC_INIT:
                pTx.next = values.x_in
                pTy.next = values.y_in
                pTheta.next = values.theta_in
                pCounter.next = 0

                values.clk.next = False
                state.next = t_states.CORDIC_START
            elif state == t_states.CORDIC_START:
                # Get angle between -1/2 and 1/2 angles
                state.next = t_states.CORDIC_SHIFT

                if mode == cordic_modes.ROTATING:
                    if pTheta < -QUARTER:
                        pTx.next = -pTx
                        pTy.next = -pTy

                        pTheta.next = pTheta + sfixba(HALF, atanval.val)
                        state.next = t_states.CORDIC_START
                    elif pTheta >= QUARTER:
                        pTx.next = -pTx
                        pTy.next = -pTy

                        pTheta.next = pTheta - sfixba(HALF, atanval.val)
                        state.next = t_states.CORDIC_START
                else:
                    if pTy >= 0 and pTx < 0:
                        pTx.next = -pTx
                        pTy.next = -pTy

                        pTheta.next = pTheta + sfixba(HALF, atanval.val)
                        state.next = t_states.CORDIC_START
                    elif pTy < 0 and pTx < 0:
                        pTx.next = -pTx
                        pTy.next = -pTy

                        pTheta.next = pTheta - sfixba(HALF, atanval.val)
                        state.next = t_states.CORDIC_START

                values.clk.next = False
            elif state == t_states.CORDIC_SHIFT:
                pTx_shift.next = pTx >> int(pCounter)
                pTy_shift.next = pTy >> int(pCounter)
                atanval.next[:] = arctantab[pCounter]

                values.clk.next = False
                state.next = t_states.CORDIC_CALC
            elif state == t_states.CORDIC_CALC:
                if ((pTheta < 0) and (mode == cordic_modes.ROTATING)) or \
                        ((pTy >= 0) and (mode != cordic_modes.ROTATING)):
                    pTx.next = pTx + pTy_shift
                    pTy.next = pTy - pTx_shift

                    pTheta.next = pTheta + atanval
                else:
                    pTx.next = pTx - pTy_shift
                    pTy.next = pTy + pTx_shift

                    pTheta.next = pTheta - atanval

                pCounter.next = pCounter + 1
                values.clk.next = False

                state.next = t_states.CORDIC_NEXT
            elif state == t_states.CORDIC_NEXT:
                values.clk.next = False

                if pCounter < BITS:
                    state.next = t_states.CORDIC_SHIFT
                else:
                    lhs.next = pTx
                    state.next = t_states.CORDIC_COS
            elif state == t_states.CORDIC_COS:
                result.next = lhs*sfixba(COSCALE, atanval.val)
                lhs.next = pTy
                values.clk.next = False
                state.next = t_states.CORDIC_SIN
            elif state == t_states.CORDIC_SIN:
                values.x_out.next = result
                result.next = lhs*sfixba(COSCALE, atanval.val)
                values.clk.next = False
                state.next = t_states.CORDIC_RESULT
            elif state == t_states.CORDIC_RESULT:
                values.y_out.next = result
                values.theta_out.next = pTheta
                values.clk.next = True
                state.next = t_states.CORDIC_END
            else:
                values.clk.next = False

    return fsm

def cordic(x, y, angle, mode=cordic_modes.ROTATING, bits=16):
    """ Function to calculate rotations using the CORDIC algorithm. The inputs x, y and angle
    are assumed to be in double format, with values between [-1, 1[. The parameter bits indicates
    the number of bits of the inputs taken into account."""

    GUARD_BITS = fixmath().guard_bits
    OFFSET_BITS = GUARD_BITS + m.ceil(m.log(bits, 2))
    BITS = bits + OFFSET_BITS
    QUARTER = sfixba(0.5, 2, -1)
    indexes = range(0, BITS)
    arctantab = [sfixba(m.atan(2. ** -idx) / m.pi, 1, -BITS)
                 for idx in indexes]
    COSCALE = sfixba(float(np.prod(1. /
                                   np.sqrt(1 +
                                           np.power(2.0,
                                                    (-2 *
                                                     np.array(indexes)))))),
                     2, -BITS)

    pTx = sfixba(float(x), 2, 2-BITS)
    pTy = sfixba(float(y), 2, 2-BITS)
    pTheta = sfixba(float(angle), 1, -BITS,
                    fixmath(overflow=fixmath.overflows.wrap))

    # Get angle between -1/2 and 1/2 angles

    if mode == cordic_modes.ROTATING:
        if pTheta < -QUARTER:
            pTx = sfixba(-pTx, pTx)
            pTy = sfixba(-pTy, pTy)

            pTheta += (QUARTER << 1)
        elif pTheta >= QUARTER:
            pTx = sfixba(-pTx, pTx)
            pTy = sfixba(-pTy, pTy)

            pTheta -= (QUARTER << 1)
    else:
        if pTy >= 0 and pTx < 0:
            pTx = sfixba(-pTx, pTx)
            pTy = sfixba(-pTy, pTy)

            pTheta += (QUARTER << 1)
        elif pTy < 0 and pTx < 0:
            pTx = sfixba(-pTx, pTx)
            pTy = sfixba(-pTy, pTy)

            pTheta -= (QUARTER << 1)

    for (pCounter, atanval) in zip(indexes, arctantab):
        if ((pTheta < 0) and (mode == cordic_modes.ROTATING)) or \
                ((pTy >= 0) and (mode != cordic_modes.ROTATING)):
            xtemp = pTx + (pTy >> pCounter)
            pTy = sfixba(pTy - (pTx >> pCounter), pTy)
            pTx = sfixba(xtemp, pTx)

            pTheta += atanval
        else:
            xtemp = pTx - (pTy >> pCounter)
            pTy = sfixba(pTy + (pTx >> pCounter), pTy)
            pTx = sfixba(xtemp, pTx)

            pTheta -= atanval

    pCos = sfixba(pTx * COSCALE, 2, 2 - int(bits))
    pSin = sfixba(pTy * COSCALE, 2, 2 - int(bits))

    return (pCos, pSin, pTheta)

def cordicTestBench():
    low = -14
    clk = Signal(False)
    reset = ResetSignal(True, True, False)
    values = CordicIf(16 + low, low, 1, -15)

    RANDOM_INPUTS = tuple([values.theta_in.min, 0, values.theta_in.max - 1] +
                          [randrange(values.theta_in.min, values.theta_in.max)
                           for _ in range(NRTESTS)])

    ANGLE_INPUTS = tuple(sfixba(RANDOM_INPUTS[i] /
                                abs(values.theta_in.min),
                                values.theta_out.val)
                         for i in range(len(RANDOM_INPUTS)))

    COS_OUTPUTS = tuple(int(cordic(1, 0, ANGLE_INPUTS[i])[0][:])
                        for i in range(len(RANDOM_INPUTS)))

    SIN_OUTPUTS = tuple(int(cordic(1, 0, ANGLE_INPUTS[i])[1][:])
                        for i in range(len(RANDOM_INPUTS)))

    count = Signal(uintba(NRTESTS))

    cos_value = Signal(cordic(1, 0, 0)[0])
    sin_value = Signal(cordic(1, 0, 0)[1])

    dut = cordic_mod(reset, clk, values)

    @instance
    def clockGen():
        clk.next = False
        while True:
            yield delay(10)
            clk.next = not clk

    @instance
    def stimulus():
        values.x_in.next = 0
        values.y_in.next = 0
        values.theta_in.next = 0
        values.enable.next = 0
        count.next = 0
        reset.next = True
        yield clk.posedge
        reset.next = False
        yield clk.posedge
        for i in range(len(RANDOM_INPUTS)):
            values.enable.next = True
            count.next = i
            values.x_in.next = 1
            values.y_in.next = 0
            values.theta_in.next[:] = RANDOM_INPUTS[i]
            cos_value.next[:] = COS_OUTPUTS[i]
            sin_value.next[:] = SIN_OUTPUTS[i]
            while not values.clk:
                yield clk.posedge
            values.enable.next = False
            yield clk.posedge
            yield clk.posedge
        yield clk.posedge
        raise StopSimulation

    @always_seq(clk.posedge, reset)
    def check():
        if values.clk:
            print(now(), count, values.theta_in,
                  values.x_out, values.y_out, values.theta_out)
            diff = values.x_out - cos_value
            assert (diff).abs() < (2.0 ** (cos_value.low + 1)), \
                    "%r != %r" % (values.x_out, cos_value)
            diff = values.y_out - sin_value
            assert (diff).abs() < (2.0 ** (sin_value.low + 1)), \
                    "%r != %r" % (values.y_out, sin_value)
            assert values.theta_out == 0

    return clockGen, stimulus, dut, check


class TestCordic(TestCase):
    def test_CordicTestBench(self):
        sim = Simulation(cordicTestBench())
        sim.run(quiet=True)

    def test_Conversion(self):
        clk = Signal(False)
        reset = ResetSignal(True, True, False)
        values = CordicIf(2, -16)
        conversion.analyze(cordic_mod, reset, clk, values)

    def test_CordicVerify(self):
        self.assertEqual(conversion.verify(cordicTestBench), 0)

if __name__ == "__main__":
    from unittest import TestLoader, TextTestRunner
    suite = TestLoader().loadTestsFromTestCase(TestCordic)
    TextTestRunner(verbosity=2).run(suite)
