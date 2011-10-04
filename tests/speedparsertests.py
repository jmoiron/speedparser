#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" """

import os
import time
import difflib
from glob import glob
from unittest import TestCase
from pprint import pprint, pformat

try:
    from speedparser import speedparser
except ImportError:
    import speedparser

import feedparser

try:
    import simplejson as json
except:
    import json

try:
    from jinja2.filters import do_filesizeformat as sizeformat
except:
    sizeformat = lambda x: "%0.2f b" % x

class TimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, time.struct_time):
            return time.mktime(o)
        if isinstance(o, Exception):
            return repr(o)
        return json.JSONEncoder.default(self, o)

munge_author = speedparser.munge_author

def load_cache(path):
    """Load a cached feedparser result."""
    jsonpath = path.replace('dat', 'json')
    if not os.path.exists(jsonpath):
        return None
    with open(jsonpath) as f:
        data = json.loads(f.read())
    ret = feedparser.FeedParserDict()
    ret.update(data)
    if 'updated_parsed' in data['feed'] and data['feed']['updated_parsed']:
        try:
            data['feed']['updated_parsed'] = time.gmtime(data['feed']['updated_parsed'])
        except: pass

    ret.feed = feedparser.FeedParserDict(data.get('feed', {}))
    entries = []
    for e in data.get('entries', []):
        if 'updated_parsed' in e and e['updated_parsed']:
            try:
                e['updated_parsed'] = time.gmtime(e['updated_parsed'])
            except: pass
        entries.append(feedparser.FeedParserDict(e))
    ret.entries = entries
    return ret

def update_cache(path, data):
    """Update the feedparser cache."""
    jsonpath = path.replace('dat', 'json')
    if isinstance(data, dict):
        content = json.dumps(data, cls=TimeEncoder)
    elif isinstance(data, basestring):
        content = data
    else:
        return None
    with open(jsonpath, 'w') as f:
        f.write(content)

def feedparse(path):
    with open(path) as f:
        text = f.read()
    try:
        result = feedparser.parse(text)
    except:
        return None
    return (path, json.dumps(result, cls=TimeEncoder).encode('base64'))

def build_feedparser_cache(update=False):
    """Build a feedparser cache."""
    from multiprocessing import Pool, cpu_count

    paths = []
    for path in glob('feeds/*.dat'):
        if not update and os.path.exists(path.replace('dat', 'json')):
            continue
        paths.append(path)

    parser_pool = Pool(cpu_count())
    results = []
    for path in paths:
        results.append(parser_pool.apply_async(feedparse, (path,)))
    for result in results:
        value = result.get()
        if value is None: continue
        path, json = value
        json = json.decode('base64')
        update_cache(path, json)

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
        if len(s1.strip()) == 0 and len(s2.strip()) < 25:
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

    def assertSameEmail(self, em1, em2):
        """Assert two emails are pretty similar.  FP and SP munge emails into
        one format, but SP is more consistent in providing that format than FP
        is."""
        if em1 == em2: return True
        if em1 == munge_author(em2):
            return True
        if em2 == munge_author(em1):
            return True
        if munge_author(em1) == munge_author(em2):
            return True
        # if we just have somehow recorded more information because we are
        # awesome, do not register that as a bug
        if em1 in em2:
            return True
        if '@' not in em1 and '@' not in em2:
            # i've encountered some issues here where both author fields are
            # absolute garbage and feedparser seems to prefer one to the other
            # based on no particular algorithm
            return True
        raise AssertionError("em1 and em2 not similar enough %s != %s" % (em1, em2))

    def assertSameLinks(self, l1, l2):
        l1 = l1.strip('#').lower().strip()
        l2 = l2.strip('#').lower().strip()
        if l1 == l2: return True
        if l1 in l2: return True
        # google uses weird object enclosure stuff that would be slow to
        # parse correctly;  the default link for the entry is good enough
        # in thee cases
        if 'buzz' in l2: return True
        if 'plus.google.com' in l2: return True
        # feedparser actually has a bug here where it'l strip ;'s from &gt; in
        # url, though a javascript: href is probably utter garbage anyway
        if l2.startswith('javascript:'):
            return self.assertPrettyClose(l1, l2)
        raise AssertionError('link1 and link2 are not similar enough %s != %s' % (l1, l2))

    def assertSameTime(self, t1, t2):
        if not t1 and not t2: return True
        if t1 == t2: return True
        gt1 = time.gmtime(time.mktime(t1))
        gt2 = time.gmtime(time.mktime(t2))
        if t1 == gt2: return True
        if t2 == gt1: return True
        raise AssertionError("time1 and time2 are not similar enough (%r != %r)" % (t1, t2))

