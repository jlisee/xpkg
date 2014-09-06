# Author: Joseph Lisee <jlisee@gmail.com>

__doc__ = """Tests for the core module
"""

# Python Imports
import copy
import os
import unittest

# Project Imports
from xpkg import core
from xpkg import util


class UtilTests(unittest.TestCase):
    def test_remove_special_offset_files(self):
        # Expected results
        expected_offset_info = {
            'text_files' : {'etc/test.cfg' : [1]},
            'sub_binary_files' : {
                'lib/python/test.py' : [[200]],
                },
            'binary_files' : {
                'bin/running' : [843,987],
                },
            }

        # Input value
        offset_info = copy.deepcopy(expected_offset_info)

        offset_info['sub_binary_files'].update({
                'lib/python/test.pyc' : [[100,120]],
                })

        offset_info['binary_files'].update({
                'bin/pop.pyc' : [123,550],
                })

        # Filter things
        new_offset, file_list = core.remove_special_offset_files(offset_info)
        expected_files = ['lib/python/test.pyc', 'bin/pop.pyc']

        self.assertEqual(expected_files, file_list)
        self.assertEqual(expected_offset_info, new_offset)



if __name__ == '__main__':
    unittest.main()
