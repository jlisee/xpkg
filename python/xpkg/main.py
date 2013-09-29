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

    # Load the description from th file
    package_description = util.load_xpd(args.path)

    dest_path = args.dest


    if 'dependencies' in package_description:
        # If we have dependencies build within the enviornemnt
        env = core.Environment(_get_env_dir(args.root))

        res = env.build_xpd(package_description, dest_path)
    else:
        # If there are no dependencies, preform a free standing build
        builder = core.BinaryPackageBuilder(package_description)

        res = builder.build(dest_path)

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
    input_val = args.name


    if input_val.endswith('.xpa'):
        # Actual package parse and print out information
        xpa = core.XPA(input_val)

        info = xpa.info
    else:
        # Package name lookup info from our environment
        env_dir = _get_env_dir(args.root)

        # Load the package database
        env = core.Environment(env_dir)

        # Grab the information
        info = env._pdb.get_info(input_val)

    # Display info
    if info:
        print '  name:',info['name']
        print '  version:',info['version']
        if info.get('dependencies', None):
            print '  dependencies:',info['dependencies']

        if args.verbose:
            print '  files:'
            for f in sorted(info['files']):
                print '    -',f
    else:
        print 'Package %s not installed.' % input_val


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
    parser.add_argument('-d', '--debug', default=False, action='store_true',
                        help="Don't catch internal exception")
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
    parser_i.add_argument(*root_args, **root_kwargs)
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
    parser_i.add_argument('-v','--verbose', action='store_true', default=False,
                          help='Show more details about the package')
    parser_i.add_argument(*root_args, **root_kwargs)
    parser_i.set_defaults(func=info)

    parser_i = subparsers.add_parser('list', help=list_packages.__doc__)
    parser_i.add_argument(*root_args, **root_kwargs)
    parser_i.set_defaults(func=list_packages)

    # parse some argument lists
    args = parser.parse_args(argv[1:])

    if args.debug:
        args.func(args)
    else:
        try:
            args.func(args)
        except core.Exception as e:
            print e
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
