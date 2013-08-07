#! /usr/bin/env python

# Author: Joseph Lisee <jlisee@gmail.com>

import os
import sys
import argparse

# Get the current directory
cur_dir, _ = os.path.split(__file__)


def jump(env_dir):
    """
    Jump into the desired environment
    """

    # Set our path vars
    env_paths = {
        'PATH' : os.path.join(env_dir, 'bin'),
        'LD_LIBRARY_PATH' : os.path.join(env_dir, 'lib'),
       }

    for varname, varpath in env_paths.iteritems():
        cur_var = os.environ.get(varname, None)

        if cur_var:
            os.environ[varname] = cur_var + os.pathsep + varpath
        else:
            os.environ[varname] = varpath

    # Setup up the PS1 (this doesn't work)
    os.environ['PS1'] = '(xpm) \u@\h:\w\$'

    # Step into shell
    os.execvp('bash', ['bash'])

def jump_func(args):
    """
    Transforms arguments into actual function
    """
    jump(args.root)


def main(argv = None):
    if argv is None:
        argv = sys.argv

    # Set up argument parsers
    parser = argparse.ArgumentParser(prog=argv[0])
    subparsers = parser.add_subparsers(help='sub-commands')

    # create the parser for the "jump""
    parser_j = subparsers.add_parser('jump', help='Jump into environment')
    parser_j.add_argument('root', type=str, help='Root directory')
    parser_j.set_defaults(func=jump_func)

    # parse some argument lists
    args = parser.parse_args(argv[1:])
    args.func(args)


if __name__ == '__main__':
    sys.exit(main())
