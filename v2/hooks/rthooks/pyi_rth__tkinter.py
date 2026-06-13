import os
import sys

tcldir = os.path.join(sys._MEIPASS, "tcl", "tcl8.6")
tkdir = os.path.join(sys._MEIPASS, "tcl", "tk8.6")

if os.path.isdir(tcldir):
    os.environ["TCL_LIBRARY"] = tcldir
else:
    raise FileNotFoundError('Tcl data directory "%s" not found.' % tcldir)

if os.path.isdir(tkdir):
    os.environ["TK_LIBRARY"] = tkdir
else:
    raise FileNotFoundError('Tk data directory "%s" not found.' % tkdir)
