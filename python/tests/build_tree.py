#! /usr/bin/env python

# Author: Joseph Lisee <jlisee@gmail.com>

# Python Imports
import argparse
import hashlib
import os
import re
import shutil
import sys

# Project Imports
from xpkg import util

# Lets find the root of our source tree
cur_dir, _ = os.path.split(__file__)
root_dir = os.path.abspath(os.path.join(cur_dir, '..', '..'))


def setup_package(name, source_dir, file_dir, tree_dir):
    # Package files
    tar_path = os.path.join(file_dir, '%s.tar.gz' % name)

    util.make_tarball(tar_path, source_dir)

    # Get the hash
    md5sum = util.hash_file(open(tar_path), hashlib.md5)

    # Template the package file
    source_xdp = os.path.join(source_dir, '%s.xpd.pyt' % name)

    package_xpd = os.path.join(tree_dir, '%s.xpd' % name)

    args = {
        'filehash' : md5sum,
        'filepath' : tar_path,
        # These are not being modified by us
        'prefix' : '%(prefix)s',
        'jobs' : '%(jobs)s',
    }

    # Find all patch files
    patch_files =  [f for f in os.listdir(source_dir) if f.endswith('.patch')]
    patch_paths = [os.path.join(source_dir, f) for f in patch_files]

    # Compute their hashes
    patch_hashes = ['md5-' + util.hash_file(open(p), hashlib.md5)
                    for p in patch_paths]

    # Build a set of keys to put their hashes back into the system
    hash_keys = {'hash-' + p: hash_val
                 for (p, hash_val) in zip(patch_files, patch_hashes)}

    #print hash_keys
    args.update(hash_keys)

    # Template file
    util.template_file(source_xdp, package_xpd, args)

    # Copy the patch files into the tree directory
    for patch_path in patch_paths:
        shutil.copy(patch_path, tree_dir)


def create_test_repo(dest_dir):
    """
    Creates a set of Xpkg package files and matches source tar balls from our
    test projects.
    """

    # Create our target directories
    file_dir = os.path.join(dest_dir, 'files')
    tree_dir = os.path.join(dest_dir, 'tree')

    util.ensure_dir(file_dir)
    util.ensure_dir(tree_dir)

    # Unpack all the packages
    test_package_dir = os.path.join(root_dir, 'tests')
    for name in os.listdir(test_package_dir):
        full_path = os.path.join(test_package_dir, name)

        if os.path.isdir(full_path):
            # Do this for all the xpd files starting with name in the directory
            regex = re.compile('(%s\d*).xpd.pyt' % name)

            for file_name in os.listdir(full_path):
                match = regex.match(file_name)

                if match:
                    xpd_name = match.group(1)
                    setup_package(xpd_name, full_path, file_dir, tree_dir)


def main(argv = None):
    if argv is None:
        argv = sys.argv

    # Set up argument parsers
    parser = argparse.ArgumentParser(prog=argv[0])
    parser.add_argument('dest', metavar='DEST', type=str,
                        help='The location to put the tree')

    # parse some argument lists
    args = parser.parse_args(argv[1:])

    # Do our work!
    create_test_repo(os.path.abspath(args.dest))

if __name__ == '__main__':
    sys.exit(main())
