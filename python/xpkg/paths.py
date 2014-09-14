# Author: Joseph Lisee <jlisee@gmail.com>

__doc__ = """
Functions to return common xpkg paths.
"""

# Python Imports
import os

# Project Imports
from xpkg import envvars

def ld_linux_path(root):
    """
    Returns the path to our major ld-so symlink. (Which allows us to change
    which ld-so we are actively using without patching a bunch of binaries)
    """

    return os.path.join(root, 'lib', 'ld-linux-xpkg.so')


def local_cache_dir():
    """
    Local user cache directory.
    """

    if envvars.xpkg_local_cache_var in os.environ:
        return os.environ[envvars.xpkg_local_cache_var]
    else:
        return os.path.expanduser(os.path.join('~', '.xpkg', 'cache'))
