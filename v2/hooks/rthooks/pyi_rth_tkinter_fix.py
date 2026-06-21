import os, sys

if getattr(sys, "frozen", False):
    base = sys._MEIPASS
    tcl_dir = os.path.join(base, "_tcl_data")
    tk_dir = os.path.join(base, "_tk_data")
    if os.path.exists(tcl_dir):
        os.environ["TCL_LIBRARY"] = tcl_dir
    if os.path.exists(tk_dir):
        os.environ["TK_LIBRARY"] = tk_dir