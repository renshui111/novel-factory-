import os
import sys

tcldir = os.path.join(sys._MEIPASS, "tcl", "tcl8.6")
tkdir = os.path.join(sys._MEIPASS, "tcl", "tk8.6")

if os.path.isdir(tcldir):
    os.environ["TCL_LIBRARY"] = tcldir
if os.path.isdir(tkdir):
    os.environ["TK_LIBRARY"] = tkdir

# Fallback: try alternate paths
if "TCL_LIBRARY" not in os.environ:
    for alt in [os.path.join(sys._MEIPASS, "tcl8.6"), os.path.join(sys._MEIPASS, "_tcl_data")]:
        if os.path.isdir(alt):
            os.environ["TCL_LIBRARY"] = alt
            break
if "TK_LIBRARY" not in os.environ:
    for alt in [os.path.join(sys._MEIPASS, "tk8.6"), os.path.join(sys._MEIPASS, "_tk_data")]:
        if os.path.isdir(alt):
            os.environ["TK_LIBRARY"] = alt
            break
