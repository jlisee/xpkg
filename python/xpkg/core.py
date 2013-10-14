# Author: Joseph Lisee <jlisee@gmail.com>

# Python Imports
import json
import os
import tarfile

from collections import defaultdict

# Project Imports
from xpkg import util
from xpkg import build


xpkg_root_var = 'XPKG_ROOT'
xpkg_tree_var = 'XPKG_TREE'
xpkg_repo_var = 'XPKG_REPO'
xpkg_local_cache_var = 'XPKG_LOCAL_CACHE'


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

        # Build a list of directories and the counts of package that reference
        # them
        self._gen_dir_counts()


    def _save_db(self):
        """
        Save DB to disk.
        """

        with open(self._db_path, 'w') as f:
            util.yaml_dump(self._db, f)


    def _gen_dir_counts(self):
        """
        Generates reference counts of directories, that can be used to see
        if a package is the last one using that directory.
        """

        self._dirs = defaultdict(int)
        for data in self._db.itervalues():
            for d in data['dirs']:
                self._dirs[d] += 1


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


    def dir_references(self, d):
        """
        Returns how many packages are using this directory.
        """

        return self._dirs[d]

    @staticmethod
    def db_dir(root):
        """
        Returns the db directory relative to the given root.
        """
        return os.path.join(root, 'var', 'xpkg')


