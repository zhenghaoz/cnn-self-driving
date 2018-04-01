import os
import platform
import subprocess


def open_file_xdg(path):
    """
    Open file or directory in system's file manager.
    :param path: file/directory path
    """
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
