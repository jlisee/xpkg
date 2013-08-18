# Author: Joseph Lisee <jlisee@gmail.com>

# Python Imports
import os
import hashlib
import yaml
import tempfile
import shutil

# Project Imports
from xpm import util

xpm_root = 'XPM_ROOT'

class Exception(BaseException):
    pass

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


    def iter_packages(self):
        """
        Returns an iterator of (package, version) pairs
        """

        for k in self._db.iteritems():
            yield k


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


class Environment(object):
    """
    This class manages the local package environment.
    """

    def __init__(self, env_dir=None, create=False, tree_path=None):

        if env_dir is None:
            if xpm_root in os.environ:
                self._env_dir = os.environ[xpm_root]
            else:
                raise Exception("No XPM_ROOT not defined, can't find environment")
        else:
            self._env_dir = env_dir

        # Error out if we are not creating and environment and this one does
        # not exist
        if not os.path.exists(self._env_dir) and not create:
            raise Exception('No XPM package DB found in root "%s"' % self._env_dir)

        # If needed this will setup the empty enviornment
        self._pdb = PackageDatabase(self._env_dir)

        # Setup the package tree to either load from the given path or return
        # no packages
        if tree_path:
            self._tree = FilePackageTree(tree_path)
        else:
            self._tree = EmptyPackageTree()


    def install(self, input_val):

        # We either have a direct path, or have to lookup the name in the tree
        if input_val.endswith('.xpd'):
            xpd_data = util.load_xpd(input_val)
        else:
            # The input_val must be a package name so try to find the xpd
            # path from the tree.
            xpd_data = self._tree.lookup(input_val)

            if xpd_data is None:
                msg = "Cannot find description for package: %s" % input_val
                raise Exception(msg)

        # Do our install
        self._install_xpd(xpd_data)


    def _install_xpd(self, data):
        """
        Really basic install command
        """

        # Build and install the package
        builder = PackageBuilder(data)

        new_files = builder.build(self._env_dir)

        # Mark the package installed
        info = {
            'version' : data['version'],
            'files' : list(new_files),
        }

        self._pdb.mark_installed(data['name'], info)


    def remove(self, name):
        """
        Removes the given package from the environment.
        """

        # Remove all the files from the db
        info = self._pdb.get_info(name)

        if info:
            # Iterate in reverse order so that we get the files before the
            # directories
            for f in sorted(info['files'], reverse=True):
                full_path = os.path.join(self._env_dir, f)
                if os.path.exists(full_path):
                    if os.path.isdir(full_path):
                        os.rmdir(full_path)
                    else:
                        os.remove(full_path)
                else:
                    # TODO: Log a warning here
                    print 'WARNING: package %s file not found: %s' % (name, full_path)

            # Remove the package from the database
            self._pdb.mark_removed(name)
        else:
            print 'Package %s not installed.' % package_name


    def jump(self, program='bash', args=[]):
        """
        Jump into the desired environment
        """

        # Set our path vars
        env_paths = {
            'PATH' : os.path.join(self._env_dir, 'bin'),
            'LD_LIBRARY_PATH' : os.path.join(self._env_dir, 'lib'),
           }

        for varname, varpath in env_paths.iteritems():
            cur_var = os.environ.get(varname, None)

            if cur_var:
                os.environ[varname] = varpath + os.pathsep + cur_var
            else:
                os.environ[varname] = varpath

        # Setup the XPM path
        os.environ[xpm_root] = self._env_dir

        # Setup up the PS1 (this doesn't work)
        os.environ['PS1'] = '(xpm) \u@\h:\w\$'

        # Step into shell
        os.execvp(program, [program] + args)


class EmptyPackageTree(object):
    """
    Package tree which has no packages in it.
    """

    def lookup(self, package):
        return None


class FilePackageTree(object):
    """
    Allows for named (and eventually versioned) lookup of packages from a
    directory full of description.
    """

    def __init__(self, path):
        # Holds are information
        self._index = {}

        # Make sure our path exists
        if not os.path.exists(path):
            raise Exception('Package tree path "%s" does not exist' % path)

        # Get information on all the dicts found in the directory
        for root, dirs, files in os.walk(path):
            for file_name in files:
                if file_name.endswith('.xpd'):

                    # Load the description
                    full_path = os.path.join(root, file_name)

                    data = util.load_xpd(full_path)

                    # Store the path in the index
                    self._index[data['name']] = full_path


    def lookup(self, package):
        """
        Returns the xpd data for the desired package, None if the package is
        not present.
        """

        if package in self._index:
            result = util.load_xpd(self._index[package])
        else:
            result = None

        return result


class PackageBuilder(object):
    """
    Assuming all the dependency conditions for the XPD are met, this builds
    and install the a package based on it's XPD into the target directory.
    """

    def __init__(self, package_xpd):
        self._xpd = package_xpd
        self._work_dir = None
        self._target_dir = None


    def build(self, target_dir):
        """
        Right now this just executes instructions inside the XPD, but in the
        not presentfuture we can make this a little smarter.

        It returns the paths of the files created in the target_dir relative
        to the target dir itself.
        """

        # Create our temporary directory
        self._work_dir = tempfile.mkdtemp(suffix = '-xpm-' + self._xpd['name'])

        # TODO: LOG THIS
        print 'Working in:',self._work_dir

        self._target_dir = target_dir

        try:
            # Fetches and unpacks all the required sources for the package
            self._get_sources()

            # Determine what directory we have to do the build in
            dirs = os.listdir(self._work_dir)
            if len(dirs) == 1:
                build_dir = os.path.join(self._work_dir, dirs[0])
            else:
                build_dir = self._work_dir

            with util.cd(build_dir):
                # Standard build configure install
                self._configure()

                self._build()

                new_files = self._install()
        finally:
            # Make sure we cleanup after we are done
            # Don't do this right now
            #shutil.rmtree(self._work_dir)
            pass

        return new_files


    def _get_sources(self):
        """
        Fetches and unpacks all the needed source files.
        """

        # Download and unpack our files
        for filehash, info in self._xpd['files'].iteritems():

            # Fetch our file
            download_path = fetch_file(filehash, info['url'])

            # Unpack into directory
            root_dir = util.unpack_tarball(download_path, self._work_dir)

            # Move if needed
            relative_path = info.get('location', None)

            if relative_path:
                dst_path = os.path.join(self._work_dir, relative_path)

                # TODO: LOG THIS
                print root_dir,'->',dst_path

                shutil.move(root_dir, dst_path)


    def _configure(self):
        """
        Run a configure step for the package if it has one.
        """

        # Configure if needed
        if 'configure' in self._xpd:
            raw_cmd = self._xpd['configure']

            cmd = raw_cmd % {'prefix' : self._target_dir}

            util.shellcmd(cmd)


    def _build(self):
        """
        Builds the desired package.
        """

        raw_cmd = self._xpd['build']

        cmd = raw_cmd % {'jobs' : '8'}

        util.shellcmd(cmd)


    def _install(self):
        """
        Installs the package, keeping track of what files it creates.
        """

        pre_files = set(util.list_files(self._target_dir))

        util.shellcmd(self._xpd['install'])

        post_files = set(util.list_files(self._target_dir))

        new_files = post_files - pre_files

        return new_files
