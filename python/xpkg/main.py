#! /usr/bin/env python

# Author: Joseph Lisee <jlisee@gmail.com>

# Python Imports
import argparse
import os
import shlex
import sys

# Library Imports
import yaml

# Project Imports
from xpkg import build
from xpkg import commands
from xpkg import core
from xpkg import util
from xpkg import create as xcreate


def init(args):
    """
    Create an environment to install packages into.
    """

    # Get the proper toolset name
    if args.toolset is None:
        toolset_name = build.DefaultToolsetName
    else:
        toolset_name = args.toolset

    # Create our environment
    core.Environment.init(args.root, args.name, toolset_name)


def install(args):
    """
    Install the given package (name, archive, or xpd).
    """

    if args.tree:
        tree_path = os.path.abspath(args.tree)
    else:
        tree_path = None

    env = _create_env(args.root, create=True, tree_path=tree_path,
                      verbose=args.verbose)

    for name in args.names:
        env.install(name)


def remove(args):
    """
    Remove the desired package.
    """

    env = _create_env(args.root)

    for name in args.names:
        env.remove(name)


def build_(args):
    """
    Create the binary for of the desired package.
    """

    # Verify arguments
    if args.use_env and args.no_env:
        raise Exception("Can't build with 'no-env' and 'use-env'")

    # Load the description from th file
    xpd = core.XPD(args.path)

    dest_path = args.dest

    have_deps = (len(xpd.dependencies) + len(xpd.build_dependencies)) > 0

    if args.use_env or have_deps and not args.no_env:
        # If we have dependencies build within the enviornemnt
        env = _create_env(args.root)

        res = env.build_xpd(xpd, dest_path, verbose=args.verbose)
    else:
        # If there are no dependencies, preform a free standing build
        builder = core.build.BinaryPackageBuilder(xpd)

        res = builder.build(dest_path, output_to_file=not args.verbose)

    print 'Package in:', res


def jump(args):
    """
    Jumps into an activated environment.
    """

    env = _create_env(args.root)

    # Parse the executable and it's arguments apart
    parts = shlex.split(args.command)

    program = parts[0]
    pargs = parts[1:]

    # Now lets run the command inside the environment
    env.jump(program=program, args=pargs, isolate=args.isolate)


def info(args):
    """
    Get information about the environment, an installed package, or package
    archive.
    """

    # Parse argument
    input_val = args.name


    if input_val is None:
        # Nothing supplied, grab environment and dump information about it
        env = _create_env(args.root)

        _environment_info(env, args.verbose)

        info = None

    elif input_val.endswith('.xpa'):
        # Actual package parse and print out information
        xpa = core.XPA(input_val)

        info = xpa.info

    else:
        # Load the package database
        env = _create_env(args.root)

        # Grab the information
        info = env.info(input_val)

    # Display info
    if info:
        _package_info(info, args.verbose)
    elif not input_val is None:
        print 'Package %s not installed.' % input_val


def _package_info(info, verbose):
    """
    Print package info a yaml like format.
    """

    print '  name:',info['name']
    print '  version:',info['version']

    if info.get('description'):
        description = info['description'].strip()

        # Process extra long descriptions
        if (80 - len('  description: ')) < len(description):
            description = util.wrap_yaml_string(description)
        print '  description:',description

    if info.get('dependencies', None):
        print '  dependencies:',info['dependencies']

    if verbose:
        print '  dirs:'
        for f in sorted(info['dirs']):
            print '    -',f
        print '  files:'
        for f in sorted(info['files']):
            print '    -',f


def _environment_info(env, verbose):
    """
    Print information about the environment.
    """

    print '  name:',env.name
    print '  toolset:',env.toolset.name
    print '  root:',env.root

    def print_path(name, paths, depth=2):
        padding = ' ' * depth

        print '%s%s:' % (padding, name)
        for p in paths:
            print '%s  - %s' % (padding, p)

    print_path('trees', env.tree_paths)
    print_path('repos', env.repo_paths)

    if verbose:
        # Now print the environment variables
        print '  env:'
        env_vars = env.get_env_variables()

        for varname, value in env_vars.iteritems():
            # Unpack the variable and it's separator
            variable, sep = value

            # Attempt to split into parts
            if sep == ' ':
                parts = shlex.split(variable)
            else:
                parts = variable.split(sep)

            # Print it out
            if len(parts) > 1:
                print_path(varname, parts, depth=4)
            else:
                print '    %s: %s' % (varname, variable)

        print '  toolset-env:'
        toolset_env_info = env.get_toolset_env_info()

        for action, varmap in toolset_env_info.iteritems():
            print '    %s:' % action
            for varname, value in varmap.iteritems():
                print '      %s: "%s"' % (varname, value)


def list_packages(args):
    """
    Lists all packages installed in environment
    """

    # Create environment
    env = _create_env(args.root)

    # Get a list of packages
    pkgs = list(env._pdb.iter_packages())

    # List packages
    for package, info in sorted(pkgs, cmp=lambda a,b: cmp(a[0], b[0])):
        print '  %s - %s' % (package, info['version'])


