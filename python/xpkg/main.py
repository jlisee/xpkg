#! /usr/bin/env python

# Author: Joseph Lisee <jlisee@gmail.com>

import argparse
import os
import shlex
import sys

# Project Imports
from xpkg import core
from xpkg import util


def install(args):
    """
    Installs a given package.
    """

    if args.tree:
        tree_path = os.path.abspath(args.tree)
    else:
        tree_path = None

    env = core.Environment(_get_env_dir(args.root), create=True,
                           tree_path=tree_path)
    env.install(args.path)


def remove(args):
    """
    Remove the desired package.
    """

    env = core.Environment(_get_env_dir(args.root))
    env.remove(args.name)


def build(args):
    """
    Create the binary for of the desired package.
    """

    builder = core.BinaryPackageBuilder(util.load_xpd(args.path))

    res = builder.build(args.dest)

    print 'Package in:', res


def jump(args):
    """
    Jumps into an activated environment.
    """

    env = core.Environment(_get_env_dir(args.root))

    # Parse the executable and it's arguments apart
    parts = shlex.split(args.command)

    program = parts[0]
    pargs = parts[1:]

    # Now lets run the command inside the environment
    env.jump(program=program, args=pargs)


def info(args):
    """
    Get information on the given package.
    """

    # Parse argument
    package_name = args.name
    env_dir = _get_env_dir(args.root)

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
    env_dir = _get_env_dir(args.root)

    # List packages
    env = core.Environment(env_dir)

    for package, info in env._pdb.iter_packages():
        print '  %s - %s' % (package, info['version'])


def _get_env_dir(env_dir):
    """
    Returns the absolute path to the given directory, or just the None.
    """

    if env_dir:
        return os.path.abspath(env_dir)
    else:
        None


def main(argv = None):
    if argv is None:
        argv = sys.argv

    # Set up argument parsers
    parser = argparse.ArgumentParser(prog=argv[0])
    subparsers = parser.add_subparsers(help='sub-commands')

    # Common arguments for environment root argument
    root_args = ['-r','--root']
    root_kwargs = {'type' : str, 'help' : 'Root directory', 'default' : None}

    # Create command parsers
    parser_j = subparsers.add_parser('jump', help='Jump into environment')
    parser_j.add_argument(*root_args, **root_kwargs)
    parser_j.add_argument('-c','--command', type=str, help='Command to run',
                          default='bash', dest='command')
    parser_j.set_defaults(func=jump)

    parser_i = subparsers.add_parser('install', help='Install from YAML file')
    parser_i.add_argument('path', type=str, help='YAML install file')
    parser_i.add_argument('-t', '--tree', type=str, default=None,
                          help='Package description tree')
    parser_i.add_argument(*root_args, **root_kwargs)
    parser_i.set_defaults(func=install)

    parser_i = subparsers.add_parser('build', help=build.__doc__)
    #parser_i.add_argument(*root_args, **root_kwargs)
    parser_i.add_argument('path', type=str, help='YAML install file')
    parser_i.add_argument('-d','--dest', type=str, default='.',
                          help='Where to place the package')
    parser_i.set_defaults(func=build)

    parser_i = subparsers.add_parser('remove', help=remove.__doc__)
    parser_i.add_argument('name', type=str, help='Name of package')
    parser_i.add_argument(*root_args, **root_kwargs)
    parser_i.set_defaults(func=remove)

    parser_i = subparsers.add_parser('info', help=info.__doc__)
    parser_i.add_argument('name', type=str, help='Name of package')
    parser_i.add_argument(*root_args, **root_kwargs)
    parser_i.set_defaults(func=info)

    parser_i = subparsers.add_parser('list', help=list_packages.__doc__)
    parser_i.add_argument(*root_args, **root_kwargs)
    parser_i.set_defaults(func=list_packages)

    # parse some argument lists
    args = parser.parse_args(argv[1:])
    args.func(args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except core.Exception as e:
        print e
        sys.exit(1)
