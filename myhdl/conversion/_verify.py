from __future__ import absolute_import
from __future__ import print_function
import sys
import os
import tempfile
import subprocess
import difflib

from collections import namedtuple

from .._Simulation import Simulation
from ._toVHDL import toVHDL
from ._toVerilog import toVerilog
from .._version import __version__

_version = __version__.replace('.', '')
# strip 'dev' for version
_version = _version.replace('dev', '')

_simulators = {}

sim = namedtuple('sim',
                 ['name',
                  'hdl',
                  'analyze',
                  'elaborate',
                  'simulate',
                  'skiplines',
                  'skipchars',
                  'ignore',
                  'languageVersion'])


def registerSimulator(name=None, hdl=None, analyze=None, elaborate=None,
                      simulate=None, skiplines=None, skipchars=None,
                      ignore=None, languageVersion=None):
    if not isinstance(name, str) or (name.strip() == ""):
        raise ValueError("Invalid simulator name")
    if hdl not in ("VHDL", "Verilog"):
        raise ValueError("Invalid hdl %s" % hdl)
    if not isinstance(analyze, str) or (analyze.strip() == ""):
        raise ValueError("Invalid analyzer command")
    # elaborate command is optional
    if elaborate is not None:
        if not isinstance(elaborate, str) or (elaborate.strip() == ""):
            raise ValueError("Invalid elaborate command")
    if not isinstance(simulate, str) or (simulate.strip() == ""):
        raise ValueError("Invalid simulator command")
    if hdl != "VHDL":
        languageVersion = None

    _simulators[name] = sim(name, hdl, analyze, elaborate, simulate,
                            skiplines, skipchars, ignore, languageVersion)

registerSimulator(
    name="ghdl",
    hdl="VHDL",
    analyze="ghdl -a --std=08 --workdir=work_%(topname)s pck_%(topname)s_myhdl_%(version)s.vhd %(topname)s.vhd",
    elaborate="ghdl -e --std=08 --workdir=work_%(topname)s -o %(unitname)s %(topname)s",
    simulate="ghdl -r --workdir=work_%(topname)s %(unitname)s",
    languageVersion="2008"
    )

# registerSimulator(
#     name="ghdl-coverage",
#     hdl="VHDL",
#     analyze="ghdl -a --std=08 --workdir=work_%(topname)s -Wc,-ftest-coverage -Wc,-fprofile-arcs"
#         " pck_%(topname)s_myhdl_%(version)s.vhd %(topname)s.vhd",
#     elaborate="ghdl -e --std=08 --workdir=work_%(topname)s -Wl,"
#         "-L`which ghdl`/../lib/gcc/x86_64-apple-darwin13.0.0/4.8.2/"
#         " -Wl,-lgcov -o %(unitname)s %(topname)s",
#     simulate="ghdl -r --workdir=work_%(topname)s %(unitname)s --vcd=%(unitname)s.gcov.vcd"
#     )

registerSimulator(
    name="nvc",
    hdl="VHDL",
    analyze="nvc --work=work_%(topname)s_nvc -a pck_%(topname)s_myhdl_%(version)s.vhd %(topname)s.vhd",
    elaborate="nvc --work=work_%(topname)s_nvc -e %(topname)s",
    simulate="nvc --work=work_%(topname)s_nvc -r %(topname)s"
    )

registerSimulator(
    name="vlog",
    hdl="Verilog",
    analyze="vlog -work work_%(topname)s_vlog %(topname)s.v",
    simulate='vsim work_%(topname)s_vlog.%(topname)s -quiet -c -do "run -all; quit -f"',
    skiplines=6,
    skipchars=2,
    ignore=("# **", "# //", "# run -all")
    )

registerSimulator(
    name="vcom",
    hdl="VHDL",
    analyze="vcom -2008 -work work_%(topname)s_vcom pck_%(topname)s_myhdl_%(version)s.vhd"
        " %(topname)s.vhd",
    simulate='vsim work_%(topname)s_vcom.%(topname)s -quiet -c -do "run -all; quit -f"',
    skiplines=6,
    skipchars=2,
    ignore=("# **", "# //", "#    Time:", "# run -all"),
    languageVersion="2008"
    )

registerSimulator(
    name="vcom-coverage",
    hdl="VHDL",
    analyze="vcom -2008 -work work_%(topname)s_vcom pck_%(topname)s_myhdl_%(version)s.vhd"
        " %(topname)s.vhd",
    simulate='vsim work_%(topname)s_vcom.%(topname)s -quiet -c -do'
             ' "coverage save -onexit %(topname)s.ucdb; run -all; quit -f" '
             '-coverage -voptargs="+cover=bcfst"',
    skiplines=6,
    skipchars=2,
    ignore=("# **", "# //", "#    Time:", "# run -all"),
    languageVersion="2008"
    )

registerSimulator(
    name="iverilog",
    hdl="Verilog",
    analyze="iverilog -o %(topname)s.o %(topname)s.v",
    simulate="vvp %(topname)s.o"
    )

