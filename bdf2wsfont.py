#!/usr/pkg/bin/python3.7 -tt

from __future__ import print_function
import collections
import fileinput
import getopt
import os.path
import re
import sys
import textwrap

"""
Title  : Simple BDF to wsfont *.h file converter
Version: 1.00
Date   : 2019-04-22
Autor  : Piotr Meyer <aniou@smutek.pl>
"""


"""
Copyright (c) 2019 Piotr Meyer <aniou@smutek.pl>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.
"""

verbose     = False
quiet       = False


# XXX: make proper help
# -p - just print all data from BDF
# -h - show usage()
# -q - quiet, now does noting
# -v - verbose, now does slightly more, XXX
# -t - conversion table, from tables/ 
# -i - input BDF file
# -o - output file, XXX: not supported

def usage():
    print("usage: %s [-h] [-p] [-q] [-v]" % os.path.basename(sys.argv[0]), 
          "-t <conversion_table> [-i <bdf_file>]")
    return


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "phqvt:i:o:")
    except getopt.GetoptError as err:
        print(err)      # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    if len(opts) == 0:
        usage()
        sys.exit(2)

    table_file  = ""
    bdf_file    = ""
    output_file = ""
    just_print  = False

    for o, a in opts:
        if o == "-v":
            verbose = True
        elif o == "-q":
            quiet = True
        elif o == "-p":
            just_print = True
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-t", "--table"):
            table_file = a
        elif o in ("-i", "--input"):
            bdf_file = a
        elif o in ("-o", "--output"):
            print("Warning: output file not supported")
            output_file = a
        else:
            assert False, "unhandled option"


    conversion_table = read_conversion_table(table_file)    
    (font_prop, font_data) = read_from_bdf(bdf_file)

    # print all characters or just ones, selected by 
    # conversion table
    #
    if just_print == True:
        count = 0
        for char in font_data:
            print_char_image(count, font_data[char])
            count=count+1
    else:
    #
    # XXX: ATM we assume that BDF file is complete and
    #      don't replace missing characters by U+FFFD
    #      https://www.utf8icons.com/character/65533/replacement-character
    #      - instead program simply crashes
    #
        print_header(font_prop, bdf_file)
        for x in range(0, 256):
            print_char_image(x, font_data[conversion_table[x]])
        print_footer()


    sys.exit(0)


def print_header(font_prop, bdf_file):
    tokens = font_prop['FONTBOUNDINGBOX'].split()
    width  = int(tokens[0])
    height = int(tokens[1])
    name   = os.path.basename(bdf_file)[:-4].replace('-', '_')
    lname  = "%s-%ix%i" % (name, width, height)
    stride = int(width / 8) + (width % 8 > 0)          # w ilu bajtach

    header = """\
    static u_char {name}_data[];

    static struct wsdisplay_font {name}_prop = {{
            "{lname}",                         /* typeface name */
            0,                              /* firstchar */
            255,                            /* numchars */
            WSDISPLAY_FONTENC_IBM,          /* encoding */
            {width},                        /* width */
            {height},                       /* height */
            {stride},                       /* stride */
            WSDISPLAY_FONTORDER_L2R,        /* bit order */
            WSDISPLAY_FONTORDER_L2R,        /* byte order */
            {name}_data                     /* data */
    }};
    
    static u_char {name}_data[] = {{""".format(lname=lname, name=name, width=width, height=height, stride=stride)
    print(textwrap.dedent(header))
    return

def print_footer():
    print("};\n")
    return


def print_char_image(char_number, char_data):
    """
    """
    p = char_data['prop']
    print("\n\t/* char 0x%02x (%03i) unicode: 0x%04x (%i) name: %s */" \
              % (char_number, char_number, 
                 int(p['ENCODING']), int(p['ENCODING']), 
                 p['STARTCHAR']))
              
    for hex_string in char_data['bitmap']:
        bit_length = len(hex_string) * 4  # len/2(bytes per hex)*8(bits)
        x = int(hex_string, 16)

        binary_string = '{:0{size}b}'.format(x, size=bit_length)
        graph_line    = binary_string.replace('1', '#').replace('0', '.')

        print("\t", end='') 
        for v in re.findall('.{1,2}', hex_string):  # or ..? for odd strings
            print("0x%s" % v.lower(), end=", ")
        print("\t/* %s */" % graph_line)

    return



def read_from_bdf(bdf_file):
    fh = open(bdf_file, "r")
    
    char_name   = None
    char_number = None
    bitmap      = False
    meta        = True
    char_data   = []
    font_prop   = {}
    font_data   = {}
    char_prop   = {}

    for line in fh:
        line   = line.strip()
        tokens = line.split(maxsplit=1)
        t      = tokens[0]

        if t == 'COMMENT':
            continue

        #--------------------------------------------------------------
        # short loop for meta-data read
        if meta == True:
            if t == 'CHARS':
                meta = False
                font_prop[t] = tokens[1]
                #print(font_prop)
                continue

            if t in ('STARTPROPERTIES', 'ENDPROPERTIES'):
                continue

            font_prop[t] = tokens[1]
            continue

        #--------------------------------------------------------------
        if t == 'ENDFONT':
            continue

        # meta data already read, now individual chars are processed
        if t == 'ENDCHAR':
            assert bitmap      != False
            assert char_number != None
            bitmap  = False

            if verbose == True:
                print("%s %i" % (char_name, char_number))
                print(char_data)
                print(char_prop)
                print("-"*10)

            font_data[char_number] = {}
            font_data[char_number]['bitmap'] = char_data
            font_data[char_number]['prop']  = char_prop

            char_number = None
            char_name   = None
            char_data   = []
            char_prop   = {}
            continue

        if bitmap == True:
            char_data.append(t)
            continue

        if t == 'ENCODING':
            char_number = int(tokens[1])

        if t == 'STARTCHAR':
            char_name = tokens[1]
     
        if t == 'BITMAP':
            bitmap   = True
            char_data = []
            continue

        #print(">", line)
        char_prop[t] = tokens[1]

    return(font_prop, font_data)

#
# rich set of conversion tables exists already in uni/ subdir of
# terminus font package (series of unicode data, without ascii column)
# XXX: use them or create new procedure for both
#
def read_conversion_table(table_file):
    unicode_character = {}
    with open(table_file, "r") as fh:
        for line in fh:
            if line.startswith('#'): continue
            tokens = line.split()
            if len(tokens) == 0:
                continue
            char_number = int(tokens[0])
            unicode_hexcode = int(tokens[1], 16)
            unicode_character[char_number] = unicode_hexcode
    return unicode_character
        


if __name__ == "__main__":
    main()

# eof
