from __future__ import absolute_import
from myhdl import *
from myhdl.conversion import analyze

import pytest

def issue_98(sda, scl, sda_i, sda_o, scl_i, scl_o):
     sda_d, scl_d = sda.driver(), scl.driver()
     @always_comb
     def hdl():
         sda_i.next = sda
         sda_d.next = 0 if not sda_o else None 
         scl_i.next = scl
         scl_d.next = None if not scl_o else 1 
     return hdl

def test_issue_98_1():
    sda_i, sda_o, scl_i, scl_o = [Signal(False) for i in range(4)]
    sda, scl = [TristateSignal(False) for i in range(2)]
    toVHDL.name = toVerilog.name = 'issue_98_1'
    assert analyze(issue_98, sda, scl, sda_i, sda_o, scl_i, scl_o) == 0

def test_issue_98_2():
    sda_i, sda_o, scl_i, scl_o = [Signal(intbv(0)[2:0]) for i in range(4)]
    sda, scl = [TristateSignal(intbv(0)[2:0]) for i in range(2)]
    toVHDL.name = toVerilog.name = 'issue_98_2'
    assert analyze(issue_98, sda, scl, sda_i, sda_o, scl_i, scl_o) == 0

def test_issue_98_3():
    sda_i, sda_o, scl_i, scl_o = [Signal(intbv(0)[1:0]) for i in range(4)]
    sda, scl = [TristateSignal(intbv(0)[1:0]) for i in range(2)]
    toVHDL.name = toVerilog.name = 'issue_98_3'
    assert analyze(issue_98, sda, scl, sda_i, sda_o, scl_i, scl_o) == 0

