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

munge_author = speedparser.munge_author

class TestCaseBase(TestCase):
    def assertPrettyClose(self, s1, s2):
        """Assert that two strings are pretty damn near equal.  This gets around
        differences in little tidy nonsense FP does that SP won't do."""
        threshold = 0.10
        if len(s1) > 1024 and len(s2) > 1024:
            threshold = 0.25
        # sometimes the title is just made up of some unicode escapes, and since
        # fp and sp treat these differently, we don't pay attention to differences
        # so long as the length is short
        if '&#' in s1 and '&#' not in s2 and len(s1) < 50:
            return True
        matcher = difflib.SequenceMatcher(None, s1, s2)
        ratio = matcher.quick_ratio()
        if ratio < threshold:
            longest_block = matcher.find_longest_match(0, len(s1), 0, len(s2))
            if len(s1) and longest_block.size / float(len(s1)) > threshold:
                return
            if longest_block.size < 50:
                raise AssertionError("%s\n ---- \n%s\n are not similar enough (%0.3f < %0.3f, %d)" %\
                        (s1, s2, ratio, threshold, longest_block.size))

def feed_equivalence(testcase, fpresult, spresult):
    self = testcase
    fpf = fpresult.feed
    spf = spresult.feed
    self.assertEqual(fpf.title, spf.title)
    if 'subtitle' in fpf:
        self.assertPrettyClose(fpf.subtitle, spf.subtitle)
    if 'generator' in fpf:
        self.assertEqual(fpf.generator, spf.generator)
    if 'link' in fpf:
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
        if 'link' in fpe:
            self.assertEqual(fpe.link, spe.link)
        if 'author' in fpe:
            if 'author' not in spe:
                raise AssertionError("spe lacks author: %s\n----\n%s" % (pformat(fpe), pformat(spe)))
            self.assertEqual(munge_author(fpe.author), munge_author(spe.author))
        if 'comments' in fpe:
            self.assertEqual(fpe.comments, spe.comments)
        if 'updated' in fpe:
            # we don't care what date fields we used as long as they
            # ended up the same
            #self.assertEqual(fpe.updated, spe.updated)
            self.assertEqual(fpe.updated_parsed, spe.updated_parsed)
        # lxml's cleaner can leave some stray block level elements around when
        # removing all containing code (like a summary which is just an object
        if 'summary' in fpe:
            if 'summary' not in spe:
                print "%s\n----\n%s\n" % (pformat(fpe), pformat(spe))
            if len(fpe.summary) < 5 and len(spe.summary.replace(' ', '')) < 20:
                pass
            else:
                self.assertPrettyClose(fpe.summary, spe.summary)
        if 'title' in fpe:
            self.assertPrettyClose(fpe.title, spe.title)
        if 'content' in fpe:
            self.assertPrettyClose(fpe.content[0]['value'], spe.content[0]['value'])
        if 'media_content' in fpe:
            self.assertEqual(len(fpe.media_content), len(spe.media_content))
            for fmc,smc in zip(fpe.media_content, spe.media_content):
                for key in fmc:
                    if key == 'isdefault':
                        self.assertEqual(fmc[key], smc['isDefault'])
                    elif key == 'filesize':
                        self.assertEqual(fmc[key], smc['fileSize'])
                    else:
                        self.assertEqual(fmc[key], smc[key])
        if 'media_thumbnail' in fpe:
            self.assertEqual(len(fpe.media_thumbnail), len(spe.media_thumbnail))
            for fmt,smt in zip(fpe.media_thumbnail, spe.media_thumbnail):
                for key in fmt:
                    self.assertEqual(fmt[key], smt[key])

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
        filename = '0178.dat'
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

class EntriesCoverageTest(TestCaseBase):
    """A coverage test that does not check to see if the feed level items
    are the same;  it only tests that entries are similar."""
    def setUp(self):
        self.files = ['feeds/%s' % f for f in os.listdir('feeds/') if not f.startswith('.')]
        self.files.sort()

    def test_entries_coverage(self):
        success = 0
        fperrors = 0
        sperrors = 0
        total = len(self.files)
        total = 300
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
                entry_equivalence(self, fpresult, spresult)
                success += 1
            except:
                import traceback
                print "Failure: %s" % f
                traceback.print_exc()
                failedentries.append(f)
        print "Success: %d out of %d (%0.2f %%, fpe: %d, spe: %d)" % (success,
                total, (100 * success)/float(total-fperrors), fperrors, sperrors)
        print "Failed entries:\n%s" % pformat(failedentries)


class CoverageTest(TestCaseBase):
    def setUp(self):
        self.files = ['feeds/%s' % f for f in os.listdir('feeds/') if not f.startswith('.')]
        self.files.sort()

    def test_feed_coverage(self):
        success = 0
        fperrors = 0
        sperrors = 0
        total = 300
        failedpaths = []
        failedentries = []
        for f in self.files[:total]:
            fperror = False
            with open(f) as fo:
                document = fo.read()
            try:
                fpresult = feedparser.parse(document)
            except:
                fperrors += 1
                fperror = True
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
        total = len(self.files)
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

class SpeedTestNoClean(TestCaseBase):
    def setUp(self):
        self.files = ['feeds/%s' % f for f in os.listdir('feeds/') if not f.startswith('.')]
        self.files.sort()

    def test_speed(self):
        total = len(self.files)
        def getspeed(parser, files, args=[]):
            t0 = time.time()
            for f in files:
                with open(f) as fo:
                    document = fo.read()
                try:
                    parser.parse(document, *args)
                except:
                    pass
            td = time.time() - t0
            return td
        fpspeed = getspeed(feedparser, self.files[:total])
        spspeed = getspeed(speedparser, self.files[:total], args=(False,))
        pct = lambda x: total/x
        print "feedparser: %0.2f/sec,  speedparser: %0.2f/sec (html cleaning disabled)" % (pct(fpspeed), pct(spspeed))

