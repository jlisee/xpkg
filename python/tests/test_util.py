# Author: Joseph Lisee <jlisee@gmail.com>

__doc__ = """Tests for the util module
"""

# Python Imports
import unittest

# Project Imports
from xpm import util


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

if __name__ == '__main__':
    unittest.main()
