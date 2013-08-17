#! /usr/bin/env python

# Author: Joseph Lisee <jlisee@gmail.com>

import argparse
import os
import sys

# Project Imports
from xpm import core


def install(args):
    """
    Installs a given package.
    """

    env = core.Environment(os.path.abspath(args.root), create=True)
    env.install(args.path)


def remove(args):
    """
    Remove the desired package.
    """

    env = core.Environment(os.path.abspath(args.root))
    env.remove(args.name)


def jump(args):
    """
    Jumps into an activated environment.
    """

    env = core.Environment(os.path.abspath(args.root))
    env.jump()


def info(args):
    """
    Get information on the given package.
    """

    # Parse argument
    package_name = args.name
    env_dir = os.path.abspath(args.root)

    # Load the package database
    env = core.Environment(env_dir)

    # Grab the information
    info = env._pdb.get_info(package_name)

    if info:
        print 'Package %s at version %s' % (package_name, info['version'])
    else:
        print 'Package %s not installed.' % package_name


def list_packages(args):
    """
    Lists all packages installed in environment
    """

    # Parse argument
    env_dir = os.path.abspath(args.root)

    # List packages
    env = core.Environment(env_dir)

    for package, info in env._pdb.iter_packages():
        print '  %s - %s' % (package, info['version'])


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

    parser_i = subparsers.add_parser('remove', help=remove.__doc__)
    parser_i.add_argument('name', type=str, help='Name of package')
    parser_i.add_argument('root', type=str, help='Root directory')
    parser_i.set_defaults(func=remove)

    parser_i = subparsers.add_parser('info', help=info.__doc__)
    parser_i.add_argument('name', type=str, help='Name of package')
    parser_i.add_argument('root', type=str, help='Root directory')
    parser_i.set_defaults(func=info)

    parser_i = subparsers.add_parser('list', help=list_packages.__doc__)
    parser_i.add_argument('root', type=str, help='Root directory')
    parser_i.set_defaults(func=list_packages)

    # parse some argument lists
    args = parser.parse_args(argv[1:])
    args.func(args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except core.Exception as e:
        print e
