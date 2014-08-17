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
def patchelf(args):
    """
    Patches all elfs in the current file tree to point to the given interp.

    Arguments:
      [new_interp, directory to search or exe]
    """

    # Parser arguments
    if not isinstance(args, list):
        args = [args]

    target_interp = args[0]

    if len(args) > 1:
        path = args[1]
    else:
        path = os.getcwd()

    # Identify a file as being elf
    elf_magic = '\x7fELF'

    def is_elf(fpath):
        with open(fpath) as f:
            magic = f.read(4)

        return magic == elf_magic

    # Find all elf binaries
    elf_files = []

    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for file_path in [os.path.join(root, f) for f in files]:
                if is_elf(file_path):
                    elf_files.append(os.path.abspath(file_path))

    elif is_elf(path):
        elf_files.append(os.path.abspath(path))

    # Patch each binary if needed
    for elf_file in elf_files:

        # Get the current elf interp
        interp = linux.readelf_interp(elf_file)

        if interp and interp != target_interp:
            util.shellcmd(['patchelf', '--set-interpreter', target_interp,
                            elf_file], shell=False)


@command
def symlink(args):
    """
    Creates a symlink, expects an array of arguments: [source, link_name]
    """

    src = args[0]
    link_name = args[1]

    os.symlink(src, link_name)


@command
def full_binary_str_replace(args):
    """
    Replace a complete binary string.
    """

    # Read in and validate args
    file_path = args[0]
    old = args[1]
    new = args[2]

    if len(new) > len(old):
        margs = (old, file_path, new)
        msg = "Cannot replace '%s' in '%s', replacement ('%s') is longer"
        raise Exception(msg & margs)

    # Generate null-terminated string
    new_len = len(new)
    null_old = old + '\0'
    null_old_len = len(null_old)

    padded_new = new + ('\0' * (null_old_len - new_len))

    args = (len(null_old), len(padded_new))
    msg = 'Old len %d not equal to new padded len %d' % args
    assert len(padded_new) == len(null_old), msg

    # Load and replace contents
    contents = open(file_path).read()

    results = contents.replace(null_old, padded_new)

    # Check to make sure the length hasn't changed
    len_contents = len(contents)
    len_results = len(results)

    args = (len_contents, len_results)
    msg = 'Len changed from %d to %d' % args

    assert len_contents == len_results, msg

    # Write out the final results
    with open(file_path, 'w') as f:
        f.write(results)
