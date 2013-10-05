# Author: Joseph Lisee <jlisee@gmail.com>

# Python Imports
import hashlib
import os
import platform
import re
import shutil
import tarfile
import tempfile

# Project Imports
from xpkg import util

xpkg_root_var = 'XPKG_ROOT'
xpkg_tree_var = 'XPKG_TREE'
xpkg_repo_var = 'XPKG_REPO'

def parse_dependency(value):
    """
    Basic support for version expression.  Right now it just parses
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


class Exception(BaseException):
    pass

class InstallDatabase(object):
    """
    Manages the on disk database of packages.
    """

    def __init__(self, env_dir):

        # Package db location
        self._db_dir = self.db_dir(env_dir)
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
        Load DB from disk.
        """

        self._db = util.yaml_load(open(self._db_path))

        # Handle the empty database case
        if self._db is None:
            self._db = {}


    def _save_db(self):
        """
        Save DB to disk.
        """

        with open(self._db_path, 'w') as f:
            util.yaml_dump(self._db, f)


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


    def installed(self, name, version=None):
        """
        Returns true if the given package is installed, supplying no version
        will return true if any version is installed.
        """

        info = self.get_info(name)

        if info:
            if version:
                return version == info.get('version', None)
            else:
                return True
        else:
            return False


    def get_rdepends(self, name):
        """
        Get all the packages which depend on this package
        """

        rdepends = []

        for pkg_name, info in self._db.iteritems():
            deps = info.get('dependencies', [])

            for dep in deps:
                dep_name, version = parse_dependency(dep)
                if dep_name == name:
                    rdepends.append(pkg_name)

        return rdepends


    @staticmethod
    def db_dir(root):
        """
        Returns the db directory relative to the given root.
        """
        return os.path.join(root, 'var', 'xpkg')


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

        # If needed this will setup the empty environment
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

        # Make sure the package cache is created
        self._xpa_cache_dir = self.xpa_cache_dir(self._env_dir)

        util.ensure_dir(self._xpa_cache_dir)


    def install(self, input_val):
        """
        Installs the desired input this can be any of the following:
          path/to/description/package.xpd
          path/to/binary/package.xpa
          package
          package==version
        """

        # Check to make sure the install is allowed
        self._install_check(input_val)

        # Install our input
        if input_val.endswith('.xpa'):
            # We have a binary package so install it
            self._install_xpa(input_val)

        elif input_val.endswith('.xpd'):
            # Path is an xpd file load that then install
            xpd = XPD(input_val)

            self._install_xpd(xpd)
        else:
            # The input_val is a package name so parse out the desired version
            # and name
            name, version = self._parse_install_input(input_val)

            # First try and find the xpa (pre-compiled) version of the package
            xpa_path = self._repo.lookup(name, version)

            if xpa_path:
                # Load up the XPA
                xpa = XPA(xpa_path, input_name=input_val)

                # Install the XPA
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


    def build_xpd(self, xpd, dest_path):
        """
        Builds the given package from it's package description (XPD) data.

        Returns the path to the package.
        """

        # Make sure all dependencies are properly installed
        self._install_deps(xpd)

        # Build the package and return the path
        builder = BinaryPackageBuilder(xpd)

        res = builder.build(dest_path, environment = self)

        return res


    def _install_xpd(self, xpd, build_into_env=False):
        """
        Builds package and directly installs it into the given environment.
        """

        # Make sure all dependencies are properly installed
        self._install_deps(xpd)

        if not build_into_env:
            # Build the package as XPD and place it into our cache
            print 'BUILDING(XPD): %s-%s' % (xpd.name, xpd.version)

            xpa_paths = self.build_xpd(xpd, self._xpa_cache_dir)

            # Now install from the xpa package(s) in our cache
            for xpa_path in xpa_paths:
                print 'INSTALLING(XPD from XPA): %s' % xpa_path

                self._install_xpa(xpa_path)
        else:
            # Build the package(s) and install directly into our enviornment
            builder = PackageBuilder(xpd)

            infos = builder.build(self._env_dir, self)

            for info in infos:
                self._pdb.mark_installed(info['name'], info)


    def _install_xpa(self, path):
        """
        Install the given binary Xpkg package.
        """

        # Open up the package
        xpa = XPA(path)

        # Grab the meta data
        info = xpa.info

        # Make sure all dependencies are properly installed
        self._install_deps(xpa)

        print 'INSTALLING(XPA): %s-%s' % (info['name'], info['version'])

        # Install the files into the target environment location
        xpa.install(self._env_dir)

        # Mark the package install
        self._pdb.mark_installed(info['name'], info)


    def _install_deps(self, info):
        """
        Makes sure all the dependencies for the given package are properly
        installed.

        The object should have a property 'dependencies' which is a list of the
        following form: ['package', 'package==1.2.2']

        TODO: handle proper version checks someday
        """

        # Install or report a version conflict for each dependency as needed
        for dep in info.dependencies:
            # Parse the name and version out of the dependency expression
            depname, version = self._parse_install_input(dep)

            # Check whether the package is installed
            installed, version_match = self._is_package_installed(depname, version)

            if not installed:
                # Not installed so install the package
                self.install(dep)

            elif installed and not version_match:
                # Installed but we have the wrong version, so lookup the current
                # package version and throw and error

                current_version = self._pdb.get_info(depname)['version']

                args = (data['name'], data['version'], depname, current_version,
                        version)

                msg = '%s-%s requires package %s at version: %s, but: %s ' \
                      'is installed'

                raise Exception(msg % args)


    def _install_check(self, input_val):
        """
        Checks for the package already being installed, or if there is a
        conflicting version installed.
        """

        # Get all the different packages that could be in an input (and XPD can
        # describe multiple packages)
        package_infos = self._load_package_info(input_val)

        for name, version in package_infos:
            # Check to see if we already have a version of that package
            # installed and if so what version
            installed, version_match = self._is_package_installed(name, version)

            if installed:
                current_version = self._pdb.get_info(name)['version']

            # Bail out if we already have the package installed, or we already
            # have a different version installed
            if installed and version_match:
                args = (name, current_version)
                raise Exception('Package %s already at version: %s' % args)

            elif installed:
                args = (name, current_version, version)

                msg = 'Package %s already at version: %s conflicts with: %s'

                raise Exception(msg % args)


    def _load_package_info(self, input_val):
        """
        Gets all the package info based on the input value, which can be an
        the path to a XPD, or XPA file, or package==version string.
        """

        # Get all name version pairs from the input
        packages = []

        if input_val.endswith('.xpa'):
            # Grab the name out of the XPA metadata
            xpa = XPA(input_val)

            name = xpa.info['name']
            version = xpa.info['version']

            packages.append((name, version))
        elif input_val.endswith('.xpd'):
            # Path is an xpd file load that then install
            xpd_data = util.load_xpd(input_val)

            # Check for all those package combinations
            if 'packages' in xpd_data:
                for name, data in xpd_data['packages'].iteritems():
                    # Default to main version if one doesn't exist
                    if data:
                        version = data.get('version', xpd_data['version'])
                    else:
                        version = xpd_data['version']
                    packages.append((name, version))
            else:
                packages.append((xpd_data['name'], xpd_data['version']))
        else:
            # The input_val must be a package name so try to find the xpd
            # so first try to find the package in a pre-compile manner
            name, version = self._parse_install_input(input_val)

            packages.append((name, version))

        return packages


    def _is_package_installed(self, name, version):
        """
        Returns a tuple saying whether the package is installed, and if so
        it's the proper version, example:

          (installed, version_match, pkgname, version)
        """

        installed = self._pdb.installed(name)
        version_match = self._pdb.installed(name, version)

        return (installed, version_match)


    def remove(self, name):
        """
        Removes the given package from the environment.
        """

        # Determine if another package depends on this one
        rdepends = self._pdb.get_rdepends(name)

        if len(rdepends) > 0:
            args = (name, ', '.join(rdepends))
            raise Exception("Can't remove %s required by: %s" % args)

        # Remove all the files from the db
        info = self._pdb.get_info(name)

        if info:
            # First we remove the files
            for f in sorted(info['files']):
                full_path = os.path.join(self._env_dir, f)

                # We use lexists to test for existence here, because we don't
                # want to de-reference symbolic links, we want to know if the
                # link file itself is present.
                if os.path.lexists(full_path):
                    os.remove(full_path)
                else:
                    # TODO: Log a warning here
                    print 'WARNING: package %s file not found: %s' % (name, full_path)

            # Now remove the directories (reverse so we remove the deeper,
            # dirs first)
            # TODO: don't try remove directories that are owned by other
            # packages
            for d in sorted(info['dirs'], reverse=True):
                full_path = os.path.join(self._env_dir, d)

                # We use lexists to test for existence here, because we don't
                # want to de-reference symbolic links, we want to know if the
                # link file itself is present.
                if os.path.lexists(full_path):
                    if len(os.listdir(full_path)) == 0:
                        os.rmdir(full_path)
                    else:
                        print 'WARNING: not removing dir, has files:',full_path
                else:
                    # TODO: Log a warning here
                    print 'WARNING: package %s directory not found: %s' % (name, full_path)

            # Remove the package from the database
            self._pdb.mark_removed(name)
        else:
            print 'Package %s not installed.' % name


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

        TODO: make this plugable so we can easily port this to multiple
        platforms.
        """

        # Set our path vars, defining different separators based on whether we
        # are directly lists of compiler flags
        cflags = '-I%s' % os.path.join(self._env_dir, 'include')

        lib_dir = os.path.join(self._env_dir, 'lib')
        ldflags = '-L%s' % lib_dir

        env_paths = {
            'PATH' : (os.path.join(self._env_dir, 'bin'), os.pathsep),
            'LD_LIBRARY_PATH' : (os.path.join(self._env_dir, 'lib'), os.pathsep),
            'CFLAGS' : (cflags, ' '),
            'CCFLAGS' : (cflags, ' '),
            'CPPFLAGS' : (cflags, ' '),
            'LDFLAGS' : (ldflags, ' '),
           }

        # Check for the presence of a custom ld-linux.so, we need to use
        # LD_PRELOAD so this overloads the hard coded version in binaries
        if os.path.exists(lib_dir):
            ld_linux = [f for f in os.listdir(lib_dir) if f.startswith('ld-linux')]
        else:
            ld_linux = []

        if len(ld_linux):
            ld_interp = sorted(ld_linux)[0]

            if len(ld_linux) > 1:
                print 'WARNING: multiple ld-linux loaders found, using:',ld_interp

            preload_path = os.path.join(lib_dir, ld_interp)
            env_paths['LD_PRELOAD'] = (preload_path, ':')

        # Place the paths into our enviornment
        for varname, pathinfo in env_paths.iteritems():
            varpath, sep = pathinfo

            cur_var = os.environ.get(varname, None)

            if cur_var:
                os.environ[varname] = varpath + sep + cur_var
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

        return parse_dependency(value)


    @staticmethod
    def xpa_cache_dir(root):
        """
        The directory we hold current built packages.
        """
        return os.path.join(root, 'var', 'xpkg', 'cache')


class XPA(object):
    """
    Represents a package archive.  The xpkg.yml format is:

        {
          'name' : 'hello',
          'version' : '1.0.0',
          'description' : 'My hello world package',
          'dependencies' : ['libgreet'],
          'dirs' : [
            'bin'
          ],
          'files' : [
            'bin/hello'
          ],
          'install_path_offsets' : {
            'install_dir' : '/tmp/install-list',
            'binary_files' : {
               'bin/hello' : [12947, 57290]
            },
            'sub_binary_files' : {
               'bin/hello' : [[1000,1050), [7562,7590,7610]]
            },
            'text_files' : {
               'share/hello/msg.txt' : [5, 100]
            }
          }
        }
    """

    def __init__(self, xpa_path, input_name=None):
        """
        Parses the metadata out of the XPA file.
        """

        # Ensure that the package exists before we open it
        if not os.path.exists(xpa_path):
            args = (input_name, xpa_path)
            msg = 'XPA path for package "%s" does not exist: "%s"' % args
            raise Exception(msg)

        # Only save the XPA path so we don't keep the tarfile itself open
        self._xpa_path = xpa_path

        with tarfile.open(xpa_path) as tar:

            # Pull out and parse the metadata
            self.info = util.yaml_load(tar.extractfile('xpkg.yml'))

        self.dependencies = self.info.get('dependencies', [])

    def install(self, path):
        """
        Extract all the files in the package to the destination directory.
        """

        # Extract all the files
        with tarfile.open(self._xpa_path) as tar:

            file_tar = tar.extractfile('files.tar.gz')

            with tarfile.open(fileobj = file_tar) as file_tar:

                file_tar.extractall(path)

        # Fix up the install paths
        self._fix_install_paths(path)

    def _fix_install_paths(self, dest_path):
        """
        Given the package info go in and replace all occurrences of the original
        install path with the new install path.
        """

        offset_info = self.info['install_path_offsets']
        install_dir = offset_info['install_dir']

        # Make sure we have enough space in binary files to replace the string
        install_len = len(install_dir)
        dest_len = len(dest_path)

        if install_len < dest_len:
            args = (dest_path, dest_len)
            msg = 'Install directory path "%s" exceeds length limit of %d'
            raise Exception(msg % args)

        # Helper function for replacement
        def replace_env_in_files(files, old, new, len_check=False,
                                 replace=None):
            """
            Read the full file, do the replace then write it out

            len_check - when true it makes sure the file length hasn't changed
            this important for binary files.

            replace - an optional external function to use for replacement,
            passed the file file_path, contents, old, and new string.
            """

            for file_path in files:
                full_path = os.path.join(dest_path, file_path)

                contents = open(full_path).read()

                if replace:
                    results = replace(file_path, contents, old, new)
                else:
                    results = contents.replace(old, new)

                # Check to make sure the length hasn't changed
                if len_check:
                    len_contents = len(contents)
                    len_results = len(results)

                    args = (len_contents, len_results)
                    msg = 'Len changed from %d to %d' % args

                    assert len_contents == len_results, msg

                # Write out the final results
                with open(full_path, 'w') as f:
                    f.write(results)

        # Do a simple find and replace in all text files
        replace_env_in_files(files = offset_info['text_files'],
                             old = install_dir,
                             new = dest_path)

        # Create a null padded replacement string for complete instances of
        # null binary strings only.
        null_install_dir = install_dir + '\0'
        null_install_len = len(null_install_dir)

        padded_env = dest_path + ('\0' * (null_install_len - dest_len))

        assert(len(padded_env) == len(null_install_dir))

        # For binary replaces find and replace with a null padded string
        replace_env_in_files(files = offset_info['binary_files'],
                             old = null_install_dir,
                             new = padded_env,
                             len_check = True)

        # Define a function to do our binary substring replacements
        def binary_sub_replace(file_path, contents, old, new):
            """
            This is not very efficient at all, but it does the job for now.
            """

            assert old == install_dir, "install dir not string to replace"
            assert new == dest_path, "dest path not replacement string"

            offsets = offset_info['sub_binary_files'][file_path]

            for offset_list in offsets:
                # Get the start of our all our install strings and the location
                # of the null terminator
                first_offset = offset_list[0]
                null_offset = offset_list[-1]

                # Grab the original string
                input_str = contents[first_offset:null_offset]

                # Find and replace all the install strings
                output_str = input_str.replace(install_dir, dest_path)

                # Length of string we are editing
                initial_len = len(input_str)

                # Length of the string we are replacing it with
                replace_len = len(output_str)

                # Build a full replacement string null padding to make up the
                # difference
                replacer = output_str +  ('\0' * (initial_len - replace_len))

                # Now lets replace that
                results = contents[0:first_offset] + replacer + contents[null_offset:]

                # Make sure we haven't effected length before moving on
                assert len(contents) == len(results)
                contents = results

            return contents

        # Do our binary substring replacements
        replace_env_in_files(files = offset_info['sub_binary_files'],
                             old = install_dir,
                             new = dest_path,
                             len_check = True,
                             replace=binary_sub_replace)


class XPD(object):
    """
    A Xpkg description file, it explains how to build one or more packages.
    """

    def __init__(self, path):
        """
        Load and parse the given XPD
        """

        # Load our data
        if isinstance(path, basestring):
            self._data = util.load_xpd(path)
        else:
            self._data = path

        # Read fields and define properties
        self.name = self._data['name']
        self.version = self._data['version']
        self.dependencies = self._data.get('dependencies', [])
        self.description = self._data.get('description', '')

    def packages(self):
        """
        Return a list of all the packages in this file, each item contains:

          {
            'name' : 'package-name',
            'version' : '1.2.4',
            'description' : 'My awesome package',
            'dirs' : ['dir'],
            'files' : ['dir/a'],
            'dependencies' : ['another-pkg'],
          }
        """

        results = []

        if 'packages' in self._data:
            results = self._get_multi_packages()
        else:
            results.append({
                'name' : self.name,
                'version' : self.version,
                'description' : self.description,
                'files' : [],
                'dependencies' : self.dependencies,
                })

        return results


    def _get_multi_packages(self):
        """
        Get the package info for each sub package, sorted in a order such that
        you don't need to install different ones.
        """

        # Get all the internal packages
        packages = self._data['packages']
        pkg_names = set(packages.keys())

        # Build a graph of the dependencies amongst the packages in this XPD
        dep_graph = {}
        for name, data in self._data['packages'].iteritems():
            if data:
                for dep in data.get('dependencies', []):
                    if dep in pkg_names:
                        dep_graph.setdefault(name, []).append(dep)
            else:
                dep_graph[name] = []

        # Topologically sort them so we start with the package that has no
        # dependencies
        sorted_names = sorted(util.topological_sort(dep_graph))

        # Produce the package data in sorted form
        results = []
        for pkg_name in sorted_names:
            pkg_data = packages.get(pkg_name)
            if pkg_data is None:
                pkg_data = {}

            # Lookup the version and dependencies, for this package, but fall
            # back full package version
            results.append({
                'name' : pkg_name,
                'version' : pkg_data.get('version', self.version),
                'description' : pkg_data.get('description', self.description),
                'dirs' : pkg_data.get('dirs', []),
                'files' : pkg_data.get('files', []),
                'dependencies' : pkg_data.get('dependencies', self.dependencies),
            })

        return results


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
            self._load_xpd(full_path)


    def lookup(self, package, version=None):
        """
        Returns the xpd data for the desired package, None if the package is
        not present.
        """

        xpd_path = self._db.lookup(name=package, version=version)
        if xpd_path:
            result = XPD(xpd_path)
        else:
            result = None

        return result

    def _load_xpd(self, xpd_path):
        """
        Loads the packages found in the given XPD

        @todo - Handle erroneous input more robustly
        """

        # Load the description
        xpd = XPD(xpd_path)

        # Store each package in for the description in our index
        for package_data in xpd.packages():
            # Read the version, defaulting the full description version if there
            # is none for this package

            self._db.store(name=package_data['name'],
                           version=package_data['version'],
                           data=xpd_path)


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
        #print 'Build package repo from dir:',path

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
                info = util.yaml_load(tar.extractfile('xpkg.yml'))

            # Get the name and version of the package from the internal info
            name = info['name']
            version = info.get('version', '')

            # Store the path to the file in the package DB
            #print 'Storing "%s" as %s version: %s' % (full_path, name, version)

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

        Current the data is the path to the archive itself.
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
        if not isinstance(package_xpd, XPD):
            self._xpd = XPD(package_xpd)
        else:
            self._xpd = package_xpd

        self._work_dir = None
        self._target_dir = None


    def build(self, target_dir, environment = None):
        """
        Right now this just executes instructions inside the XPD, but in the
        future we can make this a little smarter.

        It returns the info structure for the created package.  See the XPA
        class for the structure of the data returned.
        """

        # Create our temporary directory
        self._work_dir = tempfile.mkdtemp(suffix = '-xpkg-' + self._xpd.name)

        # TODO: LOG THIS
        print 'Working in:',self._work_dir

        self._target_dir = target_dir

        try:
            # Store the current environment
            env_vars = util.EnvStorage(store = True)

            # If we have an environment apply it's variables so the build can
            # reference the libraries installed in it
            if environment:
                environment.apply_env_variables()
                self._env_dir = environment._env_dir
            else:
                self._env_dir = ''

            # Fetches and unpacks all the required sources for the package
            self._get_sources()

            # Determine what directory we have to do the build in
            dirs = os.listdir(self._work_dir)

            if 'build-dir' in self._xpd._data:
                # If the user specifies a build directory use it
                rel_build_dir = self._xpd._data['build-dir']
                build_dir = os.path.join(self._work_dir, rel_build_dir)

                # Make sure the directory exists
                util.ensure_dir(build_dir)
            elif len(dirs) == 1:
                build_dir = os.path.join(self._work_dir, dirs[0])
            else:
                build_dir = self._work_dir

            with util.cd(build_dir):
                # Standard build configure install
                self._configure()

                self._build()

                new_paths = self._install()
        finally:
            # Put back our environment
            env_vars.restore()

            self._env_dir = ''

            # Make sure we cleanup after we are done
            shutil.rmtree(self._work_dir)

        return self._create_info(new_paths)


    def _get_sources(self):
        """
        Fetches and unpacks all the needed source files.
        """

        # Download and unpack our files
        for filehash, info in self._xpd._data['files'].iteritems():

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
        if 'configure' in self._xpd._data:
            self._run_cmds(self._xpd._data['configure'])


    def _build(self):
        """
        Builds the desired package.
        """

        self._run_cmds(self._xpd._data['build'])


    def _install(self):
        """
        Installs the package, keeping track of what files it creates.
        """

        pre_paths = set(util.list_files(self._target_dir))

        self._run_cmds(self._xpd._data['install'])

        post_paths = set(util.list_files(self._target_dir))

        new_paths = post_paths - pre_paths

        return new_paths


    def _run_cmds(self, raw):
        """
        Runs either a single or list of commands, subbing in all variables as
        needed for each command.
        """

        # If don't have a list of cmds make a single cmd list
        if isinstance(raw, list):
            cmds = raw
        else:
            cmds = [raw]

        # Run each command in turn
        for raw_cmd in cmds:
            # Make sure we have env_root when needed
            if raw_cmd.count('%(env_root)s') and len(self._env_dir) == 0:
                raise Exception('Package references environment root, '
                                'must be built in an environment')

            # Sub in our variables into the commands
            cmd = raw_cmd % {
                'jobs' : str(util.cpu_count()),
                'prefix' : self._target_dir,
                'env_root' : self._env_dir,
            }

            # Run our command
            util.shellcmd(cmd)


    def _create_info(self, new_paths):
        """
        Creates the info structure from the new files and the package XPD info.
        """

        # Split paths by files and directories
        new_dirs = set()
        new_files = set()

        for path in new_paths:
            if os.path.isdir(os.path.join(self._target_dir, path)):
                new_dirs.add(path)
            else:
                new_files.add(path)

        # Find all instances of our install path in our data
        install_path_offsets = self._find_path_offsets(new_files)

        if len(self._xpd.packages()) == 1:
            # Single package path
            infos = [{
                'name' : self._xpd.name,
                'version' : self._xpd.version,
                'description' : self._xpd.description,
                'dependencies' : self._xpd.dependencies,
                'dirs' : list(new_dirs),
                'files' : list(new_files),
                'install_path_offsets' : install_path_offsets,
            }]
        else:
            # Find the catch all package if there is one, and make sure there is
            # only one
            packages = []
            catch_all = None

            for data in self._xpd.packages():
                name = data['name']

                if 'files' in data:
                    packages.append((name, data))
                elif catch_all is None:
                    catch_all = (name, data)
                else:
                    # Throw an error if we already have a package with that
                    # pattern
                    args = (name, catch_all[0])
                    msg = 'Package %s cannot be grab all files, %s already does'
                    raise Exception(msg % args)

            def get_offsets_for_files(files):
                """
                Get the subset of path offsets needed for these files.
                """

                # Create default empty offset list section
                offset_names = ['binary_files', 'sub_binary_files', 'text_files']
                package_offsets = dict(zip(offset_names, [[]] * 3))
                package_offsets['install_dir'] = install_path_offsets['install_dir']

                # Search the offset list and make sure to include any the
                # offsets for any files found in this package
                for offset_name in offset_names:
                    offset_files = install_path_offsets[offset_name]

                    for f in files:
                        if f in offset_files:
                            package_offsets[offset_name].append(f)

                return package_offsets


            def get_needed_dirs(files):
                """
                Get the set of directories needed (this is O(n^2) in the
                number of files, would be fast with a trie made of the files
                or dirs)
                """
                dirs = []

                for f in files:
                    for d in new_dirs:
                        if f.startswith(d):
                            dirs.append(d)

                return dirs


            # TODO: go through and check if expressions from different packages
            # match all the files and print out a warning
            file_set = set(new_files)
            used_dirs = set()
            infos = []

            # TODO: handle directories

            # Go through the non catch all package gathering up files
            for name, data in packages:
                # Go through and match files
                used_files = set()

                for pattern in data['files']:
                    # Build our pattern
                    regex = re.compile(pattern)

                    # Match against files
                    for f in file_set:
                        match = regex.match(f)

                        # Mark file as used
                        if match and match.span()[1] == len(f):
                            used_files.add(f)

                # Grab the directories needed by this package, and mark them
                # as used
                dirs = get_needed_dirs(used_files)
                used_dirs.update(dirs)

                # Get the install path offsets for this package
                package_offsets = get_offsets_for_files(used_files)

                # Build final info object
                new_info = {
                    'name' : name,
                    'version' : data['version'],
                    'description' : data['description'],
                    'dependencies' : data['dependencies'],
                    'dirs' : dirs,
                    'files' : list(used_files),
                    'install_path_offsets' : package_offsets,
                }

                infos.append(new_info)

                # Remove the used_files from our file set
                file_set = file_set - used_files

            # If we have a catch all
            num_files_left = len(file_set)

            if catch_all:
                if num_files_left == 0:
                    # Warn if we don't have any files
                    print 'WARNING: %d files left un-packaged' % num_files_left
                else:
                    # Otherwise build our info object
                    name, data = catch_all

                    # Get the offsets needed for the files left
                    package_offsets = get_offsets_for_files(file_set)

                    # Get all the directories needed for our files
                    dirs = get_needed_dirs(used_files)
                    used_dirs.update(dirs)

                    # Find out what directories are left
                    unused_dirs = new_dirs - used_dirs

                    new_info = {
                        'name' : name,
                        'version' : data['version'],
                        'description' : data['description'],
                        'dependencies' : data['dependencies'],
                        'dirs' : dirs + list(unused_dirs),
                        'files' : list(file_set),
                        'install_path_offsets' : package_offsets,
                    }

                    infos.append(new_info)
            else:
                # If we don't have a catch all warn we do have files
                if num_files_left > 0:
                     print 'WARNING: %d files left un-packaged' % num_files_left

        return infos


    def _find_path_offsets(self, paths):
        """
        Search the given paths of the packages for instances of the targetdir.
        Here is some example output:

          {
            'install_dir' : '/tmp/xpkg-720617e18f95633fec423f7a522d88eb',
            # The location of the null-terminated install string
            'binary_files' : {
               'bin/hello' : [12947, 57290]
            }
            # The location of the install string and the null of the string
            # it's located in
            'sub_binary_files' : {
               'bin/hello' : [[1000, 1015], [12947, 12965]]
            }
            # The location in each file of the string we have to replace
            'text_files' : {
               'share/hello/message.txt' : [23,105]
            }
          }
        """

        # Get just our files
        install_dir = self._target_dir
        full_paths = [(os.path.join(install_dir, p),p) for p in paths]
        files = [p for p in full_paths
                 if os.path.isfile(p[0]) and not os.path.islink(p[0])]

        # State we are finding
        binary_files = {}
        sub_binary_files = {}
        text_files = {}

        for full_path, filepath in files:
            # Load file into memory
            contents = open(full_path).read()

            # Find the locations of all strings
            offsets = [m.start() for m in re.finditer(install_dir, contents)]

            # Count number of zero bytes to determine if we are binary or not
            # WARNING: this will fail with UTF16 or UTF32 files
            zeros = contents.count('\0')

            if len(offsets) > 0:
                # If we found any record the fact
                if zeros > 0:
                    binary_offsets = []
                    sub_binary_offsets = []
                    prev_null_term = None

                    # Stores each offset as full or a binary substring
                    for offset in offsets:
                        # Find the location of the null termination
                        null_term = contents.find('\0', offset)

                        if null_term == offset + len(install_dir):
                            # Record strings that are just null terminated
                            binary_offsets.append(offset)
                        else:
                            if null_term == prev_null_term:
                                # This is part of the same string as the previous
                                # instance, add to that list
                                sub_binary_offsets[-1].insert(-1, offset)
                            else:
                                # If not record the offset and null location
                                sub_binary_offsets.append([offset, null_term])

                            prev_null_term = null_term

                    # Store our results for this file path if needed
                    if len(binary_offsets) > 0:
                        binary_files[filepath] = binary_offsets

                    if len(sub_binary_offsets) > 0:
                        # Store the results
                        sub_binary_files[filepath] = sub_binary_offsets

                else:
                    # If we have found text files record the fact
                    text_files[filepath] = offsets


        # Form information into a dict return to the user
        results = {
            'install_dir' : install_dir,
            'binary_files' : binary_files,
            'sub_binary_files' : sub_binary_files,
            'text_files' : text_files,
        }

        return results


class BinaryPackageBuilder(object):
    """
    Turns XPD files into binary packages. They are built and installed into a
    temporary directory.

    The binary package format starts with an uncompressed tar file containing:
         xpkg.yml - Contains the package information
         files.tar.gz - Archive of files rooted in the env
    """

    def __init__(self,  package_xpd):
        if not isinstance(package_xpd, XPD):
            self._xpd = XPD(package_xpd)
        else:
            self._xpd = package_xpd
        self._work_dir = None
        self._target_dir = None


    def build(self, storage_dir, environment = None):
        """
        Run the standard PackageBuilder then pack up the results in a package.
        """

        # Create our temporary directory
        name = self._xpd.name
        self._work_dir = tempfile.mkdtemp(suffix = '-xpkg-install-' + name)

        # TODO: make this a hash of something meaning, full
        pad_hash = util.hash_string(name)
        install_dir = os.path.join(self._work_dir, 'install-' + pad_hash)

        # TODO: LOG THIS
        print 'Binary working in:',self._work_dir

        try:
            # Build the package(s)
            builder = PackageBuilder(self._xpd)
            infos = builder.build(install_dir, environment)

            # Build packages and get their paths
            dest_paths = [self._create_package(install_dir, storage_dir, info)
                          for info in infos]

        finally:
            # Make sure we cleanup after we are done
            # Don't do this right now
            shutil.rmtree(self._work_dir)

        return dest_paths

    def _create_package(self, install_dir, storage_dir, info):
        """
        Creates a package from the given package info.

        The path to that archive is returned.
        """

        # Tar up the files
        file_tar = os.path.join(self._work_dir, 'files.tar.gz')

        with tarfile.open(file_tar, "w:gz") as tar:
            for entry_name in info['files']:
                full_path = os.path.join(install_dir, entry_name)
                tar.add(full_path, arcname=entry_name)

        # Create our metadata file
        meta_file = os.path.join(self._work_dir, 'xpkg.yml')
        with open(meta_file, 'w') as f:
            util.yaml_dump(info, f)

        # Create our package
        package_name = self._get_package_name(info)
        package_tar = os.path.join(self._work_dir, package_name)

        with tarfile.open(package_tar, "w") as tar:
            tar.add(meta_file, arcname=os.path.basename(meta_file))
            tar.add(file_tar, arcname=os.path.basename(file_tar))

        # Move to the desired location
        dest_path = os.path.join(storage_dir, package_name)

        if os.path.exists(dest_path):
            os.remove(dest_path)

        shutil.move(package_tar, storage_dir)

        return dest_path


    def _get_package_name(self, info):
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
            'name' : info['name'],
            'version' : info['version'],
            'arch' : arch,
            'linkage' : linkage.lower(),
            'kernel' : kernel.lower(),
        }

        # Create our version
        fmt_str = '%(name)s_%(version)s_%(arch)s_%(linkage)s_%(kernel)s.xpa'

        return fmt_str % args
