# Author: Joseph Lisee <jlisee@gmail.com>

__doc__ = """
Functions to return common xpkg paths.
"""

# Python Imports
import os


def ld_linux_path(root):
    """
    Returns the path to our major ld-so symlink. (Which allows us to change
    which ld-so we are actively using without patching a bunch of binaries)
    """

    return os.path.join(root, 'lib', 'ld-linux-xpkg.so')
