all:  GHDL

GHDL:
	py.test GHDL.py test_ops.py

vlog:
	py.test vlog.py test_ops.py

vcom:
	py.test vcom.py test_ops.py

icarus:
	py.test icarus.py test_ops.py

cver:
	py.test cver.py test_ops.py

clean:
	- rm *.o *.out *.v *.vhd *.pyc *~ *.vcd* *.log *_ghdl
