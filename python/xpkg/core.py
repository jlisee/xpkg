# Author: Joseph Lisee <jlisee@gmail.com>

# Python Imports
import hashlib
import os
import platform
import shutil
import tarfile
import tempfile
import yaml

# Project Imports
from xpkg import util

xpkg_root_var = 'XPKG_ROOT'
xpkg_tree_var = 'XPKG_TREE'
xpkg_repo_var = 'XPKG_REPO'

class Exception(BaseException):
    pass

class InstallDatabase(object):
    """
    Manages the on disk database of packages.
    """

    def __init__(self, env_dir):

        # Package db location
        self._db_dir = os.path.join(env_dir, 'etc', 'xpkg')
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
    cache_dir = os.path.expanduser(os.path.join('~', '.xpkg', 'cache'))

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

    def __init__(self, env_dir=None, create=False, tree_path=None,
                 repo_path=None):

        if env_dir is None:
            if xpkg_root_var in os.environ:
                self._env_dir = os.environ[xpkg_root_var]
            else:
                raise Exception("No XPKG_ROOT not defined, can't find environment")
        else:
            self._env_dir = env_dir

        # Error out if we are not creating and environment and this one does
        # not exist
        if not os.path.exists(self._env_dir) and not create:
            raise Exception('No Xpkg package DB found in root "%s"' % self._env_dir)

        # If needed this will setup the empty enviornment
        self._pdb = InstallDatabase(self._env_dir)

        # Setup the package tree to either load from the given path or return
        # no packages
        if tree_path:
            self._tree = FilePackageTree(tree_path)
        elif xpkg_tree_var in os.environ:
            self._tree = FilePackageTree(os.environ[xpkg_tree_var])
        else:
            self._tree = EmptyPackageTree()

        # Setup the package repository so we can install pre-compiled packages
        if repo_path:
            self._repo = FilePackageRepo(repo_path)
        elif xpkg_repo_var in os.environ:
            self._repo = FilePackageRepo(os.environ[xpkg_repo_var])
        else:
            self._repo = EmptyPackageRepo()


    def install(self, input_val):

        if input_val.endswith('.xpa'):
            # We have a binary package so install it
            self._install_xpa(input_val)

        elif input_val.endswith('.xpd'):
            # Path is an xpd file load that then install
            xpd_data = util.load_xpd(input_val)

            self._install_xpd(xpd_data)
        else:
            # The input_val must be a package name so try to find the xpd
            # so first try to find the package in a pre-compile manner
            name, version = self._parse_install_input(input_val)

            xpa_path = self._repo.lookup(name, version)

            if xpa_path:
                # Verify XPA path
                if not os.path.exists(xpa_path):
                    args = (input_val, xpa_path)
                    msg = 'XPA path for package "%s" does not exist: "%s"' % args
                    raise Exception(msg)

                # Install the XPD
                self._install_xpa(xpa_path)

            else:
                # No binary package try, so lets try and find a description in
                # the package tree
                xpd_data = self._tree.lookup(name, version)

                if xpd_data is None:
                    msg = "Cannot find description for package: %s" % input_val
                    raise Exception(msg)

                # Install the XPD
                self._install_xpd(xpd_data)


    def _install_xpd(self, data):
        """
        Builds package and directly installs it into the given environment.
        """

        # Make sure all dependencies are properly installed
        self._install_deps(data)

        # Build and install the package
        builder = PackageBuilder(data)

        info = builder.build(self._env_dir, self)

        self._pdb.mark_installed(data['name'], info)


    def _install_xpa(self, path):
        """
        Install the given binary Xpkg package.
        """

        # Open up the tar file
        with tarfile.open(path) as tar:

            # Pull out and parse the metadata
            info = yaml.load(tar.extractfile('xpkg.yml'))

            # Make sure all dependencies are properly installed
            self._install_deps(info)

            # Install the files into the target environment location
            file_tar = tar.extractfile('files.tar.gz')

            with tarfile.open(fileobj = file_tar) as file_tar:

                file_tar.extractall(self._env_dir)

        # Mark the package install
        self._pdb.mark_installed(info['name'], info)


    def _install_deps(self, data):
        """
        Makes sure all the dependencies for the given package are properly
        installed.

        TODO: handle versions someday
        """

        deps = data.get('dependencies', [])

        for dep in deps:
            self.install(dep)


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

        # Setup the environment variables
        self.apply_env_variables()

        # Setup up the PS1 (this doesn't work)
        os.environ['PS1'] = '(xpkg) \u@\h:\w\$'

        # Step into shell
        os.execvp(program, [program] + args)


    def apply_env_variables(self):
        """
        Change the current environment variables so that we can use the things
        are in that environment.
        """

        # Set our path vars
        cflags = '-I%s' % os.path.join(self._env_dir, 'include')
        ldflags = '-L%s' % os.path.join(self._env_dir, 'lib')

        env_paths = {
            'PATH' : os.path.join(self._env_dir, 'bin'),
            'LD_LIBRARY_PATH' : os.path.join(self._env_dir, 'lib'),
            'CFLAGS' : cflags,
            'CCFLAGS' : cflags,
            'CPPFLAGS' : cflags,
            'LDFLAGS' : ldflags,
           }

        for varname, varpath in env_paths.iteritems():
            cur_var = os.environ.get(varname, None)

            if cur_var:
                os.environ[varname] = varpath + os.pathsep + cur_var
            else:
                os.environ[varname] = varpath

        # Setup the Xpkg path
        os.environ[xpkg_root_var] = self._env_dir

    def _parse_install_input(self, value):
        """
        Basic support for version based installs.  Right now it just parses
           mypackage==1.0.0 -> ('mypackage', '1.0.0')
           mypackage -> ('mypackage', None)
        """

        # Split into parts
        parts = value.split('==')

        # We always have name
        name = parts[0]

        # Pull out the version, or report an error
        if len(parts) == 1:
            version = None
        elif len(parts) == 2:
            version = parts[1]
        else:
            raise Exception('Invalid package expression: "%s"' % value)

        return (name, version)

