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
        cls.repo_dir = tempfile.mkdtemp(suffix = '-testing-xpm-repo')

        build_tree.create_test_repo(cls.repo_dir)

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


    def tearDown(self):
        # Remove temp dir
        if os.path.exists(self.work_dir):
           shutil.rmtree(self.work_dir)


    def _xpm_cmd(self, env_dir, args):
        """
        Run XPM command and return the output.
        """

        cmd = [os.path.join(root_dir, 'xpm')] + args + [env_dir]

        return util.shellcmd(cmd, shell=False, stream=False)


    def test_no_env(self):

        env_dir = os.path.join(self.work_dir, 'env')

        output = self._xpm_cmd(env_dir, ['list'])

        self.assertRegexpMatches(output, 'No XPM package DB found in root.*')


    def test_everything(self):
        # Get the paths to the env and the other versions
        env_dir = os.path.join(self.work_dir, 'env')
        package_xpd = os.path.join(self.repo_dir, 'tree', 'hello.xpd')

        # Run the install
        self._xpm_cmd(env_dir, ['install', package_xpd])

        # Run our program to make sure it works
        hello_bin = os.path.join(env_dir, 'bin', 'hello')

        output = util.shellcmd(hello_bin, echo=False)

        self.assertEqual('Hello, world!\n', output)

        # Make sure the package is marked installed
        output = self._xpm_cmd(env_dir, ['info', 'hello'])

        self.assertEqual('Package hello at version 1.0.0\n', output)

        # Get the package list
        output = self._xpm_cmd(env_dir, ['list'])

        self.assertEqual('  hello - 1.0.0\n', output)

        # Un-install the package
        self._xpm_cmd(env_dir, ['remove', 'hello'])

        self.assertFalse(os.path.exists(hello_bin))


if __name__ == '__main__':
    unittest.main()
