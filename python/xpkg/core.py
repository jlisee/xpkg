# Author: Joseph Lisee <jlisee@gmail.com>

# Python Imports
import json
import os
import stat
import subprocess
import tarfile

from collections import defaultdict

# Library Imports
import toposort

# Project Imports
from xpkg import build
from xpkg import envvars
from xpkg import linux
from xpkg import paths
from xpkg import util


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
        self._db_path = os.path.join(self._db_dir, 'data.yml')
        self._file_info_dir = os.path.join(self._db_dir, 'file_info')

        # Create package database if it doesn't exist
        if not os.path.exists(self._db_path):
            self._create_db()

        if not os.path.exists(self._file_info_dir):
            os.makedirs(self._file_info_dir)

        # Load database
        self._load_db()

        # Create empty file data cache
        self._file_info = {}


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

        # Split into info and file info
        file_keys = set(['files', 'install_path_offsets'])
        bare_info = {}
        file_info = {}

        for key, value in info.iteritems():
            if key in file_keys:
                file_info[key] = info[key]
            else:
                bare_info[key] = info[key]

        # Mark package with the current installed version
        self._db[name] = bare_info

        # Save the data to disk
        self._save_db()

        self._save_file_info(name, file_info)


    def mark_removed(self, name):
        """
        Marks the current package installed
        """

        # Mark package with the current installed version
        del self._db[name]

        # Save the data to disk
        self._save_db()

        # Remove the file info
        self._remove_file_info(name)


    def iter_packages(self):
        """
        Returns an iterator of (package, version) pairs
        """

        for k in self._db.iteritems():
            yield k


    def get_info(self, name, with_files=False):
        """
        Return the information on the installed package, returns None if it
        doesn't exist.
        """

        info = self._db.get(name, None)

        if with_files:
            file_info = self._get_file_info(name)

            info.update(file_info)

        return info


    def get_info_for_path(self, path):
        """
        Return the information on the installed package which contains the file,
        returns None if it doesn't exist.
        """
        # TODO: update the database to maintain a mapping table from file to
        # package

        for name, contents in self._db.iteritems():
            # Grab file info
            file_info = self._get_file_info(name)
            contents.update(file_info)

            # Check for file
            for f in contents['files']:
                if f == path:
                    return contents
            for f in contents['dirs']:
                if f == path:
                    return contents

        return None


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


    # File info guys
    def _save_file_info(self, name, file_info):
        """
        Save file info to disk.
        """

        # Save into the cache
        self._file_info[name] = file_info

        # Form our path
        file_info_path = os.path.join(self._file_info_dir, name + '.json')

        # Load
        with open(file_info_path, 'w') as f:
            json.dump(file_info, f)


    def _get_file_info(self, name):
        """
        Load file info from disk.
        """

        # Try to load from in memory cache first
        if name in self._file_info:
            return self._file_info[name]

        # Build path to the file
        file_info_path = os.path.join(self._file_info_dir, name + '.json')

        # Load the data
        with open(file_info_path) as f:
            file_info = json.load(f)

        # Cache and return the data
        self._file_info[name] = file_info

        return file_info


    def _remove_file_info(self, name):
        """
        Remove file info from disk.
        """

        if name in self._file_info:
            del self._file_info[name]

        file_info_path = os.path.join(self._file_info_dir, name + '.json')

        os.remove(file_info_path)


    @staticmethod
    def db_dir(root):
        """
        Returns the db directory relative to the given root.
        """
        return os.path.join(root, 'var', 'xpkg', 'db')