class EmptyPackageTree(object):
    """
    Package tree which has no packages in it.
    """

    def lookup(self, package, version=None):
        return None


class FilePackageTree(object):
    """
    Allows for named (and eventually versioned) lookup of packages from a
    directory full of description.
    """

    def __init__(self, path):
        # Holds the package information
        self._db = PackageDatabase()

        # Make sure our path exists
        if not os.path.exists(path):
            raise Exception('Package tree path "%s" does not exist' % path)

        # Get information on all the dicts found in the directory
        for full_path in util.match_files(path, '*.xpd'):
            # Load the description
            data = util.load_xpd(full_path)

            # Store the path in the index
            self._db.store(name=data['name'],
                           version = data.get('version', ''),
                           data=full_path)

    def lookup(self, package, version=None):
        """
        Returns the xpd data for the desired package, None if the package is
        not present.
        """

        xpd_path = self._db.lookup(name=package, version=version)
        if xpd_path:
            result = util.load_xpd(xpd_path)
        else:
            result = None

        return result


class EmptyPackageRepo(object):
    """
    Package repository which has no packages in it
    """

    def lookup(self, package, version=None):
        return None


class FilePackageRepo(object):
    """
    Allows for named (and eventually versioned) lookup of pre-built binary
    packages from a directory full of them.
    """

    def __init__(self, path):
        print 'Build package repo from dir:',path

        # Holds are information
        self._db = PackageDatabase()

        # Make sure our path exists
        if not os.path.exists(path):
            raise Exception('Package repo path "%s" does not exist' % path)

        # Get information on all the dicts found in the directory
        for full_path in util.match_files(path, '*.xpa'):
            # Open up the package file
            with tarfile.open(full_path) as tar:

                # Pull out and parse the metadata
                info = yaml.load(tar.extractfile('xpkg.yml'))

            # Get the name and version of the package from the internal info
            name = info['name']
            version = info.get('version', '')

            # Store the path to the file in the package DB
            print 'Storing "%s" as %s version: %s' % (full_path, name, version)

            self._db.store(name=name, version=version, data=full_path)


    def lookup(self, package, version=None):
        """
        Returns the path the binary package, if it doesn't exist None is
        returned.
        """

        return self._db.lookup(name=package, version=version)


class PackageDatabase(object):
    """
    Stores information about packages, right now just does version and name
    look ups.  Will eventually support more advanced queries.
    """

    def __init__(self):
        self._db = {}


    def store(self, name, version, data):
        """
        Stores the desired package data by name and version.
        """

        self._db.setdefault(name, {})[version] = data


    def lookup(self, name, version=None):
        """
        Grabs the data for the specific packages, returning either the specific
        package, of the most recent version.
        """

        # Get all versions of a package
        versions = self._db.get(name, [])

        res = None

        if len(versions):
            if version and (version in versions):
                # Version specified and we have it
                res = versions[version]
            else:
                # Sorted the version data pairs
                sorted_versions = sorted(
                    versions.items(),
                    cmp = lambda a,b: util.compare_versions(a[0], b[0]))

                # Get the data for the most recent version
                return sorted_versions[-1][1]

        return res


