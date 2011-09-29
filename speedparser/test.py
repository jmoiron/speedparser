#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" """

import os
import time
import difflib
from unittest import TestCase
from pprint import pprint, pformat
try:
    from speedparser import speedparser
except ImportError:
    import speedparser
import feedparser

class TestCaseBase(TestCase):
    def assertPrettyClose(self, s1, s2):
        """Assert that two strings are pretty damn near equal.  This gets around
        differences in little tidy nonsense FP does that SP won't do."""
        self.assertTrue(difflib.SequenceMatcher(None, s1, s2).ratio() > 0.98,
            "%s and %s are not similar enough" % (s1, s2))

def feed_equivalence(testcase, fpresult, spresult):
    self = testcase
    fpf = fpresult.feed
    spf = spresult.feed
    self.assertEqual(fpf.title, spf.title)
    if 'subtitle' in fpf:
        self.assertPrettyClose(fpf.subtitle, spf.subtitle)
    if 'generator' in fpf:
        self.assertEqual(fpf.generator, spf.generator)
    self.assertEqual(fpf.link, spf.link)
    if 'language' in fpf:
        self.assertEqual(fpf.language, spf.language)
    if 'updated' in fpf:
        self.assertEqual(fpf.updated, spf.updated)
        self.assertEqual(fpf.updated_parsed, spf.updated_parsed)

    self.assertEqual(fpresult.version, spresult.version)
    self.assertEqual(fpresult.encoding, spresult.encoding)
    # make sure the namespaces are set up properly;  feedparser adds some
    # root namespaces based on some processing and some dicts that we do not bother with
    for nskey in fpresult.namespaces:
        if nskey and nskey in spresult.namespaces:
            self.assertEqual(fpresult.namespaces[nskey], spresult.namespaces[nskey])
        elif nskey:
            print "namespace %s missing from spresult" % nskey


class SingleTest(TestCaseBase):
    def setUp(self):
        filename = '0011.dat'
        with open('feeds/%s' % filename) as f:
            self.doc = f.read()

    def tearDown(self):
        self.doc = None

    def test_single_feed(self):
        fpresult = feedparser.parse(self.doc)
        spresult = speedparser.parse(self.doc)

        d = dict(fpresult)
        d['entries'] = len(fpresult.entries)
        pprint(d)
        pprint(spresult)
        feed_equivalence(self, fpresult, spresult)


class CoverageTest(TestCaseBase):
    def setUp(self):
        self.files = ['feeds/%s' % f for f in os.listdir('feeds/') if not f.startswith('.')]
        self.files.sort()

    def test_feed_coverage(self):
        success = 0
        fperrors = 0
        sperrors = 0
        total = 20
        failedpaths = []
        for f in self.files[:total]:
            with open(f) as fo:
                document = fo.read()
            try:
                fpresult = feedparser.parse(document)
            except:
                fperrors += 1
                continue
            try:
                spresult = speedparser.parse(document)
            except:
                sperrors += 1
                continue
            try:
                feed_equivalence(self, fpresult, spresult)
                success += 1
            except:
                failedpaths.append(f)
                pass
        print "Success: %d out of %d (%0.2f %%, fpe: %d, spe: %d)" % (success,
                total, (100 * success)/float(total), fperrors, sperrors)
        print pformat(failedpaths)

class SpeedTest(TestCaseBase):
    def setUp(self):
        self.files = ['feeds/%s' % f for f in os.listdir('feeds/') if not f.startswith('.')]
        self.files.sort()

    def test_speed(self):
        def getspeed(parser, files):
            t0 = time.time()
            for f in files:
                with open(f) as fo:
                    document = fo.read()
                try:
                    parser.parse(document)
                except:
                    pass
            td = time.time() - t0
            return td
        fpspeed = getspeed(feedparser, self.files[:20])
        spspeed = getspeed(speedparser, self.files[:20])
        print "feedparser: %0.2f,  speedparser: %0.2f" % (fpspeed, spspeed)

