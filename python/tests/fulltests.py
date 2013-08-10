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

# Project imports
from xpm import util

class FullTests(unittest.TestCase):

    def setUp(self):
        # Create temp dir
        self.work_dir = tempfile.mkdtemp(suffix = '-testing-xpm')
        print self.work_dir


    def tearDown(self):
        # Remove temp dir
        if os.path.exists(self.work_dir):
           shutil.rmtree(self.work_dir)

    def test_everything(self):
        # Package directory
        root_dir = os.path.abspath(os.path.join(cur_dir, '..', '..'))

        hello_dir = os.path.join(root_dir, 'tests', 'hello')

        tar_path = os.path.join(self.work_dir, 'hello.tar.gz')

        util.make_tarball(tar_path, hello_dir)

        # Get the hash
        md5sum = util.hash_file(open(tar_path), hashlib.md5)

        # Template the package file
        source_xdp = os.path.join(hello_dir, 'hello.xpd.pyt')

        package_xpd = os.path.join(self.work_dir, 'hello.xpd')

        args = {
            'filehash' : md5sum,
            'filepath' : tar_path,
            # These are not being modified by us
            'prefix' : '%(prefix)s',
            'jobs' : '%(jobs)s',
        }

        util.template_file(source_xdp, package_xpd, args)

        # Create our output directory
        env_dir = os.path.join(self.work_dir, 'env')

        # Run the install
        cmd = [
            os.path.join(root_dir, 'xpm'),
            'install',
            package_xpd,
            env_dir
        ]

        util.shellcmd(cmd, shell=False)

        # Run our program to make sure it works
        hello_bin = os.path.join(env_dir, 'bin', 'hello')

        output = util.shellcmd(hello_bin, echo=False)

        self.assertEqual('Hello, world!\n', output)

if __name__ == '__main__':
    unittest.main()