registerSimulator(
    name="cver",
    hdl="Verilog",
    analyze="cver -c -q %(topname)s.v",
    simulate="cver -q %(topname)s.v",
    skiplines=3
    )


class _VerificationClass(object):

    __slots__ = ("simulator", "_analyzeOnly")

    def __init__(self, analyzeOnly=False):
        self.simulator = None
        self._analyzeOnly = analyzeOnly

    def __call__(self, func, *args, **kwargs):

        if not self.simulator:
            raise ValueError("No simulator specified")
        if self.simulator not in _simulators:
            raise ValueError("Simulator %s is not registered" % self.simulator)
        hdlsim = _simulators[self.simulator]
        hdl = hdlsim.hdl
        if hdl == 'Verilog' and toVerilog.name is not None:
            name = toVerilog.name
        elif hdl == 'VHDL' and toVHDL.name is not None:
            name = toVHDL.name
        else:
            name = func.__name__

        vals = {}
        vals['topname'] = name
        vals['unitname'] = name.lower()
        vals['version'] = _version

        analyze = hdlsim.analyze % vals
        elaborate = hdlsim.elaborate
        if elaborate is not None:
            elaborate = elaborate % vals
        simulate = hdlsim.simulate % vals
        skiplines = hdlsim.skiplines
        skipchars = hdlsim.skipchars
        ignore = hdlsim.ignore
        languageVersion = hdlsim.languageVersion

        if hdl == "VHDL":
            if languageVersion is not None:
                kwargs['VHDLVersion'] = languageVersion
            else:
                kwargs['VHDLVersion'] = "93"
            inst = toVHDL(func, *args, **kwargs)
        else:
            inst = toVerilog(func, *args, **kwargs)

        if hdl == "VHDL":
            if not os.path.exists("work_%(topname)s" % vals):
                os.mkdir("work_%(topname)s" % vals)
        if hdlsim.name in ('vlog', 'vcom', 'vcom-coverage'):
            if not os.path.exists("work_vsim"):
                try:
                    subprocess.call("vlib work_%(topname)s_vlog" % vals, shell=True)
                    subprocess.call("vlib work_%(topname)s_vcom" % vals, shell=True)
                    subprocess.call("vmap work_%(topname)s_vlog work_%(topname)s_vlog" % vals, shell=True)
                    subprocess.call("vmap work_%(topname)s_vcom work_%(topname)s_vcom" % vals, shell=True)
                except:
                    pass

        ret = subprocess.call(analyze, shell=True)
        if ret != 0:
            print("Analysis failed", file=sys.stderr)
            return ret

        if self._analyzeOnly:
            print("Analysis succeeded", file=sys.stderr)
            return 0

        f = tempfile.TemporaryFile(mode='w+t')
        sys.stdout = f
        sim = Simulation(inst)
        sim.run()
        sys.stdout = sys.__stdout__
        f.flush()
        f.seek(0)

        flines = f.readlines()
        f.close()
        if not flines:
            print("No MyHDL simulation output - nothing to verify",
                  file=sys.stderr)
            return 1

        if elaborate is not None:
            # print(elaborate)
            ret = subprocess.call(elaborate, shell=True)
            if ret != 0:
                print("Elaboration failed", file=sys.stderr)
                return ret

        g = tempfile.TemporaryFile(mode='w+t')
        # print(simulate)
        ret = subprocess.call(simulate, stdout=g, shell=True)
    #    if ret != 0:
    #        print "Simulation run failed"
    #        return
        g.flush()
        g.seek(0)

        glines = g.readlines()[skiplines:]
        if ignore:
            for p in ignore:
                glines = [line for line in glines if not line.startswith(p)]
        glines = [line.replace('\0', '') for line in glines]
        # limit diff window to the size of the MyHDL output
        # this is a hack to remove an eventual simulator postamble
        if len(glines) > len(flines):
            glines = glines[:len(flines)]
        glines = [line[skipchars:] for line in glines]
        flinesNorm = [line.lower() for line in flines]
        glinesNorm = [line.lower() for line in glines]
        g = difflib.unified_diff(flinesNorm, glinesNorm, fromfile=hdlsim.name,
                                 tofile=hdl)

        MyHDLLog = "%s_MyHDL.log" % vals['topname']
        HDLLog = "%s_%s.log" % (vals['topname'], hdlsim.name)
        diffLog = "%s_diff.log" % vals['topname']
        try:
            os.remove(MyHDLLog)
            os.remove(HDLLog)
        except:
            pass

        s = "".join(g)
        f = open(MyHDLLog, 'w+t')
        g = open(HDLLog, 'w+t')
        d = open(diffLog, 'w+t')
        f.writelines(flines)
        g.writelines(glines)
        d.write(s)
        f.close()
        g.close()
        d.close()

        if not s:
            print("Conversion verification succeeded", file=sys.stderr)
        else:
            print("Conversion verification failed", file=sys.stderr)
            # print >> sys.stderr, s ,
            return 1

        return 0


verify = _VerificationClass(analyzeOnly=False)
analyze = _VerificationClass(analyzeOnly=True)
