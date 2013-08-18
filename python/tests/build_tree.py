#! /usr/bin/env python

# Author: Joseph Lisee <jlisee@gmail.com>

# Python Imports
import argparse
import hashlib
import os
import sys

# Project Imports
from xpm import util

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

    util.template_file(source_xdp, package_xpd, args)


def create_test_repo(dest_dir):
    """
    Creates a set of XPM package files and matches source tar balls from our
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
            setup_package(name, full_path, file_dir, tree_dir)


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
