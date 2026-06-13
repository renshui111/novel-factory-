# Override: always include tkinter, never exclude it
import os, sys

def pre_find_module_path(hook_api):
    # Do NOT exclude tkinter - force inclusion
    # Return None instead of empty list to keep tkinter
    return None