class PackageBuilder(object):
    """
    Assuming all the dependency conditions for the XPD are met, this builds
    and install the a package based on it's XPD into the target directory.
    """

    def __init__(self, package_xpd):
        self._xpd = package_xpd
        self._work_dir = None
        self._target_dir = None


    def build(self, target_dir, environment = None):
        """
        Right now this just executes instructions inside the XPD, but in the
        future we can make this a little smarter.

        It returns the info structure for the created package.  Currently in
        the following form:

        {
          'name' : 'hello',
          'version' : '1.0.0',
          'files' : [
            'bin',
            'bin/hello'
          ]
        }
        """

        # Create our temporary directory
        self._work_dir = tempfile.mkdtemp(suffix = '-xpkg-' + self._xpd['name'])

        # TODO: LOG THIS
        print 'Working in:',self._work_dir

        self._target_dir = target_dir

        try:
            # Store the current environment
            env_vars = util.EnvStorage(store = True)

            if environment:
                environment.apply_env_variables()

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
            # Put back our environment
            env_vars.restore()

            # Make sure we cleanup after we are done
            shutil.rmtree(self._work_dir)

        return self._create_info(new_files)


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


    def _create_info(self, new_files):
        """
        Creates the info structure from the new files and the package XPD info.
        """

        info = {
            'name' : self._xpd['name'],
            'version' : self._xpd['version'],
            'files' : list(new_files),
        }

        return info


class BinaryPackageBuilder(object):
    """
    Turns XPD files into binary packages. They are built and installed into a
    temporary directory.

    The binary package format starts with an uncompressed tar file containing:
         xpkg.yml - Contains the package information
         files.tar.gz - Archive of files rooted in the env
    """

    def __init__(self,  package_xpd):
        self._xpd = package_xpd
        self._work_dir = None
        self._target_dir = None


    def build(self, storage_dir, environment = None):
        """
        Run the standard PackageBuilder then pack up the results in a package.
        """

        # Create our temporary directory
        self._work_dir = tempfile.mkdtemp(suffix = '-xpkg-install-' + self._xpd['name'])

        install_dir = os.path.join(self._work_dir, 'install')

        # TODO: LOG THIS
        print 'Binary working in:',self._work_dir

        try:
            # Build the package
            builder = PackageBuilder(self._xpd)
            info = builder.build(install_dir, environment)

            # Tar up the files
            file_tar = os.path.join(self._work_dir, 'files.tar.gz')

            with tarfile.open(file_tar, "w:gz") as tar:
                for entry_name in os.listdir(install_dir):
                    full_path = os.path.join(install_dir, entry_name)
                    tar.add(full_path, arcname=entry_name)

            # Create our metadata file
            meta_file = os.path.join(self._work_dir, 'xpkg.yml')
            with open(meta_file, 'w') as f:
                yaml.dump(info, f)

            # Create our package
            package_name = self._get_package_name()
            package_tar = os.path.join(self._work_dir, package_name)

            with tarfile.open(package_tar, "w:gz") as tar:
                tar.add(file_tar, arcname=os.path.basename(file_tar))
                tar.add(meta_file, arcname=os.path.basename(meta_file))

            # Move to the desired location
            dest_path = os.path.join(storage_dir, package_name)

            if os.path.exists(dest_path):
                os.remove(dest_path)

            shutil.move(package_tar, storage_dir)

        finally:
            # Make sure we cleanup after we are done
            # Don't do this right now
            #shutil.rmtree(self._work_dir)
            pass

        return dest_path

    def _get_package_name(self):
        """
        Gets the platform name in the following format:

           <name>_<version>_<arch>_<linkage>_<kernel>.deb

        It's really long, but we want to be able to support all platforms!
        """

        # Use the python platform module to find out about our system
        bits, linkage = platform.architecture()
        arch = platform.machine()
        kernel = platform.system()

        # Build our arguments
        args = {
            'name' : self._xpd['name'],
            'version' : self._xpd['version'],
            'arch' : arch,
            'linkage' : linkage.lower(),
            'kernel' : kernel.lower(),
        }

        # Create our version
        fmt_str = '%(name)s_%(version)s_%(arch)s_%(linkage)s_%(kernel)s.xpa'

        return fmt_str % args
