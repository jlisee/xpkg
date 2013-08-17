# Author: Joseph Lisee <jlisee@gmail.com>

# Python Imports
import os
import hashlib
import yaml
import tempfile
import shutil

# Project Imports
from xpm import util

class PackageDatabase(object):
    """
    Manages the on disk database of packages.
    """

    def __init__(self, env_dir):

        # Package db location
        self._db_dir = os.path.join(env_dir, 'etc', 'xpm')
        self._db_path = os.path.join(self._db_dir, 'db.yml')

        # Create package database if it doesn't exist
        if not os.path.exists(self._db_path):
            self._create_db()

        # Load database
        self._load_db()


    def _create_db(self):
        """
        Create database
        """

        # Create directory
        if not os.path.exists(self._db_dir):
            os.makedirs(self._db_dir)

        # Create empty db file if needed
        if not os.path.exists(self._db_path):
            with open(self._db_path, 'w') as f:
                f.write('')


    def _load_db(self):
        """
        Write DB to disk.
        """

        self._db = yaml.load(open(self._db_path))

        # Handle the empty database case
        if self._db is None:
            self._db = {}


    def _save_db(self):
        """
        Save DB to disk.
        """

        with open(self._db_path, 'w') as f:
            yaml.dump(self._db, f)


    def mark_installed(self, name, info):
        """
        Marks the current package installed
        """

        # Mark package with the current installed version
        self._db[name] = info

        # Save the data to disk
        self._save_db()


    def mark_removed(self, name):
        """
        Marks the current package installed
        """

        # Mark package with the current installed version
        del self._db[name]

        # Save the data to disk
        self._save_db()


    def get_packages(self):
        """
        Returns an iterator of (package, version) pairs
        """

        return self._db.iterkeys()


    def get_info(self, name):
        """
        Return the information on the installed package, returns None if it
        doesn't exist.
        """

        return self._db.get(name, None)


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
        valid_types = set(['md5', 'sha1', 'sha224', 'sha256', 'sha384',
                           'sha512'])

        # Get the information we need to do the hashing
        hash_typename, hex_hash = filehash.split('-')

        hash_type = getattr(hashlib, hash_typename)

        current_hash = util.hash_file(open(cache_path),
                                      hash_type=hash_type)

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
        pre_files = set(util.list_files(env_dir))

        util.shellcmd(data['install'])

        post_files = set(util.list_files(env_dir))

        new_files = post_files - pre_files

    # Mark the package installed
    pdb = PackageDatabase(env_dir)

    info = {
        'version' : data['version'],
        'files' : list(new_files),
    }

    pdb.mark_installed(data['name'], info)


def remove(name, env_dir):
    """
    Removes the given package from the environment.
    """

    # Make sure we have a package database
    if not os.path.exists(env_dir):
        print 'No XPM package DB found in root "%s"' % env_dir
        return

    # Load the package database
    pdb = PackageDatabase(env_dir)

    # Remove all the files from the db
    info = pdb.get_info(name)

    if info:
        # Iterate in reverse order so that we get the files before the
        # directories
        for f in sorted(info['files'], reverse=True):
            full_path = os.path.join(env_dir, f)
            if os.path.exists(full_path):
                if os.path.isdir(full_path):
                    os.rmdir(full_path)
                else:
                    os.remove(full_path)
            else:
                # TODO: Log a warning here
                print 'WARNING: package %s file not found: %s' % (name, full_path)

        # Remove the package from the database
        pdb.mark_removed(name)
    else:
        print 'Package %s not installed.' % package_name


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
