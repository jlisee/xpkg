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

    # parse some argument lists
    args = parser.parse_args(argv[1:])
    args.func(args)


if __name__ == '__main__':
    sys.exit(main())
