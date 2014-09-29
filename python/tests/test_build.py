# Author: Joseph Lisee <jlisee@gmail.com>

__doc__ = """Tests for the core module
"""

# Python Imports
import copy
import os
import shutil
import tempfile
import unittest

# Project Imports
from xpkg import build
from xpkg import util


class UtilTests(unittest.TestCase):

    def setUp(self):
        # The directory we are copying from
        self.base_dir = tempfile.mkdtemp(suffix = '-testing-xpkg-base')
        # The directory we are writing to
        self.target_dir = tempfile.mkdtemp(suffix = '-testing-xpkg-target')

        self._to_remove = [
            self.base_dir,
            self.target_dir
        ]


    def tearDown(self):
        for p_dir in self._to_remove:
            if os.path.exists(p_dir):
                shutil.rmtree(p_dir)


    def _write_to_file(self, path, contents):
        """
        Writes to the given path in the base dir, returns the full path.
        """

        full_path = os.path.join(self.base_dir, path)
        util.write_to_file(full_path, contents)
        return full_path


    def _make_dir(self, path):
        """
        Makes a directory in the target directory.
        """

        full_path = os.path.join(self.base_dir, path)
        os.makedirs(full_path)
        return full_path


    def _make_abs_symlink(self, sym_path, link_location):
        """
        Make a symlink with absolute paths in the base dir, returns the result
        full source path.

        sym_path - symlink path, like '../file/path' (source)
        link_location - real path '/dir/other/link' (link_name)
        """

        link_name = os.path.join(self.base_dir, link_location)
        os.symlink(os.path.join(self.base_dir, sym_path), link_name)
        return link_name


    def _make_rel_symlink(self, sym_path, link_location):
        """
        Make a symlink with absolute the source in the base dir, link_name is
        untouched.
        """

        link_name = os.path.join(self.base_dir, link_location)
        os.symlink(sym_path, link_name)
        return link_name


    def assertTargetFileContents(self, path, contents):
        """
        Checks if the desired target path exists, and contains the needed data.
        """
        full_path = os.path.join(self.target_dir, path)

        if not os.path.exists(full_path):
            self.fail('Path: "%s" does not exist' % full_path)

        actual = open(full_path, 'r').read()

        if contents != actual:
            args = (full_path, actual, contents)
            self.fail('Path: "%s" contains "%s" not "%s"' % args)


    def assertTargetPathExists(self, path):
        """
        Make sure we have the given path in our target dir.
        """
        full_path = os.path.join(self.target_dir, path)

        if not os.path.exists(full_path):
            self.fail('Path: "%s" does not exist' % full_path)


    def assertSymLink(self, path, target):
        """
        Make sure our symlink points where we expect it.
        """
        full_path = os.path.join(self.target_dir, path)

        if not os.path.exists(full_path):
            self.fail('Symlink path: "%s" does not exist' % full_path)

        lpath = os.readlink(full_path)
        if lpath != target:
            self.fail('Expected symlink "%s" != "%s"' % (target, lpath))


    def test_map_files(self):

        # Now lets make some files
        files = [
            # Basic file
            self._write_to_file('bob', 'Test'),
            # Basic directory
            self._make_dir('bin'),
            # File in directory
            self._write_to_file('bin/prog', 'Do thing'),
            # Directory with "usr" (it's trimmed)
            self._make_dir('usr/bin'),
            self._write_to_file('usr/bin/userp', 'I user'),
            # Lib and dir with x86_64-linux-gnu which are removed
            self._make_dir('usr/lib/x86_64-linux-gnu'),
            self._write_to_file('usr/lib/x86_64-linux-gnu/libmine.so', 'Dewey'),
            # Basic lib
            self._make_dir('lib'),
            self._write_to_file('lib/libo.so', '0!'),

            # Sym convention:  (Path of link, fs location of link)

            # Relative symlink (points to file in same dir)
            self._make_rel_symlink('libo.so', 'lib/libo.so.1'),

            # Absolute symlink (points to absolute FS path)
            self._make_abs_symlink('lib/libo.so', 'lib/libo.so.1.2'),

            # Now a relative symlink to a directory
            self._make_rel_symlink('lib', 'other_lib'),
            self._make_abs_symlink('lib', 'a_lib'),
        ]

        # Run the map
        mapping = build.map_files(files, self.target_dir,
                                  base_root=self.base_dir)

        # Remove the base dir so no symlinks can point there
        shutil.rmtree(self.base_dir)

        # Make sure the files exist
        self.assertTargetFileContents('bob', 'Test')
        self.assertTargetPathExists('bin')
        self.assertTargetFileContents('bin/prog', 'Do thing')
        self.assertTargetFileContents('bin/userp', 'I user'),
        self.assertTargetPathExists('lib')
        self.assertTargetFileContents('lib/libmine.so', 'Dewey'),
        self.assertTargetFileContents('lib/libo.so', '0!'),
        self.assertTargetFileContents('lib/libo.so.1', '0!'),
        self.assertTargetFileContents('lib/libo.so.1.2', '0!'),
        self.assertTargetPathExists('other_lib')
        self.assertTargetPathExists('a_lib')

        # Now check the mapping
        expected_mapping = {
            files[0] : 'bob',
            files[2] : 'bin/prog',
            files[4] : 'bin/userp',
            files[6] : 'lib/libmine.so',
            files[8] : 'lib/libo.so',
            files[9] : 'lib/libo.so.1',
            files[10] : 'lib/libo.so.1.2',
        }

        self.assertEquals(expected_mapping, mapping)


if __name__ == '__main__':
    unittest.main()
