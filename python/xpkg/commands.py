# Author: Joseph Lisee <jlisee@gmail.com>

# Python Imports
import os

from collections import namedtuple

# Library Imports
from xpkg import util
from xpkg import linux

Command = namedtuple('Command', ['name', 'args', 'working_dir'])


COMMANDS = {}

def run_command(cmd):
    """
    Runs the given command with the given argument.  This takes a Command
    object.
    """

    if not cmd.name in COMMANDS:
        raise Exception('"%s" is not built-in command' % name)

    def run_cmd():
        COMMANDS[cmd.name](cmd.args)

    if len(cmd.working_dir) > 0:
        with util.cd(cmd.working_dir):
            run_cmd()
    else:
        run_cmd()


def command(func):
    """
    Registers the given function as a command
    """

    global COMMANDS
    COMMANDS[func.func_name] = func
    return func


def parse_command(cmd):
    """
    This normalizes the input dict specified in an cpd file.  It does the
    following transformations:

    Input:

      { 'symlink' : ['./bin/a', './bin/b'] }

    Result:

      { 'cmd' : 'symlink', 'args' : ['./bin/a', './bin/b'], 'working_dir' : ''}


    Input:

      { 'patch' : { 'args' : 'my_patch.diff', 'working_dir' : '%(prefix)s' } }


    Results:

      { 'cmd' : patch', 'args' : 'my_patch.diff', 'working_dir' : '%(prefix)s' }
    """

    # TODO: if the user gets the spacing wrong there dict doesn't map right
    # and the name we get a one level dict where the name of the command is
    # mapped to None

    keys = cmd.keys()

    if len(keys) == 1:
        cmd_name = keys[0]

        value = cmd[cmd_name]

        if isinstance(value, dict):
            args = value.get('args', None)
            working_dir = value.get('working_dir', '')
        else:
            args = value
            working_dir = ''
    else:
        raise Exception("Error with command: %s", cmd)

    return Command(name=cmd_name, args=args, working_dir=working_dir)


@command
def symlink(args):
    """
    Creates a symlink, expects an array of arguments: [source, link_name]
    """

    src = args[0]
    link_name = args[1]

    os.symlink(src, link_name)
