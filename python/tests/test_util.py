# Author: Joseph Lisee <jlisee@gmail.com>

__doc__ = """Tests for the util module
"""

# Python Imports
import os
import unittest

# Project Imports
from xpkg import util


class UtilTests(unittest.TestCase):

    def do_compare(self, a, b, val, strtype):
        res = util.compare_versions(a,b)
        args = (a, strtype, b)
        self.assertEqual(val, res, 'Expected version: "%s" %s "%s"' % args)

    def test_version_class(self):
        """
        Test that our version class can properly parse out the parts of a
        version.
        """

        inputs = [
            # Test just versions
            ('1', (0,'1','',[1])),
            ('alpha', (0,'alpha','',['alpha'])),
            ('beta2', (0,'beta2','',['beta',2])),

            # Epoch version
            ("2:1", (2,'1','',[1])),

            # Debian revision
            ("1-bob", (0, '1','bob',[1])),

            # Full test
            ("3:1.0.10-fox", (3,'1.0.10','fox',[1,'.',0,'.', 10])),
            ]

        for verstr, results in inputs:
            attrs = ['epoch', 'version', 'release', 'version_parts']


            for attrname, expected, in zip(attrs, results):
                # Build version object
                ver = util.Version(verstr)

                # Grab our expected value
                value = getattr(ver, attrname)

                args = (verstr, attrname, expected, value)
                msg = "For '%s' version.%s '%s' != '%s' " % args
                self.assertEqual(expected, value, msg)

    def test_version_string_cmp(self):
        def do_compare(a, b, val, strtype):
            #res = cmp(a,b)
            res = util.version_string_cmp(a,b)
            args = (a, strtype, b, res)
            self.assertEqual(val, res, 'Expected: "%s" %s "%s" was: %d' % args)

        # Define comparison functions
        less = lambda a,b: do_compare(a, b, -1, '<')
        equal = lambda a,b: do_compare(a, b, 0, '==')
        greater = lambda a,b: do_compare(a, b, 1, '>')

        # Define our inputs
        inputs = [
            # Test normal string behavior
            ('a', 'b', less),
            ('b', 'a', greater),
            ('a', 'a', equal),
            ('alpha', 'beta', less),

            # Test strings of unequal length
            ('a', 'aa', less),
            ('aa', 'a', greater),

            # Empty string order
            ('', 'a', less),
            ('a', '', greater),
            ('', '', equal),

            # Test tilde ordering
            ('~', 'a', less),
            ('~~', '~a', less),
            ('~', '', less),
            ('', '~', greater),
            ('~', '~', equal),

            # Test tilde versions
            ('~beta', '', less),
            ('~beta', '~~prebeta', greater),
            ]

        for a, b, comparator in inputs:
            comparator(a, b)

        # Test by sorting a list
        exp = ['~~', '~~a', '~', '', 'a']
        l = ['a', '~', '', '~~a', '~~',]
        sorted_l = sorted(l, cmp = util.version_string_cmp)

        self.assertEqual(exp, sorted_l)

        # Test basic string
        exp = ['a', 'b', 'c']
        l = ['b', 'c', 'a']
        sorted_l = sorted(l, cmp = util.version_string_cmp)

        self.assertEqual(exp, sorted_l)


    def test_version_compare(self):
        # Define comparison functions
        less = lambda a,b: self.do_compare(a, b, -1, '<')
        equal = lambda a,b: self.do_compare(a, b, 0, '==')
        greater = lambda a,b: self.do_compare(a, b, 1, '>')

        # Define our inputs
        inputs = [
            # Really basic versions
            ('1', '2', less),
            ('1', '1', equal),
            ('2', '1', greater),

            # Minor patch differences
            ('1.0.0', '1.0.1', less),
            ('1.0.21', '1.0.21', equal),
            ('1.0.10', '1.0.9', greater),

            # Full version numbers
            ('1.9.0', '1.10.1', less),
            ('1.0.1', '1.0.1', equal),
            ('1.0.1', '1.0.0', greater),

            # Mixed version numbers
            ('1.1', '1.1.2', less),

            # Epoch version test
            ("2:1", "1:2", greater),
            ("10", "1:2", less),

            # Alpha vs beta versions
            ("alpha", "beta", less),
            ("alpha1", "alpha2", less),
            ("alpha10", "alpha2", greater),

            # Compare tilde versions
            ("3.0~beta1", "3.0", less),
            ("3.0~beta", "3.0~~prebeta", greater),
            ("3.0~beta4", "3.0~rc1", less),

            # Compare debian versions
            ("3.0-2", "3.0-10", less),
            ]

        # Do our comparisons
        for a, b, comparator in inputs:
            comparator(a, b)


    def test_wrap_yaml_string(self):
        long_string = "Tool which controls the generation of executables " \
                      "and other non-source files of a program from the" \
                      " program's source files."

        wrapped = util.wrap_yaml_string(long_string,tab=4)
        expected = ">\n" \
                   "    Tool which controls the generation of executables and"\
                   " other non-source files\n" \
                   "    of a program from the program's source files."

        self.assertEqual(expected, wrapped)

    def test_temp_dir(self):
        """
        Make sure our temporary directory function works
        """

        with util.temp_dir('bob_smith') as tdir:
            # Make sure we have the directory and our naming convention
            if not os.path.exists(tdir):
                self.fail('Temporary dir: "%s" does not exist' % tdir)

            self.assertRegexpMatches(tdir, '.*bob_smith')

            # Touch a file and make sure it's in our dir
            util.touch('my_file')

            if not os.path.exists(os.path.join(tdir, 'my_file')):
                self.fail('We are not in the desired directory')


        # Make sure the directory no longer existss
        if os.path.exists(tdir):
            self.fail('Temporary dir: "%s" still exists, not cleaned up' % tdir)



class SortTests(unittest.TestCase):

    def test_topological_sort(self):
        """
        Test basic topological sort
        """

        # Basic dependency graph
        graph = {
            'libmulti' : [],
            'libmulti-dev' : ['libmulti'],
            'multi-tools' : ['libmulti'],
        }

        actual = sorted(util.topological_sort(graph))
        expected = ['libmulti', 'libmulti-dev', 'multi-tools']
        self.assertEqual(expected, actual)


    def test_robust_topological_sort(self):
        """
        Test that we can sort properly even with loops!
        """

        # A graph with cycles:
        #
        #         <-        <-
        #        /   \     /  /
        #  0 -> 1 -> 2 -> 3 --
        graph = {
            0 : [1],
            1 : [2],
            2 : [1,3],
            3 : [3],
        }

        # Do our sort
        topo_graph = util.robust_topological_sort(graph)
        expected = [(0,), (2, 1), (3,)]

        self.assertEqual(expected, topo_graph)

    # TODO: update this code to optionally detect cycles and make sure are
    # detected properly (like toposort so we can drop the req)


if __name__ == '__main__':
    unittest.main()