def feed_equivalence(testcase, fpresult, spresult):
    self = testcase
    fpf = fpresult.feed
    spf = spresult.feed
    self.assertEqual(fpf.title, spf.title)
    if 'subtitle' in fpf:
        self.assertPrettyClose(fpf.subtitle, spf.subtitle)
    if 'generator' in fpf:
        self.assertEqual(fpf.generator, spf.generator)
    if 'link' in fpf and fpf.link:
        self.assertSameLinks(fpf.link, spf.link)
    if 'language' in fpf:
        self.assertEqual(fpf.language, spf.language)
    if 'updated' in fpf:
        self.assertEqual(fpf.updated, spf.updated)
        self.assertSameTime(fpf.updated_parsed, spf.updated_parsed)

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
            self.assertSameLinks(fpe.link, spe.link)
        if 'author' in fpe:
            self.assertSameEmail(fpe.author, spe.author)
        if 'comments' in fpe:
            self.assertEqual(fpe.comments, spe.comments)
        if 'updated' in fpe and 'updated_parsed' in fpe and fpe.updated_parsed:
            # we don't care what date fields we used as long as they
            # ended up the same
            #self.assertEqual(fpe.updated, spe.updated)
            self.assertSameTime(fpe.updated_parsed, spe.updated_parsed)
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
                    elif ':' in key:
                        # these have generally not been important and are
                        # usually namespaced keys..  if the key *also* exists
                        # in fmc with a ':' in it, or has a ':' in it to start,
                        # lets ignore it
                        continue
                    elif key not in smc:
                        matched = False
                        for k in smc:
                            if k.endswith(key) and ':' in k:
                                matched = True
                                break
                        if matched:
                            continue
                        message = "Non-namespaced key failure in media_content:\n"
                        message += "%s\n-----%s\n" % (pformat(dict(fmc)), pformat(dict(smc)))
                        message += "key %s not found in smc" % key
                        raise AssertionError(message)
                    else:
                        self.assertEqual(fmc[key].lower(), smc[key].lower())
        if 'media_thumbnail' in fpe:
            self.assertEqual(len(fpe.media_thumbnail), len(spe.media_thumbnail))
            for fmt,smt in zip(fpe.media_thumbnail, spe.media_thumbnail):
                for key in fmt:
                    self.assertEqual(fmt[key], smt[key])

class MultiTestEntries(TestCaseBase):
    def setUp(self):
        self.filenames = [
         'feeds/1114.dat',
         'feeds/2047.dat',
         'feeds/2072.dat',
         'feeds/2091.dat',
        ]

    def test_feeds(self):
        for path in self.filenames:
            with open(path) as f:
                doc = f.read()
            fpresult = feedparser.parse(doc)
            spresult = speedparser.parse(doc)
            try:
                feed_equivalence(self, fpresult, spresult)
                entry_equivalence(self, fpresult, spresult)
            except:
                import traceback
                print "Comp Failure: %s" % path
                traceback.print_exc()


