from __future__ import absolute_import
import os
path = os.path
import subprocess
import myhdl
from myhdl import *
# Icarus
def setupCosimulationIcarus(**kwargs):
    name = kwargs['name']
    objfile = "%s.o" % name
    if path.exists(objfile):
        os.remove(objfile)
    analyze_cmd = ['iverilog', '-o', objfile, '%s.v' %name, 'tb_%s.v' % name]
    subprocess.call(analyze_cmd)
    vpi = os.path.abspath(myhdl.__file__+"/../../cosimulation/icarus/myhdl.vpi")
    simulate_cmd = ['vvp', '-m', vpi, objfile]
    return Cosimulation(simulate_cmd, **kwargs)

# cver
def setupCosimulationCver(**kwargs):
    name = kwargs['name']
    vpi = os.path.abspath(myhdl.__file__+"/../../cosimulation/cver/myhdl_vpi")
    cmd = "cver -q +loadvpi=%s:vpi_compat_bootstrap " + \
          "%s.v tb_%s.v " % (vpi, name, name)
    return Cosimulation(cmd, **kwargs)

def verilogCompileIcarus(name):
    objfile = "%s.o" % name
    if path.exists(objfile):
        os.remove(objfile)
    analyze_cmd = "iverilog -o %s %s.v tb_%s.v" % (objfile, name, name)
    os.system(analyze_cmd)


def verilogCompileCver(name):
    cmd = "cver -c %s.v" % name
    os.system(cmd)



setupCosimulation = setupCosimulationIcarus
#setupCosimulation = setupCosimulationCver

verilogCompile = verilogCompileIcarus
#verilogCompile = verilogCompileCver
