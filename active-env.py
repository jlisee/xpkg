#! /usr/bin/env python

# Author: Joseph Lisee <jlisee@gmail.com>

import os
import sys

# Get the current directory
cur_dir, _ = os.path.split(__file__)

def main():

    # Get our path
    env_dir = os.path.abspath(os.path.join(cur_dir, 'env'))

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

if __name__ == '__main__':
    sys.exit(main())
