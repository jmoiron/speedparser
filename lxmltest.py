#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test raw feedparser speeds (pypy test)."""

import os
import time
import feedparser
from pprint import pformat
from lxml import etree
from lxml import html
from multiprocessing import Pool

files = ['feeds/%s' % p for p in os.listdir('feeds/')]

def parse(file):
    with open(file) as f:
        data = f.read()
    try:
        etree.fromstring(data)
        return True
    except:
        try:
            html.fromstring(data)
            return True
        except:
            try:
                feedparser.parse(data)
                return False
            except:
                print "--- error in file %s ---" % file
                return None

t0 = time.time()
pool = Pool(4)
results = pool.map(parse, files)
td = time.time() - t0

fallbacks = len(results) - len(filter(None, results))
d = dict([(k, results.count(k)) for k in set(results)])
print pformat(d)

print "Processed %d feeds in %0.2fs (%0.2f feeds/sec, %d fallbacks)" % (len(files), td, len(files)/td, fallbacks)
