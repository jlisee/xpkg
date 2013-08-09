#! /usr/bin/env python

# Author: Joseph Lisee <jlisee@gmail.com>

import argparse
import os
import sys
import hashlib
import yaml
import tempfile
import shutil

# Project Imports
from xpm import util

# Get the current directory
cur_dir, _ = os.path.split(__file__)

def fetch_file(filehash, url):
    # Make sure cache exists
    cache_dir = os.path.expanduser(os.path.join('~', '.xpm', 'cache'))

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # Get the path where the file will be placed in our cache
    cache_path = os.path.join(cache_dir, filehash)

    # See if we need to download the file
    download_file = not os.path.exists(cache_path)

    if os.path.exists(cache_path):
        # Lets verify the hash of the existing file, it's mostly ok to do this
        # because we need to read the file off disk to unpack it and the OS will
        # cache it.

        # Get the hash types
        valid_types = set(['MD5', 'sha1', 'sha224', 'sha256', 'sha384',
                           'sha512'])

        # Get the information we need to do the hashing
        hash_type, hex_hash = filehash.split('-')

        hash_func = getattr(hashlib, hash_type)

        current_hash = util.hash_file(open(cache_path), hash_func)

        # Check if the hashes don't match and if they don't make sure we can the
        # file
        if current_hash != hex_hash:
            download_file = True

    else:
        download_file = True

    # Download if needed
    if download_file:
        p = util.fetch_url(url, cache_path)
        print url,p

    return cache_path


def install(yaml_path, env_dir):
    """
    Really basic install command
    """

    # Load our file
    data = yaml.load(open(yaml_path))

    # Create our temporary directory
    work_dir = tempfile.mkdtemp(suffix = '-xpm-' + data['name'])

    print 'Working in:',work_dir

    # Download and unpack our files
    for filehash, info in data['files'].iteritems():

        # Fetch our file
        download_path = fetch_file(filehash, info['url'])

        # Unpack into directory
        root_dir = util.unpack_tarball(download_path, work_dir)

        # Move if needed
        relative_path = info.get('location', None)

        if relative_path:
            dst_path = os.path.join(work_dir, relative_path)

            print root_dir,'->',dst_path

            shutil.move(root_dir, dst_path)

    # Figure out which directory we need
    dirs = os.listdir(work_dir)
    if len(dirs) == 1:
        build_dir = os.path.join(work_dir, dirs[0])
    else:
        build_dir = work_dir


    with util.cd(build_dir):
        # Configure if needed
        if 'configure' in data:
            raw_cmd = data['configure']

            cmd = raw_cmd % {'prefix' : env_dir}

            util.shellcmd(cmd)

        # Build
        raw_cmd = data['build']
        cmd = raw_cmd % {'jobs' : '8'}
        util.shellcmd(cmd)

        # Install
        util.shellcmd(data['install'])

    # Mark the package installed


def install_func(args):
    install(args.path, os.path.abspath(args.root))


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
    jump(os.path.abspath(args.root))


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

    parser_i = subparsers.add_parser('install', help='Install from YAML file')
    parser_i.add_argument('path', type=str, help='YAML install file')
    parser_i.add_argument('root', type=str, help='Root directory')
    parser_i.set_defaults(func=install_func)

    # parse some argument lists
    args = parser.parse_args(argv[1:])
    args.func(args)


if __name__ == '__main__':
    sys.exit(main())
