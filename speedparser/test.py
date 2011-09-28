#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" """

import os
import time
from unittest import TestCase
from pprint import pprint, pformat
try:
    from speedparser import speedparser
except ImportError:
    import speedparser
import feedparser

def feed_equivalence(testcase, fpresult, spresult):
    self = testcase
    fpf = fpresult.feed
    spf = spresult.feed
    self.assertEqual(fpf.title, spf.title)
    if 'subtitle' in fpf:
        self.assertEqual(fpf.subtitle, spf.subtitle)
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
        if nskey:
            self.assertEqual(fpresult.namespaces[nskey], spresult.namespaces[nskey])


class SingleTest(TestCase):
    def setUp(self):
        filename = '0004.dat'
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


class CoverageTest(TestCase):
    def setUp(self):
        self.files = ['feeds/%s' % f for f in os.listdir('feeds/') if not f.startswith('.')]
        self.files.sort()

    def test_feed_coverage(self):
        success = 0
        fperrors = 0
        sperrors = 0
        total = 200
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

class SpeedTest(TestCase):
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

