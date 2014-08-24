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
from xpkg import linux
from xpkg import util
from tests import build_tree

class TestBase(unittest.TestCase):

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
        """
        Creates repo and environment directory.
        """

        # Create temp dir
        self.work_dir = tempfile.mkdtemp(suffix = '-testing-xpkg')
        print self.work_dir

        # Create the user cache dir
        self.user_cache_dir = os.path.join(self.work_dir, 'user_cache')

        # Mock the user dir
        os.environ[core.xpkg_local_cache_var] = self.user_cache_dir

        # Create the env_dir
        self.env_dir = os.path.join(self.work_dir, 'env')

        # Create our binary package repository dir
        self.repo_dir = os.path.join(self.work_dir, 'repo')
        util.ensure_dir(self.repo_dir)

        # Save the environment
        self._envStorage = util.EnvStorage(store = True)


    def tearDown(self):
        """
        Cleans up the created files, and resets the environment.
        """

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


    def assertLPathExists(self, path):
        """
        Checks if the link exists, but doesn't care if the file it points to
        actually exists.
        """
        if not os.path.lexists(path):
            self.fail('Symlink: "%s" does not exist' % path)


    def _xpkg_cmd(self, args, env_dir=None, use_var=True, should_fail=False):
        """
        Run Xpkg command and return the output.

          should_fail - if true, don't error out if the command returns != 0

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

        # Have the tool return the full stack trace in debug mode
        if not should_fail:
            args.insert(0, '--debug')

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


    def _make_empty_env(self):
        """
        Creates an empty environment so we know that this is really an
        environment.
        """

        # Create our environment in the proper directory, with the name 'test'
        self._xpkg_cmd(['init', self.env_dir, 'test'])



class FullTests(TestBase):

    def setUp(self):
        # Normal setup
        TestBase.setUp(self)

        # Saves this to maek the rest of the tests shorter
        self.hello_bin = os.path.join(self.env_dir, 'bin', 'hello')


    def test_init(self):
        """
        Lets just make what we expected to be here is here.
        """

        # Set things up
        self._make_empty_env()

        # TODO: make this linux specific
        settings_dir = os.path.join(self.env_dir, 'var', 'xpkg')
        self.assertPathExists(settings_dir)


    @unittest.skip("ld-linux feature not supported")
    def test_ld_linux_init(self):
        """
        Make sure the ld path is setup properly linux.
        """

        self._make_empty_env()

        ld_so_path = os.path.join(self.env_dir, 'lib', 'ld-linux-xpkg.so')
        self.assertLPathExists(ld_so_path)
        self.assertPathExists(ld_so_path)


    def test_no_env(self):
        """
        Make sure we get an error when there is no environment.
        """

        env_dir = os.path.join(self.work_dir, 'env')

        output = self._xpkg_cmd(['list'], should_fail = True)

        self.assertRegexpMatches(output, 'No Xpkg environment found in.*')


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

        expected = {
            'name' : 'hello',
            'version' : '1.0.0',
            'description' : 'Says hello'
        }
        self.assertEqual(expected, data)

        # Full output
        output = self._xpkg_cmd(['info', 'hello', '--verbose'], use_var=False)

        data = yaml.load(output)

        expected['files'] = ['bin/hello']
        expected['dirs'] = ['bin']
        self.assertEqual(expected, data)

        # Non-existent output
        output = self._xpkg_cmd(['info', 'nothere'], use_var=False)

        self.assertEquals('Package nothere not installed.\n', output)

        # Test getting file input
        output = self._xpkg_cmd(['info', 'bin/hello'], use_var=False)
        self.assertEqual(expected, data)


    def test_environment_info(self):
        """
        Make sure we can get the basic information about our environment.
        """

        self._make_empty_env()

        # Set up our environment variables
        os.environ[core.xpkg_tree_var] = self.tree_dir
        os.environ[core.xpkg_repo_var] = self.repo_dir

        # Our expected results
        expected = {
            'name' : 'test',
            'toolset' : 'local',
            'root' : self.env_dir,
            'trees' : [self.tree_dir],
            'repos' : [self.repo_dir],
        }

        # Run output and compare the results
        output = self._xpkg_cmd(['info', '--verbose'])

        data = yaml.load(output)

        # Remove the env sections
        env_section = data.pop('env')
        toolset_env_section = data.pop('toolset-env')

        self.assertEqual(expected, data)

        # Now do a basic check on the env data
        self.assertIn('PATH', env_section)


    def test_info_root_args(self):
        """
        Make sure we can pass the root with the command line flag.
        """

        self._xpkg_cmd(['install', self.hello_xpd])

        # Make sure the info command returns the right data
        output = self._xpkg_cmd(['info', 'hello'], )

        data = yaml.load(output)
        expected = {
            'name' : 'hello',
            'version' : '1.0.0',
            'description' : 'Says hello'
        }
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

        # Make the directory contain that package is empty
        hello_dir, _ = os.path.split(self.hello_bin)
        self.assertNoPathExists(hello_dir)


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


    def test_remove_with_deps(self):

        # Make sure we can access the package tree for building
        os.environ[core.xpkg_tree_var] = self.tree_dir

        # Install greet
        self._xpkg_cmd(['install', 'greeter'])

        # Test that greeter works
        greeter_bin = os.path.join(self.env_dir, 'bin', 'greeter')
        def greet_test():
            output = self._xpkg_cmd(['jump', '-c', 'greeter'])
            self.assertEqual('Welcome to a better world!\n', output)

        greet_test()

        # Try and remove libgreet
        self._xpkg_cmd(['remove', 'libgreet'], should_fail=True)

        # Make sure that didn't work and we can still greet
        greet_test()


    def test_jump(self):
        # Setup environment
        self._make_empty_env()

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

        expected = {
            'name' : 'hello',
            'version' : '1.0.0',
            'description' : 'Says hello'
        }
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


    def test_install_most_recent(self):
        """
        Make sure that when install a package with multiple versions the newest
        version is installed.
        """

        # Make sure we can access the package tree for building
        os.environ[core.xpkg_tree_var] = self.tree_dir

        # Install libgreet and make sure we have the most recent version
        self._xpkg_cmd(['install', 'libgreet'])

        output = self._xpkg_cmd(['list'])

        self.assertRegexpMatches(output, '.*libgreet - 2.0.0.*')


    def test_build_with_deps(self):
        """
        Make sure that when we build an XPD package it's dependencies are
        installed first.
        """

        # Setup environment
        self._make_empty_env()

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
        self._make_empty_env()

        # Make sure we can access the package tree for building
        os.environ[core.xpkg_tree_var] = self.tree_dir

        # Build the package
        xpd_path = os.path.join(self.tree_dir, 'greeter.xpd')
        self._xpkg_cmd(['build', xpd_path, '--dest', self.repo_dir])

        # Purge the environment and re-setup
        shutil.rmtree(self.env_dir)
        self._make_empty_env()

        # Get the path to the generated package
        pkg_path = os.path.join(self.repo_dir, os.listdir(self.repo_dir)[0])

        # Install the binary
        self._xpkg_cmd(['install', pkg_path])

        # Make sure that we can run the program (and the deps are there)
        output = self._xpkg_cmd(['jump', '-c', 'greeter'])
        self.assertEqual('Hello!\n', output)


    def test_install_build_deps(self):
        """
        Make sure that when we install the hello world package from an
        XPA we only get the hello package and not the fake tools package.
        """

        # Build the hello package
        self._make_empty_env()
        os.environ[core.xpkg_tree_var] = self.tree_dir

        self._xpkg_cmd(['build',
                        os.path.join(self.tree_dir, 'libgreet2.xpd'),
                        '--dest', self.repo_dir])

        # Check the package
        new_files = os.listdir(self.repo_dir)
        pkg_path = os.path.join(self.repo_dir, new_files[0])

        output = self._xpkg_cmd(['info',pkg_path])
        info = yaml.load(output)

        self.assertNotIn('dependencies', info)

        # Clean up the environment
        shutil.rmtree(self.env_dir)
        self._make_empty_env()

        # Install the hello package from the XPA
        os.environ[core.xpkg_repo_var] = self.repo_dir

        self._xpkg_cmd(['install', 'libgreet'])

        # Make sure it's the only package install
        output = self._xpkg_cmd(['list'])

        self.assertEqual('  libgreet - 2.0.0\n', output)


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
        self._make_empty_env()

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


    def test_multipkg_xpd_install(self):
        """
        Make sure that install the a of multiple package XPD installs all parts.
        """

        # Make sure we can access the package tree for building
        os.environ[core.xpkg_tree_var] = self.tree_dir

        # Run the install
        self._xpkg_cmd(['install', os.path.join(self.tree_dir, 'multipkg.xpd')])

        # Run our program to make sure it works
        #output = util.shellcmd(self.hello_bin, echo=False)

        # Make sure our programs exist
        bin_dir = os.path.join(self.env_dir, 'bin')
        self.assertPathExists(os.path.join(bin_dir, 'toola'))
        self.assertPathExists(os.path.join(bin_dir, 'toolb'))

        # Run the list command and parse it to get our list of installed
        # packages (maybe we should just read the DB directly?)
        output = self._xpkg_cmd(['list'], )

        install_info = [l.strip().split(' - ')
                        for l in output.split('\n')
                        if len(l.strip()) > 0]

        # Check the contents of the install info
        self.assertIn(['multi-tools', '1.5.0'], install_info)
        self.assertIn(['libmulti', '1.0.0'], install_info)
        self.assertIn(['libmulti-dev', '1.0.0'], install_info)
        self.assertEqual(4, len(install_info))

        # TODO:
        #  - purge environment
        #  - just install libmulti
        #  - make sure it's the only thing installed


    def test_multi_tree(self):
        """
        Test that we can properly work with multiple package trees.
        """

        # Paths to our two trees
        primary_tree = os.path.join(self.work_dir, 'primary-tree')
        secondary_tree = os.path.join(self.work_dir, 'secondary-tree')

        # Copy the contents of our main tree primary local tree
        shutil.copytree(self.tree_dir, primary_tree)

        # Move libgreet-2 and hello packages to the secondary tree
        util.ensure_dir(secondary_tree)

        for move_file in ['libgreet2.xpd', 'hello.xpd']:
            shutil.move(os.path.join(primary_tree, move_file),
                        secondary_tree)

        # Set the tree environment variable to include both the primary and
        # the secondary tree
        os.environ[core.xpkg_tree_var] = '%s:%s' % (primary_tree, secondary_tree)

        # Make sure we can install hello package
        self._xpkg_cmd(['install', 'hello'])

        self.assertPathExists(self.hello_bin)

        # Install greeter2, and make sure we have libgreet installed
        self._xpkg_cmd(['install', 'greeter==2.0.0'])

        output = self._xpkg_cmd(['list'])

        self.assertRegexpMatches(output, '.*libgreet - 2.0.0.*')


    def test_patching(self):
        # Setup the env for install (make sure we have access to the tree)
        os.environ[core.xpkg_tree_var] = self.tree_dir

        # Install the program
        self._xpkg_cmd(['install', '--verbose', 'patchme'])

        # Check the message that was printed out
        output = self._xpkg_cmd(['jump', '-c', 'patchme'])

        self.assertEqual('I\'m patched!\n', output)


    def test_commands(self):
        """
        Tests our custom command system
        """

        os.environ[core.xpkg_tree_var] = self.tree_dir

        # Install the program
        self._xpkg_cmd(['install', '--verbose', 'commands'])

        # Check the message that was printed out
        output = self._xpkg_cmd(['jump', '-c', 'fun'])

        self.assertEqual('I\'m fun\n', output)

        # Now run the command and make sure our internal path changed
        output = self._xpkg_cmd(['jump', '-c', 'fun -h'])

        self.assertEqual('Path: /fixed/path\n', output)


    def test_env_commands(self):
        """
        Make sure we can set environment variables for each command that
        builds are package.
        """

        os.environ[core.xpkg_tree_var] = self.tree_dir

        # Install the program
        self._xpkg_cmd(['install', '--verbose', 'env-command'])

        # Check the message that was printed out
        output = self._xpkg_cmd(['jump', '-c', 'env_command'])

        self.assertEqual('Hi\n', output)


    # TODO: test build dependencies
    #  - build package with build-deps
    #  - make sure normal and build depth is installed
    #  - purge-environment
    #  - install package, make sure only normal dep is installed


    def test_create(self):
        # Get the basics from our directory
        p = os.path.join(root_dir, 'tests', 'create', 'autotool')
        xpd_path = os.path.join(p, 'result.xpd')
        expected = yaml.load(open(xpd_path))
        expected_path = os.path.join(self.work_dir, 'autotool.xpd')

        # Create our tar file
        tar_name = '%s-%s.tar.gz' % (expected['name'], expected['version'])

        tar_path = os.path.join(self.work_dir, tar_name)

        util.make_tarball(tar_path, p)

        # Update the expected with the correct hash and file path
        hash_str = util.hash_file(open(tar_path), hashlib.md5)
        expected['files'] = {'md5-' + hash_str : {'url' : tar_path}}

        # Run our command with that tar file
        abs_tar = os.path.abspath(tar_path)

        with util.save_env():
            os.environ['PYTHONPATH'] = os.getcwd() + ':' + os.environ.get('PYTHONPATH','')
            with util.cd(self.work_dir):
                output = self._xpkg_cmd(['create', abs_tar])

        # Now lets load our file
        self.assertPathExists(expected_path)
        xpd = yaml.load(open(expected_path))

        self.assertEquals(expected, xpd)


class LinuxTests(TestBase):

    @unittest.skip("this feature is current not-enabled")
    def test_local_elf_interp(self):
        """
        Makes sure we have a custom elf interp that links to the system one.
        """

        # Run the install
        self._xpkg_cmd(['install', 'basic', '--tree', self.tree_dir])

        # Make sure the program exists
        basic_bin = os.path.join(self.env_dir, 'bin', 'basic')
        self.assertPathExists(basic_bin)

        # Run our program to make sure it works
        output = util.shellcmd([basic_bin], shell=False, stream=False)

        self.assertEqual('Hello, world!\n', output)

        # Now make sure it has the proper elf interp
        expected = os.path.join(self.env_dir, 'lib', 'ld-linux-xpkg.so')
        interp_path = linux.readelf_interp(basic_bin)
        self.assertEquals(expected, interp_path)

    @unittest.skip("this feature is current not-enabled")
    def test_local_elf_interp_install(self):
        """
        Makes sure that we link to the installed interp if there is one.
        """

        # This is a slight hack, but lets pre-create seed the environment with
        # our symlink ld.so so that it is the link target
        interp_path = linux.readelf_interp(sys.executable)
        lib_dir = os.path.join(self.env_dir, 'lib')
        target_path = os.path.join(lib_dir, 'ld-2.99.so')

        util.ensure_dir(lib_dir)
        os.symlink(interp_path, target_path)

        # Create out environment
        self._make_empty_env()

        # Run the install
        self._xpkg_cmd(['install', 'basic', '--tree', self.tree_dir])

        # Make sure it has the proper elf interp
        basic_bin = os.path.join(self.env_dir, 'bin', 'basic')
        interp_path = linux.readelf_interp(basic_bin)

        expected = os.path.join(self.env_dir, 'lib', 'ld-linux-xpkg.so')

        self.assertEquals(expected, interp_path)

        # Make sure it points to our special one
        linked_path = os.readlink(interp_path)
        self.assertEquals(target_path, linked_path)


class ToolsetTests(TestBase):
    """
    Tests that require toolset packages to be built first.
    @TODO: FIX THIS TEST THE MAKEFILE DOESN"T USE TCC AT ALL
    """

    @classmethod
    def setUpClass(cls):
        """
        Sets up a little test Xpkg environment and builds the test toolset
        packages.
        """

        # Get all the basics setup
        TestBase.setUpClass()

        # Create a toolset repo directory
        cls.toolset_repo_dir = os.path.join(cls.storage_dir, 'toolset-repo')

        util.ensure_dir(cls.toolset_repo_dir)

        # Build our packages into it
        root_tree = os.path.join(root_dir, 'pkgs')

        for pkg_name in ['busybox', 'tcc', 'uclibc']:
            xpd_path = os.path.join(root_tree, pkg_name + '.xpd')

            args = ['build', xpd_path, '--dest', cls.toolset_repo_dir]

            cmd = [sys.executable, '-m', 'xpkg.main'] + args

            # Run build inside toolset dir so that the build logs don't pollute
            # Anything
            cwd = os.getcwd()
            with util.cd(cls.toolset_repo_dir):
                with util.save_env():
                    os.environ['PYTHONPATH'] = cwd

                    output = util.shellcmd(cmd, shell=False, stream=False)

    def test_basic(self):
        """
        Makes sure our basic toolset package works.
        """

        # Setup the environment to use our testing toolset
        self._xpkg_cmd(['init', self.env_dir, 'test-env', '--toolset', 'Test'])

        # Make sure we can locate of packages
        os.environ[core.xpkg_tree_var] = self.tree_dir
        os.environ[core.xpkg_repo_var] = self.toolset_repo_dir

        # Install the program
        self._xpkg_cmd(['install', '--verbose', 'toolset-basic'])

        # Can we run our program
        basic_bin = os.path.join(self.env_dir, 'bin', 'basic')

        output = util.shellcmd([basic_bin], shell=False, stream=False)

        self.assertEqual('Hello, world!\n', output)


if __name__ == '__main__':
    unittest.main()
