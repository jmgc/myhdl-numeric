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

def _package(version=None, fixed=False):
    result = """\
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
"""
    if version == "93":
        result += """
use ieee.standard_additions.all;
use ieee.numeric_std_additions.all;
"""
    if fixed:
        result += """
use ieee.fixed_float_types.all;
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
    result += """
    function c_l2u (arg: std_logic; size: integer) return unsigned;

    function c_l2s (arg: std_logic; size: integer) return signed;

    function c_i2u (arg: integer; size: integer) return unsigned;

    function c_i2s (arg: integer; size: integer) return signed;

    function c_u2u (arg: unsigned; size: integer) return unsigned;

    function c_u2s (arg: unsigned; size: integer) return signed;

    function c_s2u (arg: signed; size: integer) return unsigned;

    function c_s2s (arg: signed; size: integer) return signed;
"""
    if fixed:
        result += """
    function bool (arg: sfixed) return boolean;

    function floor (arg: sfixed) return sfixed;

    function c_l2f (arg: std_logic; high: integer; low: integer) return sfixed;

    function c_i2f (arg: integer; high: integer; low: integer) return sfixed;

    function c_u2f (arg: unsigned; high: integer; low: integer) return sfixed;

    function c_s2f (arg: signed; high: integer; low: integer) return sfixed;

    function c_f2f (arg: sfixed; high: integer; low: integer) return sfixed;

    function c_f2u (arg: sfixed; size: integer) return unsigned;

    function c_f2s (arg: sfixed; size: integer) return signed;

    function t_f2u (arg: sfixed; size: integer) return unsigned;

    function t_f2s (arg: sfixed; size: integer) return signed;

    function t_f2f (arg: sfixed; high: integer; low: integer) return sfixed;

    function t_u2f (arg: unsigned; high: integer; low: integer) return sfixed;

    function t_s2f (arg: signed; high: integer; low: integer) return sfixed;
    
    function c_u2r (arg: unsigned) return real;
    
    function c_s2r (arg: signed) return real;

    function c_str2f (value: std_logic_vector; high: integer; low: integer)
            return sfixed;

    function c_str2f (value: std_logic_vector) return sfixed;
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
    result += """
    function c_l2u (arg: std_logic; size: integer) return unsigned is
        variable result: unsigned((size - 1) downto 0);
    begin
        result := (others => '0');
        result(0) := arg;
        return result;
    end function c_l2u;

    function c_l2s (arg: std_logic; size: integer) return signed is
        constant r_high: integer := maximum(size - 1, 1);
        variable result: signed(r_high downto 0);
    begin
        result := (others => '0');
        result(0) := arg;
        return result;
    end function c_l2s;

    function c_i2u (arg: integer; size: integer) return unsigned is
    begin
        return unsigned(to_signed(arg, size + 1)((size-1) downto 0));
    end function c_i2u;

    function c_i2s (arg: integer; size: integer) return signed is
    begin
        return to_signed(arg, size + 1)((size-1) downto 0);
    end function c_i2s;

    function c_u2u (arg: unsigned; size: integer) return unsigned is
    begin
        return resize(arg, size);
    end function c_u2u;

    function c_u2s (arg: unsigned; size: integer) return signed is
    begin
        return signed(resize(arg, size));
    end function c_u2s;

    function c_s2u (arg: signed; size: integer) return unsigned is
        constant t_size: natural    := size + 1;
        constant o_left: natural    := size - 1;
        variable tmp: unsigned(size downto 0);
    begin
        tmp := unsigned(resize(arg, t_size));
        return tmp(o_left downto 0);
    end function c_s2u;

    function c_s2s (arg: signed; size: integer) return signed is
        constant t_size: natural    := size + 1;
        constant o_left: natural    := size - 1;
        variable tmp: signed(size downto 0);
    begin
        tmp := resize(arg, t_size);
        return tmp(o_left downto 0);
    end function c_s2s;
"""
    if fixed:
        result += """
    function bool (arg: sfixed) return boolean is
    begin
        return arg /= 0;
    end function bool;

    function floor (arg: sfixed) return sfixed is
        constant left_index:    integer := maximum(arg'left, 1); 
        variable result:    sfixed(left_index downto 0);
    begin
        result := resize(arg, result'left, result'right, fixed_overflow_style,
                        fixed_truncate);
        return result;
    end function floor;

    function c_l2f (arg: std_logic; high: integer; low: integer) return sfixed is
        constant r_high: integer := maximum(high, 1);
        constant r_low: integer := minimum(low, 0);
        variable result: sfixed(r_high downto r_low);
    begin
        result := (others => '0');
        result(0) := arg;
        return result;
    end function c_l2f;

    function c_i2f (arg: integer; high: integer; low: integer) return sfixed is
        variable tmp: sfixed(maximum(high, 1) downto 0);
    begin
        tmp := to_sfixed(arg, tmp'left, 0);
        return resize(tmp, high, low);
    end function c_i2f;

    function c_f2u (arg: sfixed; size: integer) return unsigned is
    begin
        return to_unsigned(to_ufixed(arg), size);
    end function c_f2u;

    function c_f2s (arg: sfixed; size: integer) return signed is
    begin
        return to_signed(arg, size);
    end function c_f2s;

    function c_f2f (arg: sfixed; high: integer; low: integer) return sfixed is
    begin
        return resize(arg, high, low);
    end function c_f2f;

    function c_u2f (arg: unsigned; high: integer; low: integer) return sfixed is
    begin
        return resize(to_sfixed(to_ufixed(arg)), high, low);
    end function c_u2f;

    function c_s2f (arg: signed; high: integer; low: integer) return sfixed is
    begin
        return resize(to_sfixed(arg), high, low);
    end function c_s2f;

    function t_u2f (arg: unsigned; high: integer; low: integer) return sfixed is
    begin
        return to_sfixed(to_ufixed(arg, high, low, fixed_wrap, fixed_truncate))(high downto low);
    end function t_u2f;

    function t_s2f (arg: signed; high: integer; low: integer) return sfixed is
    begin
        return to_sfixed(to_ufixed(unsigned(arg), high, low, fixed_wrap, fixed_truncate))(high downto low);
    end function t_s2f;

    function t_f2f (arg: sfixed; high: integer; low: integer) return sfixed is
    begin
        return resize(arg, high + 1, low, fixed_wrap, fixed_truncate)(high downto low);
    end function t_f2f;

    function t_f2u (arg: sfixed; size: integer) return unsigned is
    begin
        return to_unsigned(to_ufixed(arg), size, fixed_wrap, fixed_truncate);
    end function t_f2u;

    function t_f2s (arg: sfixed; size: integer) return signed is
    begin
        return to_signed(arg, size + 1, fixed_wrap, fixed_truncate)(size-1 downto 0);
    end function t_f2s;

    function c_u2r (arg: unsigned) return real is
    begin
        return to_real(to_ufixed(arg));
    end function c_u2r;
    
    function c_s2r (arg: signed) return real is
    begin
        return to_real(to_sfixed(arg));
    end function c_s2r;

    function c_str2f (value: std_logic_vector) return sfixed is
    begin
        return c_str2f(value, value'length - 1, 0);
    end function c_str2f;

    function c_str2f (value: std_logic_vector; high: integer; low: integer)
            return sfixed is
        variable result : sfixed (high downto low) ;
    begin
        result := sfixed(value);
        return result;
    end function c_str2f;
"""
    result += """
end pck_myhdl_%(version)s;

"""
    result %= {'version' : _shortversion}
    
    return result
