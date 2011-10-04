#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test raw feedparser speeds, but this feedparser is patched to use lxml."""

import os
import feedparser
import time
from pprint import pformat
from multiprocessing import Pool

files = ['feeds/%s' % p for p in os.listdir('feeds/')]

def parse(file):
    with open(file) as f:
        data = f.read()
    try:
        result = feedparser.parse(data)
        if result['_used_lxml']:
            return True
        return False
    except:
        return None

t0 = time.time()
pool = Pool(4)
results = pool.map(parse, files)
td = time.time() - t0

d = dict([(k, results.count(k)) for k in set(results)])
print pformat(d)

print "Processed %d feeds in %0.2fs (%0.2f feeds/sec)" % (len(files), td, len(files)/td)