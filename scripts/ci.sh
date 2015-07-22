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
elif [ "$CI_TARGET" == "iverilog" ]; then
  run_test make -C "myhdl/test/conversion/general" iverilog
  run_test make -C cosimulation/icarus test
  run_test make -C myhdl/test/conversion/toVerilog
  run_test make -C "myhdl/test/bugs" iverilog
elif [ "$CI_TARGET" == "ghdl" ]; then
  ghdl --dispconfig
  sudo -E cp vhdl/fixed_pkg_c.vhdl vhdl/fixed_float_types_c.vhdl vhdl/numeric_std_additions.vhdl vhdl/standard_additions_c.vhdl /usr/lib/ghdl/lib/gcc/x86_64-linux-gnu/4.8/vhdl/src/ieee/.
  MYHDL_WORK_DIR=`pwd`
  cd /usr/lib/ghdl/lib/gcc/x86_64-linux-gnu/4.8/vhdl/lib/v93/ieee
  sudo -E ghdl -a --ieee=none --std=93 -P../std --work=ieee ../../../src/ieee/standard_additions_c.vhdl
  sudo -E ghdl -a --ieee=none --std=93 -P../std --work=ieee ../../../src/ieee/fixed_float_types_c.vhdl
  sudo -E ghdl -a --ieee=none --std=93 -P../std --work=ieee ../../../src/ieee/fixed_pkg_c.vhdl
  sudo -E ghdl -a --ieee=none --std=93 -P../std --work=ieee ../../../src/ieee/numeric_std_additions.vhdl
  cd $MYHDL_WORK_DIR
  run_test make -C "myhdl/test/conversion/general" ghdl
  run_test make -C myhdl/test/conversion/toVHDL ghdl
  run_test make -C "myhdl/test/bugs" ghdl
elif [ "$CI_TARGET" == "numeric" ]; then
  ghdl --dispconfig
  sudo -E cp vhdl/fixed_pkg_c.vhdl vhdl/fixed_float_types_c.vhdl vhdl/numeric_std_additions.vhdl vhdl/standard_additions_c.vhdl /usr/lib/ghdl/lib/gcc/x86_64-linux-gnu/4.8/vhdl/src/ieee/.
  MYHDL_WORK_DIR=`pwd`
  cd /usr/lib/ghdl/lib/gcc/x86_64-linux-gnu/4.8/vhdl/lib/v93/ieee
  sudo -E ghdl -a --ieee=none --std=93 -P../std --work=ieee ../../../src/ieee/standard_additions_c.vhdl
  sudo -E ghdl -a --ieee=none --std=93 -P../std --work=ieee ../../../src/ieee/fixed_float_types_c.vhdl
  sudo -E ghdl -a --ieee=none --std=93 -P../std --work=ieee ../../../src/ieee/fixed_pkg_c.vhdl
  sudo -E ghdl -a --ieee=none --std=93 -P../std --work=ieee ../../../src/ieee/numeric_std_additions.vhdl
  cd $MYHDL_WORK_DIR
  run_test make -C myhdl/test/numeric ghdl
  run_test make -C myhdl/test/conversion/numeric ghdl
fi

exit $foundError
