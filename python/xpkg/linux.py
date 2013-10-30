# Author: Joseph Lisee <jlisee@gmail.com>

__doc__ = """
Functionality that is very linux specific goes in this module.
"""

# Python Imports
import os
import re
import sys

# Library Imports
from elftools.elf.elffile import ELFFile
from elftools.elf.segments import InterpSegment

# Project Imports
from xpkg import paths
from xpkg import util


def readelf_interp(binary_path):
    """
    This reads the program interpreter (INTERP), usually ld-linux.so from the
    given binary. It will return None if it can't find it.
    """

    # Use pyelftools to extract the program header
    elffile = ELFFile(open(binary_path))

    # Go through the segments until we INTERP segment
    interp = None

    for segment in elffile.iter_segments():
        if isinstance(segment, InterpSegment):
            interp = segment.get_interp_name()

    return interp


def update_ld_so_symlink(root, target_dir = None):
    """
    Maintains a symlink from <env_dir>/lib/ld-linux-xpkg.so to the
    Environment's local one or the system copy.

      root - the root directory of our environment
      target_dir - where to place the symlink (defaults to root)
    """

    # Use the current Python interpreters ld-linux path as the system
    # version
    interp_path = readelf_interp(sys.executable)

    if interp_path is None:
        msg = 'Could not find ELF program interpreter for: ' + sys.executable
        raise Exception(msg)

    # Search for system copies (this is kind of hacky right now)
    search_dirs = [
        'lib',
        'lib64',
        os.path.join('lib', 'x86_64-linux-gnu'),
        os.path.join('lib', 'i386-linux-gnu')
    ]
    search_paths = [os.path.join(root, d) for d in search_dirs]

    search_patterns = [
        'ld-2.[0-9]+.so',
        'ld64-uClibc.so.0'
    ]
    search_regex = [re.compile(p) for p in search_patterns]

    env_interp = None

    for search_dir in [p for p in search_paths if os.path.exists(p)]:
        for filename in os.listdir(search_dir):
            for regex in search_regex:
                match = regex.match(filename)

                if match and match.span()[1] == len(filename):
                    env_interp = os.path.join(search_dir, filename)

    # Chose the environment interp the source one
    if env_interp:
        source_interp = env_interp
    else:
        source_interp = interp_path

    # Remove the existing symlink if present
    if target_dir is None:
        target_root = root
    else:
        target_root = target_dir

    link_target = paths.ld_linux_path(target_root)

    if os.path.lexists(link_target):
        os.remove(link_target)

    # Make sure the target directory is created
    link_dir, _ = os.path.split(link_target)
    util.ensure_dir(link_dir)

    # Place down our symlink
    os.symlink(source_interp, link_target)

    return link_target
