#!/usr/bin/env python3

"""
This routine parses plain-text parameter files that list runtime
parameters for use in our codes.  The general format of a parameter
is:

max_step                            integer            1
small_dt                            real               1.d-10
xlo_boundary_type                   character          ""
octant                              logical            .false.

This specifies the runtime parameter name, datatype, and default
value.

An optional 4th column can be used to indicate the priority -- if,
when parsing the collection of parameter files, a duplicate of an
existing parameter is encountered, the value from the one with
the highest priority (largest integer) is retained.

This script takes a template file and replaces keywords in it
(delimited by @@...@@) with the Fortran code required to
initialize the parameters, setup a namelist, and allow for
commandline overriding of their defaults.

"""

from __future__ import print_function

import sys
import getopt

header="""\
! DO NOT EDIT THIS FILE!!!
!
! This file is automatically generated by write_probin.py at
! compile-time.
!
! To add a runtime parameter, do so by editting the appropriate _parameters
! file.

"""

class Parameter(object):
    # the simple container to hold the runtime parameters
    def __init__(self):
        self.var = ""
        self.type = ""
        self.value = ""
        self.priority = 0

    def __lt__(self, other):
        return self.priority < other.priority


def get_next_line(fin):
    # return the next, non-blank line, with comments stripped
    line = fin.readline()

    pos = str.find(line, "#")

    while (pos == 0 or str.strip(line) == "") and line:
        line = fin.readline()
        pos = str.find(line, "#")

    return line[:pos]


def parse_param_file(params_list, param_file, other_list=None):
    """read all the parameters in a given parameter file and add valid
    parameters to the params list.

    if otherList is present, we will search through it to make sure
    we don't add a duplicate parameter.

    """

    if other_list == None:
        other_list = []

    err = 0

    try: f = open(param_file, "r")
    except IOError:
        sys.exit("write_probin.py: ERROR: file {} does not exist".format(param_file))
    else:
        print("write_probin.py: working on parameter file {}...".format(param_file))

    line = get_next_line(f)

    while line and not err:

        fields = line.split()

        if not len(fields) >= 3:
            print("write_probin.py: ERROR: missing one or more fields in parameter definition.")
            err = 1
            continue

        current_param = Parameter()

        current_param.var   = fields[0]
        current_param.type  = fields[1]
        current_param.value = fields[2]

        try: current_param.priority = int(fields[3])
        except: pass

        skip = 0

        # check to see if this parameter is defined in the current list
        # if so, keep the one with the highest priority
        p_names = [p.var for p in params_list]
        try: idx = p_names.index(current_param.var)
        except:
            idx = -1
        else:
            if params_list[idx] < current_param:
                params_list.pop(idx)
            else:
                skip = 1

        # don't allow it to be a duplicate in the other_list
        o_names = [p.var for p in other_list]
        try: idx2 = o_names.index(current_param.var)
        except:
            pass
        else:
            print("write_probin.py: ERROR: parameter {} already defined.".format(current_param.var))
            err = 1

        if not err == 1 and not skip == 1:
            params_list.append(current_param)

        line = get_next_line(f)

    return err


def abort(outfile):
    """ abort exits when there is an error.  A dummy stub file is written
    out, which will cause a compilation failure """

    fout = open(outfile, "w")
    fout.write("There was an error parsing the parameter files")
    fout.close()
    sys.exit(1)


