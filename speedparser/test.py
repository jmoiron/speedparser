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
        threshold = 0.01
        if len(s1) > 1024 and len(s2) > 1024:
            threshold = 0.25
        match = lambda x, y: difflib.SequenceMatcher(None, x, y).ratio()
        self.assertTrue(match(s1, s2) > threshold,
            "%s \n ---- \n %s\n are not similar enough (%0.3f < %0.3f)" % (s1, s2, match(s1, s2), threshold))

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

def entry_equivalence(test_case, fpresult, spresult):
    self = test_case
    self.assertEqual(len(fpresult.entries), len(spresult.entries))
    for fpe,spe in zip(fpresult.entries, spresult.entries):
        self.assertEqual(fpe.author, spe.author)
        self.assertEqual(fpe.link, spe.link)
        if 'comments' in fpe:
            self.assertEqual(fpe.comments, spe.comments)
        if 'updated' in fpe:
            # we don't care what date fields we used as long as they
            # ended up the same
            #self.assertEqual(fpe.updated, spe.updated)
            self.assertEqual(fpe.updated_parsed, spe.updated_parsed)
        self.assertPrettyClose(fpe.summary, spe.summary)
        self.assertPrettyClose(fpe.title, spe.title)
        if 'content' in fpe:
            self.assertPrettyClose(fpe.content[0]['value'], spe.content[0]['value'])

class SingleTest(TestCaseBase):
    def setUp(self):
        filename = '0013.dat'
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

class SingleTestEntries(TestCaseBase):
    def setUp(self):
        filename = '0006.dat'
        with open('feeds/%s' % filename) as f:
            self.doc = f.read()

    def tearDown(self):
        self.doc = None

    def test_single_feed(self):
        fpresult = feedparser.parse(self.doc)
        spresult = speedparser.parse(self.doc)

        d = dict(fpresult)
        d['entries'] = d['entries'][:4]
        pprint(d)
        pprint(spresult)
        feed_equivalence(self, fpresult, spresult)
        entry_equivalence(self, fpresult, spresult)


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
        failedentries = []
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
            try:
                entry_equivalence(self, fpresult, spresult)
            except:
                failedentries.append(f)
        print "Success: %d out of %d (%0.2f %%, fpe: %d, spe: %d)" % (success,
                total, (100 * success)/float(total-fperrors), fperrors, sperrors)
        print "Entry Success: %d out of %d (%0.2f %%)" % (success-len(failedentries),
                success, (100*(success-len(failedentries)))/float(total-fperrors))
        print "Failed Paths:\n%s" % pformat(failedpaths)
        print "Failed entries:\n%s" % pformat(failedentries)

class SpeedTest(TestCaseBase):
    def setUp(self):
        self.files = ['feeds/%s' % f for f in os.listdir('feeds/') if not f.startswith('.')]
        self.files.sort()

    def test_speed(self):
        total = 10
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
        fpspeed = getspeed(feedparser, self.files[:total])
        spspeed = getspeed(speedparser, self.files[:total])
        pct = lambda x: total/x
        print "feedparser: %0.2f/sec,  speedparser: %0.2f/sec" % (pct(fpspeed), pct(spspeed))

