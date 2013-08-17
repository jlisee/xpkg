# Author: Joseph Lisee <jlisee@gmail.com>

__doc__ = """Really basic full up tests
"""

# Python Imports
import os
import shutil
import sys
import tempfile
import unittest
import hashlib

cur_dir, _ = os.path.split(__file__)
root_dir = os.path.abspath(os.path.join(cur_dir, '..', '..'))

# Project imports
from xpm import util
from tests import build_tree


class FullTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Sets up a little test XPM environment
        """

        # Create test repository
        cls.repo_dir = tempfile.mkdtemp(suffix = '-testing-xpm-repo')

        build_tree.create_test_repo(cls.repo_dir)

        # Provide a path to the xpd
        cls.hello_xpd = os.path.join(cls.repo_dir, 'tree', 'hello.xpd')


    @classmethod
    def tearDownClass(cls):
        """
        Destroys our test xpm environment
        """
        if os.path.exists(cls.repo_dir):
           shutil.rmtree(cls.repo_dir)


    def setUp(self):
        # Create temp dir
        self.work_dir = tempfile.mkdtemp(suffix = '-testing-xpm')
        print self.work_dir

        # Save the env_dir
        self.env_dir = os.path.join(self.work_dir, 'env')


    def tearDown(self):
        # Remove temp dir
        if os.path.exists(self.work_dir):
           shutil.rmtree(self.work_dir)


    def _xpm_cmd(self, args, env_dir=None):
        """
        Run XPM command and return the output.
        """

        if env_dir is None:
            env_dir = self.env_dir

        cmd = [os.path.join(root_dir, 'xpm')] + args + [env_dir]

        return util.shellcmd(cmd, shell=False, stream=False)


    def test_no_env(self):
        """
        Make sure we get an error when there is no environment.
        """

        env_dir = os.path.join(self.work_dir, 'env')

        output = self._xpm_cmd(['list'])

        self.assertRegexpMatches(output, 'No XPM package DB found in root.*')


    def test_install(self):
        """
        Make sure the desired program was installed and works.
        """

        # Run the install
        self._xpm_cmd(['install', self.hello_xpd])

        # Run our program to make sure it works
        hello_bin = os.path.join(self.env_dir, 'bin', 'hello')

        output = util.shellcmd(hello_bin, echo=False)

        self.assertEqual('Hello, world!\n', output)


    def test_info(self):
        """
        Makes sure we can get the proper information back about an installed
        package.
        """
        # Install the package
        self._xpm_cmd(['install', self.hello_xpd])

        # Make sure the info command returns the right data
        output = self._xpm_cmd(['info', 'hello'])

        self.assertEqual('Package hello at version 1.0.0\n', output)


    def test_remove(self):

        # Install the package
        self._xpm_cmd(['install', self.hello_xpd])

        # Get the package list
        output = self._xpm_cmd(['list'])

        self.assertEqual('  hello - 1.0.0\n', output)

        # Un-install the package
        self._xpm_cmd(['remove', 'hello'])

        hello_bin = os.path.join(self.env_dir, 'bin', 'hello')

        self.assertFalse(os.path.exists(hello_bin))


if __name__ == '__main__':
    unittest.main()
