from __future__ import absolute_import
#  This file is part of the myhdl library, a Python package for using
#  Python as a Hardware Description Language.
#
#  Copyright (C) 2003-2008 Jan Decaluwe
#
#  The myhdl library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public License as
#  published by the Free Software Foundation; either version 2.1 of the
#  License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

from __future__ import absolute_import
import myhdl

_version = myhdl.__version__.replace('.','')
_shortversion = _version.replace('dev','')

def _package(fixed=False):
    result = """\
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
"""
    if fixed:
        result += """
use ieee.fixed_pkg.all;
"""
    result += """ 
package pck_myhdl_%(version)s is

    attribute enum_encoding: string;

    function stdl (arg: boolean) return std_logic;

    function stdl (arg: integer) return std_logic;

    function to_unsigned (arg: boolean; size: natural) return unsigned;

    function to_signed (arg: boolean; size: natural) return signed;

    function to_integer(arg: boolean) return integer;

    function to_integer(arg: std_logic) return integer;

    function to_unsigned (arg: std_logic; size: natural) return unsigned;

    function to_signed (arg: std_logic; size: natural) return signed;

    function bool (arg: std_logic) return boolean;

    function bool (arg: unsigned) return boolean;

    function bool (arg: signed) return boolean;

    function bool (arg: integer) return boolean;

    function "-" (arg: unsigned) return signed;
"""    
    if fixed:
        result += """
    function bool (arg: sfixed) return boolean;

    function floor (arg: sfixed) return sfixed;
"""
    result += """
end pck_myhdl_%(version)s;


package body pck_myhdl_%(version)s is

    function stdl (arg: boolean) return std_logic is
    begin
        if arg then
            return '1';
        else
            return '0';
        end if;
    end function stdl;

    function stdl (arg: integer) return std_logic is
    begin
        if arg /= 0 then
            return '1';
        else
            return '0';
        end if;
    end function stdl;


    function to_unsigned (arg: boolean; size: natural) return unsigned is
        variable res: unsigned(size-1 downto 0) := (others => '0');
    begin
        if arg then
            res(0):= '1';
        end if;
        return res;
    end function to_unsigned;

    function to_signed (arg: boolean; size: natural) return signed is
        variable res: signed(size-1 downto 0) := (others => '0');
    begin
        if arg then
            res(0) := '1';
        end if;
        return res; 
    end function to_signed;

    function to_integer(arg: boolean) return integer is
    begin
        if arg then
            return 1;
        else
            return 0;
        end if;
    end function to_integer;

    function to_integer(arg: std_logic) return integer is
    begin
        if arg = '1' then
            return 1;
        else
            return 0;
        end if;
    end function to_integer;

    function to_unsigned (arg: std_logic; size: natural) return unsigned is
        variable res: unsigned(size-1 downto 0) := (others => '0');
    begin
        res(0):= arg;
        return res;
    end function to_unsigned;

    function to_signed (arg: std_logic; size: natural) return signed is
        variable res: signed(size-1 downto 0) := (others => '0');
    begin
        res(0) := arg;
        return res; 
    end function to_signed;

    function bool (arg: std_logic) return boolean is
    begin
        return arg = '1';
    end function bool;

    function bool (arg: unsigned) return boolean is
    begin
        return arg /= 0;
    end function bool;

    function bool (arg: signed) return boolean is
    begin
        return arg /= 0;
    end function bool;

    function bool (arg: integer) return boolean is
    begin
        return arg /= 0;
    end function bool;

    function "-" (arg: unsigned) return signed is
    begin
        return - signed(resize(arg, arg'length+1));
    end function "-";
"""
    if fixed:
        result += """
    function bool (arg: sfixed) return boolean is
    begin
        return arg /= 0;
    end function bool;

    function floor (arg: sfixed) return sfixed is
        variable result:    sfixed(arg'high downto arg'low);
    begin
        result := arg;
        if result'high <= 0 then
            result := (others => '0');
        elsif result'low < 0 then
            result(-1 downto result'low) := (others => '0');
        end if;
        return result;
    end function floor;
"""
    result += """
end pck_myhdl_%(version)s;

"""
    result %= {'version' : _shortversion}
    
    return result
