#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Get feeds from urls.txt and parse them with feedparser."""

import random
import sys
import feedparser
from multiprocessing import Pool

import eventlet
from eventlet.green import urllib2
from eventlet import tpool

active = set([])
titles = list()


def parse_feed(data):
    doc = tpool.execute(feedparser.parse, data)
    return doc.feed.get('title', "NO TITLE")


def parse_feed_callback(result):
    titles.append(result)


def geturl(url, filename):
    active.add(url)
    print "%d active" % len(active)
    try:
        resp = urllib2.urlopen(url, timeout=5)
    except:
        return ''
    finally:
        active.remove(url)
    try:
        document = resp.read()
    except:
        return ''
    if resp.code > 210:
        return ''
    return document


def main():
    opts, args = parse_args()
    pool = eventlet.GreenPool(opts.pool)
    with open(args[0]) as f:
        urls = map(str.strip, f.read().split('\n'))
    to_fetch = random.sample(urls, opts.max)
    filenames = ['%04d.dat' % i for i in range(1, opts.max + 1)]
    parser_pool = Pool(5)
    results = []
    for document in pool.imap(geturl, to_fetch, filenames):
        results.append(parser_pool.apply_async(parse_feed, (document,)))
    titles = [r.get() for r in results]
    parser_pool.close()
    parser_pool.join()
    print titles


def parse_args():
    import optparse
    parser = optparse.OptionParser(usage='%prog [opts] urls.txt')
    parser.add_option('-n', '--pool', default=25, help='pool size')
    parser.add_option('-m', '--max', default=400, help='number of urls to download')
    parser.add_option('', '--no-write', action='store_true', default=False, help='dont write output files')
    opts, args = parser.parse_args()
    opts.max = int(opts.max)
    opts.pool = int(opts.pool)
    if len(args) != 1:
        print "You must provide an argument that is a text file with \\n delimited urls."
        sys.exit(1)
    return opts, args

if __name__ == '__main__':
    main()
