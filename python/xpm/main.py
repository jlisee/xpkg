#! /usr/bin/env python

# Author: Joseph Lisee <jlisee@gmail.com>

import argparse
import os
import sys

# Project Imports
from xpm import core


def install(args):
    """
    Installs a given package
    """
    core.install(args.path, os.path.abspath(args.root))


def jump(args):
    """
    Jumps into an activated environment.
    """
    core.jump(os.path.abspath(args.root))


def info(args):
    """
    Get information on the given package.
    """

    # Parse argument
    package_name = args.name
    env_dir = os.path.abspath(args.root)

    # Make sure we have a package database
    if not os.path.exists(env_dir):
        print 'No XPM package DB found in root "%s"' % env_dir

    # Load the package database
    pdb = core.PackageDatabase(env_dir)

    # Grab the information
    info = pdb.get_info(package_name)

    if info:
        print 'Package %s at version %s' % (package_name, info)
    else:
        print 'Package %s not installed.' % package_name


def main(argv = None):
    if argv is None:
        argv = sys.argv

    # Set up argument parsers
    parser = argparse.ArgumentParser(prog=argv[0])
    subparsers = parser.add_subparsers(help='sub-commands')

    # create the parser for the "jump""
    parser_j = subparsers.add_parser('jump', help='Jump into environment')
    parser_j.add_argument('root', type=str, help='Root directory')
    parser_j.set_defaults(func=jump)

    parser_i = subparsers.add_parser('install', help='Install from YAML file')
    parser_i.add_argument('path', type=str, help='YAML install file')
    parser_i.add_argument('root', type=str, help='Root directory')
    parser_i.set_defaults(func=install)

    parser_i = subparsers.add_parser('info', help=info.__doc__)
    parser_i.add_argument('name', type=str, help='Name of package')
    parser_i.add_argument('root', type=str, help='Root directory')
    parser_i.set_defaults(func=info)


    # parse some argument lists
    args = parser.parse_args(argv[1:])
    args.func(args)


if __name__ == '__main__':
    sys.exit(main())