def write_probin(probin_template, param_A_files, param_B_files,
                 namelist_name, out_file):

    """ write_probin will read through the list of parameter files and
    output the new out_file """

    paramsA = []
    paramsB = []

    try:
        print(" ")
        print("write_probin.py: creating {}".format(out_file))
    except:
        sys.exit("write_probin.py: ERROR: your version of Python is unsupported. Please update to at least Python 2.7.")

    # read the parameters defined in the parameter files

    for f in param_A_files:
        err = parse_param_file(paramsA, f)
        if err: abort(out_file)

    for f in param_B_files:
        err = parse_param_file(paramsB, f, other_list=paramsA)
        if err: abort(out_file)

    # params will hold all the parameters (from both lists A and B)
    params = paramsA + paramsB


    # open up the template

    try: ftemplate = open(probin_template, "r")
    except IOError:
        sys.exit("write_probin.py: ERROR: file {} does not exist".format(probin_template))

    template_lines = [line for line in ftemplate]

    ftemplate.close()

    # output the template, inserting the parameter info in between the @@...@@
    fout = open(out_file, "w")

    fout.write(header)

    for line in template_lines:

        index = line.find("@@")

        if index >= 0:
            index2 = line.rfind("@@")

            keyword = line[index+len("@@"):index2]
            indent = index*" "

            if keyword in ["declarationsA", "declarationsB"]:
                if keyword == "declarationsA":
                    pm = paramsA
                elif keyword == "declarationsB":
                    pm = paramsB

                #print([k.var for k in pm])

                # declaraction statements
                for n in range(len(pm)):

                    type = pm[n].type

                    if type == "real":
                        fout.write("{}real (kind=dp_t), save, public :: {} = {}\n".format(
                            indent, pm[n].var, pm[n].value))
                        fout.write("{}!$acc declare create({})\n".format(indent, pm[n].var))

                    elif type == "character":
                        fout.write("{}character (len=256), save, public :: {} = {}\n".format(
                            indent, pm[n].var, pm[n].value))
                        fout.write("{}!$acc declare create({})\n".format(indent, pm[n].var))

                    elif type == "integer":
                        fout.write("{}integer, save, public :: {} = {}\n".format(
                            indent, pm[n].var, pm[n].value))
                        fout.write("{}!$acc declare create({})\n".format(indent, pm[n].var))

                    elif type == "logical":
                        fout.write("{}logical, save, public :: {} = {}\n".format(
                            indent, pm[n].var, pm[n].value))
                        fout.write("{}!$acc declare create({})\n".format(indent, pm[n].var))

                    else:
                        print("write_probin.py: invalid datatype for variable {}".format(pm[n].var))

                if len(pm) == 0:
                    if keyword == "declarationsA":
                        fout.write("{}integer, save, public :: a_dummy_var = 0\n".format(indent))
                    else:
                        fout.write("\n")


            elif keyword == "namelist":

                for n in range(len(params)):
                    fout.write("{}namelist /{}/ {}\n".format(
                        indent, namelist_name, params[n].var))

                if len(params) == 0:
                    fout.write("{}namelist /{}/ a_dummy_var\n".format(
                        indent, namelist_name))

            elif keyword == "defaults":

                for n in range(len(params)):
                    fout.write("{}{} = {}\n".format(
                        indent, params[n].var, params[n].value))

            elif keyword == "commandline":

                for n in range(len(params)):

                    fout.write("{}case (\'--{}\')\n".format(indent, params[n].var))
                    fout.write("{}   farg = farg + 1\n".format(indent))

                    if params[n].type == "character":
                        fout.write("{}   call get_command_argument(farg, value = {})\n".format(
                            indent, params[n].var))

                    else:
                        fout.write("{}   call get_command_argument(farg, value = fname)\n".format(indent))
                        fout.write("{}   read(fname, *) {}\n".format(indent, params[n].var))

            elif keyword == "printing":

                fout.write("100 format (1x, a3, 2x, a32, 1x, \"=\", 1x, a)\n")
                fout.write("101 format (1x, a3, 2x, a32, 1x, \"=\", 1x, i10)\n")
                fout.write("102 format (1x, a3, 2x, a32, 1x, \"=\", 1x, g20.10)\n")
                fout.write("103 format (1x, a3, 2x, a32, 1x, \"=\", 1x, l)\n")

                for n in range(len(params)):

                    type = params[n].type

                    if type == "logical":
                        cmd = "merge(\"   \", \"[*]\", {} .eqv. {})".format(params[n].var, params[n].value)
                    else:
                        cmd = "merge(\"   \", \"[*]\", {} == {})".format(params[n].var, params[n].value)

                    if type == "real":
                        fout.write("{}write (unit,102) {}, &\n \"{}\", {}\n".format(
                            indent, cmd, params[n].var, params[n].var) )

                    elif type == "character":
                        fout.write("{}write (unit,100) {}, &\n \"{}\", trim({})\n".format(
                            indent, cmd, params[n].var, params[n].var) )

                    elif type == "integer":
                        fout.write("{}write (unit,101) {}, &\n \"{}\", {}\n".format(
                            indent, cmd, params[n].var, params[n].var) )

                    elif type == "logical":
                        fout.write("{}write (unit,103) {}, &\n \"{}\", {}\n".format(
                            indent, cmd, params[n].var, params[n].var) )

                    else:
                        print("write_probin.py: invalid datatype for variable {}".format(params[n].var))


            elif keyword == "acc":

                fout.write(indent + "!$acc update &\n")
                fout.write(indent + "!$acc device(")

                for n, p in enumerate(params):
                    fout.write("{}".format(p.var))

                    if n == len(params)-1:
                        fout.write(")\n")
                    else:
                        if n % 3 == 2:
                            fout.write(") &\n" + indent + "!$acc device(")
                        else:
                            fout.write(", ")

        else:
            fout.write(line)

    print(" ")
    fout.close()


if __name__ == "__main__":

    try: opts, _ = getopt.getopt(sys.argv[1:], "t:o:n:", ["pa=", "pb="])

    except getopt.GetoptError:
        print("write_probin.py: invalid calling sequence")
        sys.exit(2)

    probin_template = ""
    out_file = ""
    namelist_name = ""
    param_A_files_str = ""
    param_B_files_str = ""

    for o, a in opts:

        if o == "-t":
            probin_template = a

        if o == "-o":
            out_file = a

        if o == "-n":
            namelist_name = a

        if o == "--pa":
            param_A_files_str = a

        if o == "--pb":
            param_B_files_str = a


    if (probin_template == "" or out_file == "" or namelist_name == ""):
        sys.exit("write_probin.py: ERROR: invalid calling sequence")

    param_A_files = param_A_files_str.split()
    param_B_files = param_B_files_str.split()

    write_probin(probin_template, param_A_files, param_B_files,
                 namelist_name, out_file)
