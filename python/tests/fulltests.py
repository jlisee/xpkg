# Author: Joseph Lisee <jlisee@gmail.com>

__doc__ = """
These are tests using the public interface and files of Xpkg itself, not the
internal python implementation.  This idea is that we can use these tests when
porting over to a future version.
"""

# Python Imports
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

# Library Imports
import yaml


cur_dir, _ = os.path.split(__file__)
root_dir = os.path.abspath(os.path.join(cur_dir, '..', '..'))

# Project imports
from xpkg import core
from xpkg import util
from tests import build_tree


class FullTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Sets up a little test Xpkg environment
        """

        # Create test repository
        cls.storage_dir = tempfile.mkdtemp(suffix = '-testing-xpkg-repo')

        build_tree.create_test_repo(cls.storage_dir)

        # Provide path to the package description tree
        cls.tree_dir = os.path.join(cls.storage_dir, 'tree')

        # Provide a path to the xpd
        cls.hello_xpd = os.path.join(cls.tree_dir, 'hello.xpd')


    @classmethod
    def tearDownClass(cls):
        """
        Destroys our test xpkg environment
        """
        if os.path.exists(cls.storage_dir):
            shutil.rmtree(cls.storage_dir)


    def setUp(self):
        # Create temp dir
        self.work_dir = tempfile.mkdtemp(suffix = '-testing-xpkg')
        print self.work_dir

        # Create the env_dir
        self.env_dir = os.path.join(self.work_dir, 'env')

        self.hello_bin = os.path.join(self.env_dir, 'bin', 'hello')

        # Create our binary package repository dir
        self.repo_dir = os.path.join(self.work_dir, 'repo')
        util.ensure_dir(self.repo_dir)

        # Save the environment
        self._envStorage = util.EnvStorage(store = True)


    def tearDown(self):
        # Remove temp dir
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)

        # Restore new variables
        self._envStorage.restore()


    def assertPathExists(self, path):
        """
        Checks if the desired path exists
        """
        if not os.path.exists(path):
            self.fail('Path: "%s" does not exist' % path)


    def assertNoPathExists(self, path):
        """
        Checks to make sure the desired path does *not* exist
        """
        if os.path.exists(path):
            self.fail('Path: "%s" exists' % path)


    def _xpkg_cmd(self, args, env_dir=None, use_var=True, should_fail=False):
        """
        Run Xpkg command and return the output.

        This sets the XPKG_ROOT environment var commands are executed with
        respected to self.env_dir directory.
        """

        # Setup arguments
        if env_dir is None:
            env_dir = self.env_dir

        if use_var:
            env_args = []
            os.environ[core.xpkg_root_var] = env_dir
        else:
            # Clear variable
            if core.xpkg_root_var in os.environ:
                del os.environ[core.xpkg_root_var]

            # Set out args
            env_args = ['--root',env_dir]

        # Run the command directly calling the python xpkg implementation
        cmd = [sys.executable, '-m', 'xpkg.main'] + args + env_args

        try:
            output = util.shellcmd(cmd, shell=False, stream=False)

            # If we got here but we should of failed error out
            if should_fail:
                args = ' '.join(cmd)
                msg = 'Command "%s" did not return a non-zero exit code' % args
                self.fail(msg)

        except subprocess.CalledProcessError as c:
            # Capture this error, and only re throw if we were not excepting
            # an exception
            output = c.output

            if not should_fail:
                raise c

        return output

    def _make_empty_db(self):
        """
        Creates an empty environment so we know that this is really an
        environment.
        """

        # Create and empty db files
        db_dir = core.InstallDatabase.db_dir(self.env_dir)
        util.ensure_dir(db_dir)

        db_path = os.path.join(db_dir, 'db.yml')
        util.touch(db_path)


    def test_no_env(self):
        """
        Make sure we get an error when there is no environment.
        """

        env_dir = os.path.join(self.work_dir, 'env')

        output = self._xpkg_cmd(['list'], should_fail = True)

        self.assertRegexpMatches(output, 'No Xpkg package DB found in root.*')


    def test_install(self):
        """
        Make sure the desired program was installed and works.
        """

        # Run the install
        self._xpkg_cmd(['install', self.hello_xpd])

        # Run our program to make sure it works
        output = util.shellcmd(self.hello_bin, echo=False)

        self.assertEqual('Hello, world!\n', output)


    def test_install_twice(self):
        """
        Make sure the desired program was installed and works.
        """

        # Run the install
        self._xpkg_cmd(['install', self.hello_xpd])

        # Get the modification time
        mtime = os.path.getmtime(self.hello_bin)

        # A second install attempt should fail
        self._xpkg_cmd(['install', self.hello_xpd], should_fail=True)

        # Make sure the modification time hasn't changed
        new_mtime = os.path.getmtime(self.hello_bin)

        self.assertEqual(mtime, new_mtime)


    def test_install_with_tree_flag(self):
        """
        Make sure we can install with the package tree.
        """

        # Run the install
        self._xpkg_cmd(['install', 'hello', '--tree', self.tree_dir])

        # Run our program to make sure it works
        self.assertPathExists(self.hello_bin)


    def test_install_with_tree_var(self):
        """
        Make sure we can install with the package tree.
        """

        # Set our environment variable
        os.environ[core.xpkg_tree_var] = self.tree_dir

        # Run the install
        self._xpkg_cmd(['install', 'hello'])

        # Run our program to make sure it works
        self.assertPathExists(self.hello_bin)


    def test_install_with_tree_repo(self):
        """
        Make sure we can install with the package tree.
        """

        # Build our package and place it into our repo directory
        self._xpkg_cmd(['build', self.hello_xpd, '--dest', self.repo_dir])

        # Run the install, referencing our adhoc package repository
        os.environ[core.xpkg_repo_var] = self.repo_dir

        self._xpkg_cmd(['install', 'hello'])

        # Run our program to make sure it works
        self.assertPathExists(self.hello_bin)


    def test_info(self):
        """
        Makes sure we can get the proper information back about an installed
        package.
        """

        self._xpkg_cmd(['install', self.hello_xpd])

        # Normal output
        output = self._xpkg_cmd(['info', 'hello'], use_var=False)

        data = yaml.load(output)

        expected = {'name' : 'hello', 'version' : '1.0.0'}
        self.assertEqual(expected, data)

        # Full output
        output = self._xpkg_cmd(['info', 'hello', '--verbose'], use_var=False)

        data = yaml.load(output)

        expected['files'] = ['bin', 'bin/hello']
        self.assertEqual(expected, data)


    def test_info_root_args(self):
        """
        Make sure we can pass the root with the command line flag.
        """

        self._xpkg_cmd(['install', self.hello_xpd])

        # Make sure the info command returns the right data
        output = self._xpkg_cmd(['info', 'hello'], )

        data = yaml.load(output)
        expected = {'name' : 'hello', 'version' : '1.0.0'}
        self.assertEqual(expected, data)


    def test_remove(self):

        # Install the package
        self._xpkg_cmd(['install', self.hello_xpd])

        # Get the package list
        output = self._xpkg_cmd(['list'])

        self.assertEqual('  hello - 1.0.0\n', output)

        # Un-install the package
        self._xpkg_cmd(['remove', 'hello'])

        self.assertNoPathExists(self.hello_bin)


    def test_symlink_remove(self):
        """
        Make sure removal with symlink works properly.
        """

        # Make this visible so we can pull in fake tools
        os.environ[core.xpkg_tree_var] = self.tree_dir

        # Install the package
        self._xpkg_cmd(['install', os.path.join(self.tree_dir, 'libgreet.xpd')])

        # Make sure the file is there
        libpath = os.path.join(self.env_dir, 'lib', 'libgreet.so')
        self.assertPathExists(libpath)
        self.assertPathExists(libpath + '.1')

        # Remove the package
        self._xpkg_cmd(['remove', 'libgreet'])

        # Make sure everything is done
        self.assertNoPathExists(libpath + '.1')
        self.assertFalse(os.path.lexists(libpath))


    def test_jump(self):
        # Setup environment
        self._make_empty_db()

        # Test ENV_ROOT
        def get_var(varname):
            py_command = 'python -c "import os; print os.environ[\'%s\']"' % varname

            return self._xpkg_cmd(['jump', '-c', py_command]).strip()

        self.assertEquals(self.env_dir, get_var(core.xpkg_root_var))

        # Make sure PATH is set
        path = get_var('PATH')
        paths = path.split(os.pathsep)

        bin_dir = os.path.join(self.env_dir, 'bin')

        self.assertEqual(1, paths.count(bin_dir))
        self.assertTrue(path.startswith(bin_dir))

        # Make sure LD_LIBRARY_PATH is set
        path = get_var('LD_LIBRARY_PATH')
        paths = path.split(os.pathsep)

        lib_dir = os.path.join(self.env_dir, 'lib')

        self.assertEqual(1, paths.count(lib_dir))
        self.assertTrue(path.startswith(lib_dir))


    def test_build(self):
        # Build our package
        self._xpkg_cmd(['build', self.hello_xpd, '--dest', self.repo_dir])

        # Get the path to the created package
        new_files = os.listdir(self.repo_dir)

        self.assertEqual(1, len(new_files))

        pkg_path = os.path.join(self.repo_dir, new_files[0])

        # Install the package
        self._xpkg_cmd(['install', pkg_path])

        # Make sure the package is in the info
        output = self._xpkg_cmd(['info', 'hello'], )

        data = yaml.load(output)

        expected = {'name' : 'hello', 'version' : '1.0.0'}
        self.assertEqual(expected, data)

        # Make sure the actual binary exists
        self.assertPathExists(self.hello_bin)


    def test_dependencies(self):
        # Make sure we can access the package tree for building
        os.environ[core.xpkg_tree_var] = self.tree_dir

        # Install greet
        self._xpkg_cmd(['install', 'greeter'])

        # Make sure the greeter works
        greeter_bin = os.path.join(self.env_dir, 'bin', 'greeter')

        output = self._xpkg_cmd(['jump', '-c', 'greeter'])

        self.assertEqual('Welcome to a better world!\n', output)


    def test_versions(self):
        # Make sure we can access the package tree for building
        os.environ[core.xpkg_tree_var] = self.tree_dir

        # Install greet
        self._xpkg_cmd(['install', 'greeter==1.0.0'])

        # Make sure the greeter works
        greeter_bin = os.path.join(self.env_dir, 'bin', 'greeter')

        output = self._xpkg_cmd(['jump', '-c', 'greeter'])

        self.assertEqual('Hello!\n', output)


    def test_build_with_deps(self):
        """
        Make sure that when we build an XPD package it's dependencies are
        installed first.
        """

        # Setup environment
        self._make_empty_db()

        # Make sure we can access the package tree for building
        os.environ[core.xpkg_tree_var] = self.tree_dir

        # This will force the install faketools
        xpd_path = os.path.join(self.tree_dir, 'libgreet.xpd')
        self._xpkg_cmd(['build', xpd_path, '--dest', self.repo_dir])


    def test_install_xpa_deps(self):
        """
        Make sure that when install a binary package it's dependencies are
        installed first.
        """

        # Setup environment
        self._make_empty_db()

        # Make sure we can access the package tree for building
        os.environ[core.xpkg_tree_var] = self.tree_dir

        # Build the package
        xpd_path = os.path.join(self.tree_dir, 'greeter.xpd')
        self._xpkg_cmd(['build', xpd_path, '--dest', self.repo_dir])

        # Purge the environment and re-setup
        shutil.rmtree(self.env_dir)
        self._make_empty_db()

        # Get the path to the generated package
        pkg_path = os.path.join(self.repo_dir, os.listdir(self.repo_dir)[0])

        # Install the binary
        self._xpkg_cmd(['install', pkg_path])

        # Make sure that we can run the program (and the deps are there)
        output = self._xpkg_cmd(['jump', '-c', 'greeter'])

        self.assertEqual('Hello!\n', output)


    def test_for_path_offsets(self):

        # Make sure we can access the package tree for building
        os.environ[core.xpkg_tree_var] = self.tree_dir

        # Install faketools so we don't depend on dependencies working
        self._xpkg_cmd(['install', 'faketools'])

        # Install the package with offsets
        self._xpkg_cmd(['install', 'libgreet'])

        # Read in the DB
        db_dir = core.InstallDatabase.db_dir(self.env_dir)
        db_path = os.path.join(db_dir, 'db.yml')

        self.assertPathExists(db_path)

        # Make sure our package is in it
        db = yaml.load(open(db_path))

        self.assertIn('libgreet', db)

        # Now lets make sure we have the right info
        info = db['libgreet']
        binary_offsets = info['install_path_offsets']['binary_files']

        self.assertEqual(1, len(binary_offsets))
        self.assertIn('lib/libgreet.so.1', binary_offsets)

        sub_binary_offsets = info['install_path_offsets']['sub_binary_files']
        self.assertEqual(1, len(sub_binary_offsets))
        self.assertIn('lib/libgreet.so.1', sub_binary_offsets)

        # Make sure that one of those sub-strings is multipart
        greet_offsets = sub_binary_offsets['lib/libgreet.so.1']
        min_l = min(map(len, greet_offsets))
        max_l = max(map(len, greet_offsets))

        self.assertEqual(2, min_l)
        self.assertEqual(3, max_l)

    # TODO: test that if a dep is installed it would be-installed
    # TODO: test that install the same package twice will return and error
    # TODO: test for version conflicts for deps

    def test_install_path_changes(self):
        # Setup environment
        self._make_empty_db()

        # Make sure we can access the package tree for building
        os.environ[core.xpkg_tree_var] = self.tree_dir

        # Put a libgreet binary package in the repo, so that's embedded build
        # directory is different and needs to be actively changed.
        xpd_path = os.path.join(self.tree_dir, 'libgreet2.xpd')
        self._xpkg_cmd(['build', xpd_path, '--dest', self.repo_dir])

        # Make sure we have the repo dir setup so pull in our pre-built package
        os.environ[core.xpkg_repo_var] = self.repo_dir

        # Install greet
        self._xpkg_cmd(['install', 'greeter'])

        # Make sure the greeter works
        greeter_bin = os.path.join(self.env_dir, 'bin', 'greeter')

        output = self._xpkg_cmd(['jump', '-c', 'greeter -i'])

        # We expect the path to have the install directory
        expected = 'Hello from (bin): %s\n' % self.env_dir

        self.assertEqual(expected, output)

        # Now try binary substrings
        output = self._xpkg_cmd(['jump', '-c', 'greeter -l'])

        expected = 'Hello from (bin/greet): %s\n' % (self.env_dir + '/greet')

        self.assertEqual(expected, output)

        # Now test that text files substitutions happen
        output = self._xpkg_cmd(['jump', '-c', 'greeter -c'])

        args = (self.env_dir, 'I am in: ' + self.env_dir)
        expected = 'Hello conf (%s/share/libgreet/settings.conf): %s\n' % args

        self.assertEqual(expected, output)

        # Now test with binary strings that in their twice
        output = self._xpkg_cmd(['jump', '-c', 'greeter -d'])

        args = (self.env_dir, self.env_dir)
        expected = 'Str: ./configure --prefix=%s --libdir=%s/lib --fast\n' % args
        self.assertEqual(expected, output)



if __name__ == '__main__':
    unittest.main()
