#!/bin/bash

ANSI_RED=`tput setaf 1`
ANSI_GREEN=`tput setaf 2`
ANSI_CYAN=`tput setaf 6`
ANSI_RESET=`tput sgr0`

run_test() {
  echo -e "\n${ANSI_CYAN}running test: $@ ${ANSI_RESET}"
  "$@"
  if [ $? -ne 0 ]; then
    echo "${ANSI_RED}[FAILED] $@ ${ANSI_RESET}"
    foundError=1
  else
    echo "${ANSI_GREEN}[PASSED] $@ ${ANSI_RESET}"
  fi
  echo
}

foundError=0
echo -e "Running $CI_TARGET tests\n"

CI_TARGET=${CI_TARGET:-core}
if [ "$CI_TARGET" == "core" ]; then
  run_test make -C myhdl/test/core
  run_test make -C myhdl/test/core2
elif [ "$CI_TARGET" == "icarus" ]; then
  run_test make -C "myhdl/test/conversion/general" icarus
  run_test make -C cosimulation/icarus test
  run_test make -C myhdl/test/conversion/toVerilog
elif [ "$CI_TARGET" == "ghdl" ]; then
  run_test make -C "myhdl/test/conversion/general" GHDL
  run_test make -C myhdl/test/conversion/toVHDL GHDL
elif [ "$CI_TARGET" == "bugs" ]; then
  run_test make -C "myhdl/test/bugs" icarus
  run_test make -C "myhdl/test/bugs" GHDL
elif [ "$CI_TARGET" == "numeric" ]; then
  sudo -E cp vhdl/fixed_pck.vhdl vhdl/math_utility_pkg.vhdl /usr/lib/ghdl/lib/gcc/x86_64-linux-gnu/4.8/vhdl/src/ieee/.
  MYHDL_WORK_DIR = `pwd`
  cd /usr/lib/ghdl/lib/gcc/x86_64-linux-gnu/4.8/vhdl/v93/ieee
  sudo -E ghdl -a --ieee=none --std=93 -P../std --work=ieee ../../../src/ieee/math_utility_pkg.vhdl
  sudo -E ghdl -a --ieee=none --std=93 -P../std --work=ieee ../../../src/ieee/fixed_pkg.vhdl
  cd $MYHDL_WORK_DIR
  run_test make -C myhdl/test/numeric
  run_test make -C myhdl/test/conversion/numeric
fi

exit $foundError