class Settings(object):
    """
    Settings for the current environment.

    TODO: add versioning to the on disk format
    """

    def __init__(self, path):
        """
        Create settings object with the stored settings from the given path.
        """

        # Load the settings data if the file exists
        if os.path.exists(path):
            settings_data = util.yaml_load(open(path))
        else:
            settings_data = None


        # Lookup data based on the presence of the configuration data
        if settings_data is None:
            toolset_dict = None
            self.name = 'none'
        else:
            toolset_dict = settings_data.get('toolset', None)
            self.name = settings_data.get('name', 'unknown')

        # Create toolset if possible otherwise get the default
        if toolset_dict is None:
            self.toolset = build.Toolset.lookup_by_name(build.DefaultToolsetName)
        else:
            self.toolset = build.Toolset.create_from_dict(toolset_dict)



class Environment(object):
    """
    This class manages the local package environment.
    """

    SETTINGS_PATH = os.path.join('var', 'xpkg', 'env.yml')

    @staticmethod
    def init(env_dir, name, toolset_name=None):
        """
        Initialize the environment in the given directory.
        """

        # Bail out with an error if the environment already exists
        if Environment.env_exists(env_dir):
            raise Exception('Environment already exists in: %s' % env_dir)

        # Create the empty db file (this triggers database file creation)
        pdb = InstallDatabase(env_dir)

        # Make sure we have a valid ld.so symlink
        #linux.update_ld_so_symlink(env_dir)

        # Lookup our toolset and translate to dict
        toolset = build.Toolset.lookup_by_name(toolset_name)

        # Create our settings dict and write it disk
        settings = {
            'name' : name,
            'toolset' : toolset.to_dict(),
        }

        # For path to our settings files, and save it
        settings_path = os.path.join(env_dir, Environment.SETTINGS_PATH)

        with open(settings_path, 'w') as f:
            util.yaml_dump(settings, f)


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
            if envvars.xpkg_root_var in os.environ:
                self._env_dir = os.environ[envvars.xpkg_root_var]
            else:
                raise Exception("No XPKG_ROOT not defined, can't find environment")
        else:
            self._env_dir = env_dir

        self.root = self._env_dir

        self.verbose = verbose

        # Error out if we are not creating and environment and this one does
        # not exist
        if not self.env_exists(self._env_dir) and not create:
            raise Exception('No Xpkg environment found in "%s"' % self._env_dir)

        # Create environment if needed
        if not self.env_exists(self._env_dir) and create:
            self.init(self._env_dir, 'default', build.DefaultToolsetName)

        # If needed this will setup the empty environment
        self._pdb = InstallDatabase(self._env_dir)

        # Load the settings
        settings = Settings(self.env_settings_path(self._env_dir))

        self.name = settings.name
        self.toolset = settings.toolset

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
        self.tree_paths = get_paths(tree_path, envvars.xpkg_tree_var)

        if len(self.tree_paths) == 1:
            self._tree = FilePackageTree(self.tree_paths[0])
        elif len(self.tree_paths) > 0:
            trees = [FilePackageTree(t) for t in self.tree_paths]
            self._tree = CombinePackageSource(trees)
        else:
            self._tree = EmptyPackageSource()

        # Setup the package repository so we can install pre-compiled packages
        self.repo_paths = get_paths(repo_path, envvars.xpkg_repo_var)

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

        install_obj = None

        # Check to make sure the install is allowed
        self._install_check(input_val)

        # Install our input
        if input_val.endswith('.xpa'):
            # We have a binary package so install it
            install_obj = XPA(input_val)

        elif input_val.endswith('.xpd'):
            # Path is an xpd file load that then install
            install_obj = XPD(input_val)

        else:
            # The input_val is a package name so parse out the desired version
            # and name
            name, version = self._parse_install_input(input_val)

            # First try and find the xpa (pre-compiled) version of the package
            install_obj = self._repo.lookup(name, version)

            if not install_obj:
                # No binary package try, so lets try and find a description in
                # the package tree
                install_obj = self._tree.lookup(name, version)

                if install_obj is None:
                    msg = "Cannot find description for package: %s" % input_val
                    raise Exception(msg)

        # Install what we have
        if install_obj:
            # Check for cycles in the dependency graph
            self._check_deps(install_obj)

            # Install as needed
            if isinstance(install_obj, XPA):
                self._install_xpa(install_obj)
            elif isinstance(install_obj, XPD):
                self._install_xpd(install_obj)
            else:
                raise Error("Incorrect install obj")


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


    def _check_deps(self, input_info):
        """
        An XPA or XPD whose deps we are going to check.  Make sure we can
        install them, and that we don't have any loops.
        """

        seen_deps = set([input_info.name])
        to_check = [input_info]
        dep_graph = defaultdict(set)

        # TODO: build list of every version of each package available
        # TODO: pull info from _install_deps so we can provide a list of deps
        # to install

        # Keep working through packages until there are none left and we
        # have all the edge dependencies
        while len(to_check) > 0:
            # Get an object to test
            info = to_check.pop()
            cur_name = info.name
            #print cur_name

            # Build a list of the names of the deps this package needs, we
            # include build deps of files
            deps = self._resolve_deps(info.dependencies)
            #print '  Deps:',deps

            if isinstance(info, XPD):
                build_deps = self._resolve_deps(info.build_dependencies)
                #print '  Build deps:',deps
                deps += build_deps

            # Add these to the list of seen deps
            for dep in deps:
                # The input_val is a package name so parse out the desired
                # version and name
                name, version = self._parse_install_input(dep)

                # Turn the deps into further objects to check
                next_info = self._repo.lookup(name, version)

                if not next_info:
                    next_info = self._tree.lookup(name, version)

                if next_info is None:
                    msg = "Cannot find description for package: %s" % dep
                    raise Exception(msg)

                # Catch a package depending on it's self
                is_installed = self._is_package_installed(name, version)

                if not is_installed and cur_name == name:
                    raise Exception('Package "%s" depends on it\'s self' % name)

                # Now add the edge list
                dep_graph[cur_name].add(name)

                # If we have not seen this before add it to the list to check
                if not dep in seen_deps:
                    to_check.append(next_info)
                    seen_deps.add(cur_name)

        # Run a topological sort to find see if we have any cycles
        try:
            # TODO: replace this with our internal sort once it has a cycle
            # detection option
            res = toposort.toposort(dep_graph)

            for v in res:
                # Ignore result for now we just want to catch cycles
                pass

        except ValueError as e:
            # TODO: translate this exception better
            raise Exception(str(e))


    def _install_xpd(self, xpd, build_into_env=False, installing=None):
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
                self._mark_installed(info['name'], info)


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
        self._mark_installed(info['name'], info)


    def _install_deps(self, info, build=False):
        """
        Makes sure all the dependencies for the given package are properly
        installed.

        The object should have a property 'dependencies' which is a list of the
        following form: ['package', 'package==1.2.2']

        TODO: handle proper version checks someday
        """

        # Get the full dep list based on whether we need the build dependencies
        deps = self._resolve_deps(info.dependencies)

        if build:
            # Resolve all the build dependencies
            build_deps = self._resolve_deps(info.build_dependencies)

            deps += build_deps

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
            # Path is an xpd file, load it
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


    def _resolve_deps(self, build_deps):
        """
        Uses the current toolset to resolve build dependencies.  Any build
        dependency started with "tl:" is resolved using the current toolset.
        """

        # Use the toolset to resolve all of our deps
        final_deps = []

        for dep in build_deps:
            if dep.startswith('tl:'):
                # Use the toolset to translate the dep
                new_dep = self.toolset.lookup_build_dep(dep[3:])
            else:
                # Not a toolset dep just include it directly
                new_dep = dep

            # Only include if we have a valid dep
            if len(new_dep):
                final_deps.append(new_dep)

        return final_deps


    def _mark_installed(self, name, info):
        """
        Marks the package installed and updates the so link as needed.
        """

        self._pdb.mark_installed(info['name'], info)

        #linux.update_ld_so_symlink(self._env_dir)


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
        info = self._pdb.get_info(name, with_files=True)

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

            # Update the ld.so as needed
            #linux.update_ld_so_symlink(self._env_dir)
        else:
            print 'Package %s not installed.' % name


    def info(self, input_val, with_files=False):
        """
        Returns information about either the given package, or the package the
        file belongs too.

        @return None if no lookup was successful
        """

        info = self._pdb.get_info(input_val, with_files=with_files)

        if not info:
            # It's not a package so lets try doing a file lookup instead
            full_path = os.path.abspath(input_val)

            if full_path.startswith(self.root):
                relative_path = full_path[len(self.root) + 1:]
                return self._pdb.get_info_for_path(relative_path)

        return info


    def jump(self, program='bash', args=[], isolate=False, gui=False):
        """
        Jump into the desired environment.  When we isolate all variables will
        be set instead of pre-pended.
        """

        if args is None:
            args = []

        # Setup the environment variables
        self.apply_env_variables(isolate=isolate, gui=gui)

        # Setup up the PS1 (this doesn't work)
        os.environ['PS1'] = '(xpkg:%s) \u@\h:\w\$' % self.name

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

        # Get our list of library directories
        lib_bases = ['lib']

        if util.is_64bit():
            lib_bases.extend([
                'lib64',
                'lib/x86_64-linux-gnu',
                ])
        else:
            lib_bases.extend([
                'lib/i386-linux-gnu',
            ])

        lib_dirs = [os.path.join(self._env_dir, l) for l in lib_bases]

        # For our LDFLAGS and LD_LIBRARY_PATH variables
        ldflags = ' '.join(['-L%s' % l for l in lib_dirs])
        ld_library_path = os.pathsep.join(lib_dirs)

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
            'LD_LIBRARY_PATH' : (ld_library_path, os.pathsep),
            'CFLAGS' : (cflags, ' '),
            'CCFLAGS' : (cflags, ' '),
            'CPPFLAGS' : (cflags, ' '),
            'LDFLAGS' : (ldflags, ' '),
           }

        return env_paths


    def get_toolset_env_info(self):
        #subs = {'LD_SO_PATH' : paths.ld_linux_path(self._env_dir)}
        subs = {}
        return self.toolset.get_env_var_info(subs)


    def apply_env_variables(self, isolate=False, gui=False):
        """
        Change the current environment variables so that we can use the things
        are in that environment.

          isolate - over write local environment variables, try to limit the
                    effect of other things installed on the system.
          gui - Allow GUI programs (like X11) the environment variables they
                need to work.
        """

        env_paths = self.get_env_variables()

        # Place the paths into our environment
        for varname, pathinfo in env_paths.iteritems():
            varpath, sep = pathinfo

            cur_var = os.environ.get(varname, None)

            if cur_var and not isolate:
                os.environ[varname] = varpath + sep + cur_var
            else:
                os.environ[varname] = varpath

        # Hack for linux, keep around DISPLAY so when running isolated mode X11
        # apps can still talk to the local xserver
        if gui and 'DISPLAY' in os.environ:
            env_paths['DISPLAY'] = os.environ['DISPLAY']

        # Remove not being set environment environment variables when we are
        # isolating the environment
        if isolate:
            for varname in os.environ.keys():
                if varname not in env_paths:
                    del os.environ[varname]

        # Setup the Xpkg path
        os.environ[envvars.xpkg_root_var] = self._env_dir

        # Apply toolset environment variables
        # TODO: only use this sub on linux
        #subs = {'LD_SO_PATH' : paths.ld_linux_path(self._env_dir)}
        self.toolset.apply_env_vars({})


    def _parse_install_input(self, value):
        """
        Basic support for version based installs.  Right now it just parses
           mypackage==1.0.0 -> ('mypackage', '1.0.0')
           mypackage -> ('mypackage', None)
        """

        return parse_dependency(value)


    @staticmethod
    def env_exists(env_dir):
        """
        Returns true if the environment has been setup.
        """
        return os.path.exists(Environment.env_settings_path(env_dir))


    @staticmethod
    def env_settings_path(env_dir):
        """
        Full path to the settings dir.
        """
        return os.path.join(env_dir, Environment.SETTINGS_PATH)


    @staticmethod
    def xpa_cache_dir(root):
        """
        The directory we hold current built packages.
        """
        return os.path.join(root, 'var', 'xpkg', 'cache')


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

        @TODO Break up this mega function
        """

        # Grab the offset info and filer out the pyc strings
        raw_offset_info = self.info['install_path_offsets']

        offset_info, pyc_files = remove_special_offset_files(raw_offset_info)

        # Fix up all the pyc files
        recompile_pyc_files(pyc_files, dest_path)

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

                # Make sure we have write access to the file so we can change
                # its contents. Some packages have write protected files with
                # paths we need to change.
                fperms = os.stat(full_path).st_mode
                perms_changed = True

                if 0 == (fperms & stat.S_IWUSR):
                    perms_changed = True
                    os.chmod(full_path, fperms | stat.S_IWUSR)

                # Read in the file contents and update the variables
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

                # Change perms back if needed
                if perms_changed:
                    os.chmod(full_path, fperms)

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


def recompile_pyc_files(files, dest_path):
    """
    Recompiles all the given python files using the local python.
    """

    # TODO: maybe do multiple of these at once to save on interp startup
    # time
    for pyc_file in files:
        path, _ = os.path.splitext(pyc_file)
        full_path = os.path.join(dest_path, path + '.py')
        subprocess.call(['python', '-m', 'py_compile', full_path])


def remove_special_offset_files(offset_info):
    """
    Some types of files, like compiled python files (.pyc) need special
    handling to deal with their embedded paths.  This removes them from
    the list so they can be handled separately.
    """

    # The keys which contains files to filer
    file_keys = set(['text_files', 'binary_files', 'sub_binary_files'])

    # Copy all non-file info into the new offset
    non_file_keys = set(offset_info.keys()) - file_keys
    new_offset_info = dict([(k, offset_info[k]) for k in non_file_keys])

    for f in file_keys:
        new_offset_info[f] = {}

    # Filter in the file keys
    special_ext = set(['.pyc'])
    special_files = []

    for key in file_keys:
        for file_path, value in offset_info[key].iteritems():
            _, ext = os.path.splitext(file_path)

            if ext in special_ext:
                special_files.append(file_path)
            else:
                new_offset_info[key][file_path] = value

    return new_offset_info, special_files


class XPD(object):
    """
    A Xpkg description file, it explains how to build one or more packages.
    """

    def __init__(self, path, data=None):
        """
        Load and parse the given XPD
        """

        # Save path
        self.path = path

        # Load our data
        if data is None:
            self._data = util.load_xpd(path)
        else:
            self._data = data

        def get_field(name, default):
            f = self._data.get(name, default)

            if f is None:
                f = default

            return f

        # Read fields and define properties
        self.name = self._data['name']
        self.version = self._data['version']
        self.dependencies = get_field('dependencies', [])
        self.build_dependencies = get_field('build-dependencies', [])
        self.description = get_field('description', '')


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
        xpd = XPD(xpd_path, data=data)

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
        self._dirty = False

        # Determine the path to our cache
        cache_root = paths.local_cache_dir()

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

            # Mark our selves dirty so we know that we have to save the data
            self._dirty = True
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

        if self._dirty:
            cache_dir, _ = os.path.split(self._cache_path)

            util.ensure_dir(cache_dir)

            with open(self._cache_path, 'w') as f:
                json.dump(self._cache, f)


class PackageDatabase(object):
    """
    Stores information about packages, right now just does version and name
    look ups.  Will eventually support more advanced queries.

    This is used to query the repo and tree for what packages they contain.
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