def run_command(args):
    """
    Run the given built in command with the desired arguments.
    """

    # Create an environment
    env = _create_env(args.root)


    # Run within the environment
    with util.save_env():
        env.apply_env_variables()

        cmd = commands.Command(name=args.name[0], args=args.args, working_dir='')
        commands.run_command(cmd)


def create(args):
    """
    Retrieve the given URI, uses xpkg cache if possible.
    """

    # Manage URL
    raw_url = args.url[0]
    if raw_url.count('://'):
        url = raw_url
    else:
        url = 'file://' + os.path.abspath(raw_url)

    # Generate an XPD to build the resource at that URL
    xpd_yaml = xcreate.url_to_xpd(url)

    # Now create an output path and check it
    output_path = args.output

    if not output_path:
        xpd = yaml.load(xpd_yaml)
        output_path = xpd['name'] + '.xpd'

    with open(output_path, 'w') as f:
        f.write(xpd_yaml)

    print 'XPD written to:',output_path


def _get_env_dir(env_dir):
    """
    Returns the absolute path to the given directory, or just the None.
    """

    if env_dir:
        return os.path.abspath(env_dir)
    else:
        None


def _create_env(env_dir, **kwargs):
    """
    Create an environment object with a path that might be None.
    """

    return core.Environment(_get_env_dir(env_dir), **kwargs)



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
    parser_j = subparsers.add_parser('init', help=init.__doc__)
    parser_j.add_argument('root', type=str, help='Root directory')
    parser_j.add_argument('name', type=str, help='Name for the environment')
    parser_j.add_argument('-t','--toolset', type=str, default=None,
                          help='Name for the environment')
    parser_j.set_defaults(func=init)

    parser_j = subparsers.add_parser('jump', help=jump.__doc__)
    parser_j.add_argument(*root_args, **root_kwargs)
    parser_j.add_argument('-c','--command', type=str, help='Command to run',
                          default='bash', dest='command')
    parser_j.add_argument('-i','--isolate', action='store_true', default=False,
                          help='Overwrite instead of prepend environment variables')
    parser_j.set_defaults(func=jump)

    parser_i = subparsers.add_parser('install', help=install.__doc__)
    parser_i.add_argument('names', type=str, nargs='+',
                          help='Package name, XPD, or XPA file path')
    parser_i.add_argument('-t', '--tree', type=str, default=None,
                          help='Package description tree')
    parser_i.add_argument('-v','--verbose', action='store_true', default=False,
                          help='Print build output to screen')
    parser_i.add_argument(*root_args, **root_kwargs)
    parser_i.set_defaults(func=install)

    parser_i = subparsers.add_parser('build', help=build_.__doc__)
    parser_i.add_argument(*root_args, **root_kwargs)
    parser_i.add_argument('path', type=str, help='YAML install file')
    parser_i.add_argument('-d','--dest', type=str, default='.',
                          help='Where to place the package')
    parser_i.add_argument('-e','--use-env', action='store_true', default=False,
                          help='Force environment usage')
    parser_i.add_argument('-n','--no-env', action='store_true', default=False,
                          help='Force independent build')
    parser_i.add_argument('-v','--verbose', action='store_true', default=False,
                          help='Print build output to screen')
    parser_i.set_defaults(func=build_)

    parser_i = subparsers.add_parser('remove', help=remove.__doc__)
    parser_i.add_argument('names', type=str, nargs='+', help='Name of package')
    parser_i.add_argument(*root_args, **root_kwargs)
    parser_i.set_defaults(func=remove)

    parser_i = subparsers.add_parser('info', help=info.__doc__)
    parser_i.add_argument('name', type=str, help='Name of package', nargs='?')
    parser_i.add_argument('-v','--verbose', action='store_true', default=False,
                          help='Show more details about the package')
    parser_i.add_argument(*root_args, **root_kwargs)
    parser_i.set_defaults(func=info)

    parser_i = subparsers.add_parser('list', help=list_packages.__doc__)
    parser_i.add_argument(*root_args, **root_kwargs)
    parser_i.set_defaults(func=list_packages)

    parser_i = subparsers.add_parser('command', help=run_command.__doc__)
    #parser_j.add_argument(*root_args, **root_kwargs)
    parser_i.add_argument('name', type=str, nargs=1,
                          help='Name of the command')
    parser_i.add_argument('args', type=str, nargs='*',
                          help='Arguments for the command')
    parser_i.add_argument(*root_args, **root_kwargs)
    parser_i.set_defaults(func=run_command)

    parser_i = subparsers.add_parser('create', help=create.__doc__)
    parser_i.add_argument('url', type=str, nargs=1,
                          help='URL of archive you wish to create an XPD for')
    parser_i.add_argument('-o', '--output', type=str, default=None,
                          help='(Optional) Output file for the generated XPD')
    parser_i.add_argument(*root_args, **root_kwargs)
    parser_i.set_defaults(func=create)

    # parse some argument lists
    args = parser.parse_args(argv[1:])

    if args.debug:
        args.func(args)
    else:
        # TODO: provide a debug option that shows the stack trace, or maybe log
        # it
        try:
            args.func(args)
        except core.Exception as e:
            print e
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