class SingleTest(TestCaseBase):
    def setUp(self):
        filename = '0003.dat'
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
        d = dict(spresult)
        d['entries'] = d['entries'][:4]
        pprint(d)
        feed_equivalence(self, fpresult, spresult)
        entry_equivalence(self, fpresult, spresult)

class EntriesCoverageTest(TestCaseBase):
    """A coverage test that does not check to see if the feed level items
    are the same;  it only tests that entries are similar."""
    def setUp(self):
        self.files = [f for f in glob('feeds/*.dat') if not f.startswith('.')]
        self.files.sort()

    def test_entries_coverage(self):
        success = 0
        fperrors = 0
        sperrors = 0
        errcompats = 0
        fperror = False
        total = len(self.files)
        total = 1000
        failedpaths = []
        failedentries = []
        bozoentries = []
        for f in self.files[:total]:
            fperror = False
            with open(f) as fo:
                document = fo.read()
            try:
                fpresult = load_cache(f)
                if fpresult is None:
                    fpresult = feedparser.parse(document)
            except:
                fperrors += 1
                fperror = True
            if fpresult.get('bozo', 0):
                fperrors += 1
                fperror = True
            try:
                spresult = speedparser.parse(document)
            except:
                if fperror:
                    errcompats += 1
                else:
                    sperrors += 1
                    bozoentries.append(f)
                continue
            if 'bozo_exception' in spresult:
                if fperror:
                    errcompats += 1
                else:
                    sperrors += 1
                    bozoentries.append(f)
                continue
            try:
                entry_equivalence(self, fpresult, spresult)
                success += 1
            except:
                import traceback
                print "Failure: %s" % f
                traceback.print_exc()
                failedentries.append(f)
        print "Success: %d out of %d (%0.2f %%, fpe: %d, spe: %d, both: %d)" % (success,
                total, (100 * success)/float(total-fperrors), fperrors, sperrors, errcompats)
        print "Failed entries:\n%s" % pformat(failedentries)
        print "Bozo entries:\n%s" % pformat(bozoentries)


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
        self.files = [f for f in glob('feeds/*.dat') if not f.startswith('.')]
        self.files.sort()

    def test_speed(self):
        total = len(self.files)
        total = 300
        def getspeed(parser, files):
            fullsize = 0
            t0 = time.time()
            for f in files:
                with open(f) as fo:
                    document = fo.read()
                    fullsize += len(document)
                try:
                    parser.parse(document)
                except:
                    pass
            td = time.time() - t0
            return td, fullsize
        #fpspeed = getspeed(feedparser, self.files[:total])
        spspeed, fullsize = getspeed(speedparser, self.files[:total])
        pct = lambda x: total/x
        print "speedparser: %0.2f/sec, %s/sec" % (pct(spspeed), sizeformat(fullsize/spspeed))
        #print "feedparser: %0.2f/sec,  speedparser: %0.2f/sec" % (pct(fpspeed), pct(spspeed))

class SpeedTestNoClean(TestCaseBase):
    def setUp(self):
        self.files = [f for f in glob('feeds/*.dat') if not f.startswith('.')]
        self.files.sort()

    def test_speed(self):
        total = len(self.files)
        def getspeed(parser, files, args=[]):
            fullsize = 0
            t0 = time.time()
            for f in files:
                with open(f) as fo:
                    document = fo.read()
                    fullsize += len(document)
                try:
                    parser.parse(document, *args)
                except:
                    pass
            td = time.time() - t0
            return td, fullsize
        #fpspeed = getspeed(feedparser, self.files[:total])
        spspeed, fullsize = getspeed(speedparser, self.files[:total], args=(False,))
        pct = lambda x: total/x
        print "speedparser (no html cleaning): %0.2f/sec, %s/sec" % (pct(spspeed), sizeformat(fullsize/spspeed))
        #print "feedparser: %0.2f/sec,  speedparser: %0.2f/sec (html cleaning disabled)" % (pct(fpspeed), pct(spspeed))


if __name__ == '__main__':
    build_feedparser_cache()