class Environment(object):
    """
    This class manages the local package environment.
    """

    def __init__(self, env_dir=None, create=False, tree_path=None,
                 repo_path=None, verbose=False):
        """
          env_dir - path to the environment dir
          create - create the environment if it does exist
          tree_path - URL for a XPD tree
          repo_path - URL for a XPA package archive
          verbose - print all build commands to screen
        """

        if env_dir is None:
            if xpkg_root_var in os.environ:
                self._env_dir = os.environ[xpkg_root_var]
            else:
                raise Exception("No XPKG_ROOT not defined, can't find environment")
        else:
            self._env_dir = env_dir

        self.root = self._env_dir

        self.verbose = verbose

        # Error out if we are not creating and environment and this one does
        # not exist
        if not os.path.exists(self._env_dir) and not create:
            raise Exception('No Xpkg package DB found in root "%s"' % self._env_dir)

        # If needed this will setup the empty environment
        self._pdb = InstallDatabase(self._env_dir)

        def get_paths(base_path, env_var):
            """
            Parse class argument and environment variables to get path.
            """

            # Get the raw path from our given value, or the environment variable
            raw_path = None

            if base_path:
                raw_path = base_path
            elif env_var in os.environ:
                raw_path = os.environ[env_var]
            else:
                raw_path = None

            # Turn that raw path into a list
            if raw_path:
                paths = raw_path.split(':')
            else:
                paths = []

            return paths

        # Setup the package tree to either load from the given path or return
        # no packages
        self.tree_paths = get_paths(tree_path, xpkg_tree_var)

        if len(self.tree_paths) == 1:
            self._tree = FilePackageTree(self.tree_paths[0])
        elif len(self.tree_paths) > 0:
            trees = [FilePackageTree(t) for t in self.tree_paths]
            self._tree = CombinePackageSource(trees)
        else:
            self._tree = EmptyPackageSource()

        # Setup the package repository so we can install pre-compiled packages
        self.repo_paths = get_paths(repo_path, xpkg_repo_var)

        if len(self.repo_paths) == 1:
            self._repo = FilePackageRepo(self.repo_paths[0])
        elif len(self.repo_paths) > 0:
            repos = [FilePackageRepo(t) for t in self.repo_paths]
            self._repo = CombinePackageSource(repos)
        else:
            self._repo = EmptyPackageSource()

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
            xpa = self._repo.lookup(name, version)

            if xpa:
                # Install the XPA
                self._install_xpa(xpa)

            else:
                # No binary package try, so lets try and find a description in
                # the package tree
                xpd_data = self._tree.lookup(name, version)

                if xpd_data is None:
                    msg = "Cannot find description for package: %s" % input_val
                    raise Exception(msg)

                # Install the XPD
                self._install_xpd(xpd_data)


    def build_xpd(self, xpd, dest_path, verbose=False):
        """
        Builds the given package from it's package description (XPD) data.

        Returns the path to the package.
        """

        # Determine if we are doing a verbose build
        verbose_build = verbose or self.verbose

        # Make sure all dependencies are properly installed
        self._install_deps(xpd, build=True)

        # Build the package and return the path
        builder = build.BinaryPackageBuilder(xpd)

        res = builder.build(dest_path, environment=self,
                            output_to_file=not verbose_build)

        return res


    def _install_xpd(self, xpd, build_into_env=False):
        """
        Builds package and directly installs it into the given environment.

          xpd - an XPD describing the package to install.
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
            # Build the package(s) and install directly into our environment
            builder = build.PackageBuilder(xpd)

            infos = builder.build(self._env_dir, environment=self,
                            output_to_file=not self.verbose)

            for info in infos:
                self._pdb.mark_installed(info['name'], info)


    def _install_xpa(self, path):
        """
        Install the given binary Xpkg package.
        """

        # Open up the package
        if isinstance(path, XPA):
            xpa = path
        else:
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


    def _install_deps(self, info, build=False):
        """
        Makes sure all the dependencies for the given package are properly
        installed.

        The object should have a property 'dependencies' which is a list of the
        following form: ['package', 'package==1.2.2']

        TODO: handle proper version checks someday
        """

        # Get the full dep list based on whether we need the build dependencies
        deps = info.dependencies

        if build:
            deps = info.dependencies + info.build_dependencies

        # Install or report a version conflict for each dependency as needed
        for dep in deps:
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

                args = (info.name, info.version, depname, current_version,
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
                    elif self._pdb.dir_references(d) == 1:
                        # Only warn when we are the last package referencing this dir
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


    def get_env_variables(self):
        """
        TODO: make this plugable so we can easily port this to multiple
        platforms.
        """

        # Set our path vars, defining different separators based on whether we
        # are directly lists of compiler flags
        cflags = '-I%s' % os.path.join(self._env_dir, 'include')

        lib_dir = os.path.join(self._env_dir, 'lib')
        ldflags = '-L%s -L%s' % (lib_dir, '"/home/with space"')

        # Default list of bin paths
        bin_paths = [os.path.join(self._env_dir, 'bin')]

        # Extra directories which we want on the path if they exist
        extra_bin_dirs = ['usr/bin', 'usr/sbin', 'sbin']

        for d in extra_bin_dirs:
            full_path = os.path.join(self._env_dir, d)
            if os.path.exists(full_path):
                bin_paths.append(full_path)

        env_paths = {
            'PATH' : (os.pathsep.join(bin_paths), os.pathsep),
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

        return env_paths


    def apply_env_variables(self):
        """
        Change the current environment variables so that we can use the things
        are in that environment.
        """

        env_paths = self.get_env_variables()

        # Place the paths into our environment
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


    @staticmethod
    def local_cache_dir():
        """
        Local user cache directory.
        """

        if xpkg_local_cache_var in os.environ:
            return os.environ[xpkg_local_cache_var]
        else:
            return os.path.expanduser(os.path.join('~', '.xpkg', 'cache'))


    @staticmethod
    def log_dir(root):
        """
        The directory we place build logs
        """
        return os.path.join(root, 'var', 'xpkg', 'log')


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

    def __init__(self, xpa_path, input_name=None, info=None):
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

        # If not given the manifest info, read it out of the XPA
        if info is None:
            # Read the manifest out of the XPA
            self.info = self._read_info(xpa_path)
        else:
            self.info = info

        self.name = self.info['name']
        self.version = self.info['version']
        self.dependencies = self.info.get('dependencies', [])

        # We have no build deps, because were already built, but we want to
        # maintain a similar interface
        self.build_dependencies = []


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


    def _read_info(self, xpa_path):
        """
        Read the manifest data out of the xpa_path.
        """

        with tarfile.open(xpa_path) as tar:

            # Pull out and parse the metadata
            return util.yaml_load(tar.extractfile('xpkg.yml'))


    def _fix_install_paths(self, dest_path):
        """
        Given the package info go in and replace all occurrences of the original
        install path with the new install path.
        """

        offset_info = self.info['install_path_offsets']
        # Make sure the type is a string, incase it because unicode somehow
        # TODO: see if our caching layer is giving us unicode strings
        install_dir = str(offset_info['install_dir'])

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
        self.build_dependencies = self._data.get('build-dependencies', [])
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


class EmptyPackageSource(object):
    """
    A source of package descriptions or binary packages with nothing in it.
    """

    def lookup(self, package, version=None):
        return None


class CombinePackageSource(object):
    """
    A simple way to query multiple package sources (trees, or repos).
    """

    def __init__(self, sources):
        self._sources = sources

    def lookup(self, package, version=None):
        """
        Get the most recent version of the package in any source, or the
        version specified if it exists in any.
        """

        if version:
            # We have a version so search our trees in order until we find it
            for source in self._sources:
                result = source.lookup(package, version)

                # Bail out if we have found the package
                if result:
                    break
        else:
            # With no version we grab all version of the package then get the
            # most recent

            # Grab all the package versions
            pkgs = []

            for source in self._sources:
                result = source.lookup(package)
                if result:
                    pkgs.append(result)

            # If we have any packages sort by the version
            if len(pkgs) > 0:
                sorter = lambda a,b: util.compare_versions(a.version, b.version)
                sorted_pkgs = sorted(pkgs, cmp=sorter)

                # Get the data for the most recent version
                result = sorted_pkgs[-1]
            else:
                result = None

        return result


class FilePackageTree(object):
    """
    Allows for named and versioned lookup of packages from a directory full of
    description.
    """

    def __init__(self, path):
        # Holds the package information
        self._db = PackageDatabase()

        # Make sure our path exists
        if not os.path.exists(path):
            raise Exception('Package tree path "%s" does not exist' % path)

        # Create our cache
        self._cache = FileParseCache(path, 'tree')

        # Get information on all the dicts found in the directory
        for full_path in util.match_files(path, '*.xpd'):
            self._load_xpd(full_path)

        # Save cached info
        self._cache.save_to_disk()


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

        # Load the data through the cache
        data = self._cache.load(xpd_path, lambda p: XPD(p)._data)

        # Create the description
        xpd = XPD(data)

        # Store each package in for the description in our index
        for package_data in xpd.packages():
            # Read the version, defaulting the full description version if there
            # is none for this package

            self._db.store(name=package_data['name'],
                           version=package_data['version'],
                           data=xpd_path)


class FilePackageRepo(object):
    """
    Allows for named and versioned lookup of pre-built binary packages from a
    directory full of them.

    The JSON caching results is about 4 times faster than PyYAML using
    the C loader.
    """

    def __init__(self, path):
        #print 'Build package repo from dir:',path

        # Holds are information
        self._db = PackageDatabase()

        # Make sure our path exists
        if not os.path.exists(path):
            raise Exception('Package repo path "%s" does not exist' % path)

        # Create our cache
        cache = FileParseCache(path, 'repo')

        # Get information on all the dicts found in the directory
        for full_path in util.match_files(path, '*.xpa'):
            # Load the data through the cache
            info = cache.load(full_path, lambda p: XPA(p).info)

            xpa = XPA(full_path, info=info)

            # Store the object in our repo
            self._db.store(name=xpa.name, version=xpa.version, data=xpa)

        # Save cached info
        cache.save_to_disk()


    def lookup(self, package, version=None):
        """
        Returns the XPA representing binary package, if it doesn't exist None is
        returned.
        """

        return self._db.lookup(name=package, version=version)


class FileParseCache(object):
    """
    Cache for the tree and file parser.  This takes advantage of the
    speed advantage of the JSON parser (and maybe some better future
    optimized format)
    """

    def __init__(self, path, name):
        self._path = path

        # Determine the path to our cache
        cache_root = Environment.local_cache_dir()

        hash_key = self._path + name
        hash_file = 'md5-%s.json' % util.hash_string(hash_key)

        self._cache_path = os.path.join(cache_root, name, hash_file)

        # Load the cache from disk
        self.load_from_disk()


    def load(self, path, load_func):
        """
        Loads data from a cache of this structure:
        {
          'full/path/to/repo/file.xpa' : {
            'mtime' : 1339007845.0,
            'data' : {
              ....
            }
          }
        }

        Arguments:

          path - we are loading
          load_func - takes path, returns dict we are caching

        Return None if nothing is found in the cache for this path.
        """

        load = False

        # Stat the desired file
        mtime = os.stat(path).st_mtime

        # Check for file in cache
        if path in self._cache:
          # If the current file is newer than the cache, load it
          if mtime > self._cache[path]['mtime']:
              load = True
        else:
            load = True

        if load:
            # Load data
            data = load_func(path)

            # Update the cache
            self._cache[path] = {
                'mtime' : mtime,
                'data' : data,
                }
        else:
            # Load from cache
            data = self._cache[path]['data']

        # Return XPA
        return data


    def load_from_disk(self):
        """
        Load the cached JSON file.
        """

        if os.path.exists(self._cache_path):
            self._cache = json.load(open(self._cache_path))
        else:
            self._cache = {}


    def save_to_disk(self):
        """
        Saves XPA info manifests to JSON cache file.
        """

        cache_dir, _ = os.path.split(self._cache_path)

        util.ensure_dir(cache_dir)

        with open(self._cache_path, 'w') as f:
            json.dump(self._cache, f)


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
        package, or the most recent version.  If the version can't be found,
        None is returned.

        Currently the data is the path to the archive itself.
        """

        # Get all versions of a package
        versions = self._db.get(name, [])

        res = None

        if len(versions):
            if version and (version in versions):
                # Version specified and we have it
                res = versions[version]
            elif version is None:
                # Sorted the version data pairs
                sorted_versions = sorted(
                    versions.items(),
                    cmp = lambda a,b: util.compare_versions(a[0], b[0]))

                # Get the data for the most recent version
                return sorted_versions[-1][1]

        return res
