# Author: Joseph Lisee <jlisee@gmail.com>

import hashlib
import os
import subprocess
import sys
import tarfile
import urllib

from contextlib import contextmanager


def shellcmd(cmd, echo=True, stream=True):
    """
    Run 'cmd' in the shell and return its standard out.
    """

    if echo:
        print '[cmd] {0}'.format(cmd)

    if stream:
        out = None

        subprocess.check_call(cmd, stderr=sys.stderr, stdout=sys.stdout,
                              shell=True)
    else:
        out = subprocess.check_output(cmd, stderr=sys.stderr, shell=True)

        if echo:
            print out

    return out


def fetch_url(url, local_path):
    """
    Download the remote url into the local path
    """

    print 'Downloading',

    # Determine what the local file will be called
    local_filename = os.path.basename(url)

    def progress(count, block_size, total_size):
        """
        Super simple progress reporter.
        """
        percent = int(count*block_size*100/total_size)

        args = (local_filename, percent, total_size)
        sys.stdout.write("\r%s - %2d%% of %d bytes" % args)
        sys.stdout.flush()

    # Down the file
    filename, headers = urllib.urlretrieve(url, local_path,
                                           reporthook = progress)

    return filename


def hash_file(f, hash_type, block_size=2**20):
    """
    Computes the hash sum for a file
    """

    hash_state = hash_type()

    while True:
        data = f.read(block_size)

        if not data:
            break

        hash_state.update(data)

    return hash_state.hexdigest()


def unpack_tarball(tar_url, extract_path='.'):
    """
    Extracts a tar file to disk, return root directory (and assumes
    there is one).
    """

    print 'Unpacking',tar_url

    # Open and extract
    with tarfile.open(tar_url, 'r') as tar:
        tar.extractall(extract_path)
        filenames = tar.getnames()

    # Get root (the shortest path will be the root if there is one)
    unpack_dir = sorted(filenames)[0]

    return os.path.join(extract_path, unpack_dir)


@contextmanager
def cd(new_dir):
    """
    Changes directories, always return, example:

    with cd('/some/dir'):
        # In some dir
    # Out of some dir
    """

    # Store current directory
    cwd = os.path.abspath(os.getcwd())

    # Move into directory and yield control
    os.chdir(new_dir)

    try:
        yield

    finally:
        # Return to current directory
        os.chdir(cwd)
