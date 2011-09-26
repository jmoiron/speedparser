#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Get feeds from urls.txt and write them to feeds/"""

import random
import sys
from pprint import pprint

import eventlet
from eventlet.green import urllib2
from eventlet import tpool

directory = {}
active = set([])

def write_file(filename, contents):
    with open(filename, 'w') as f:
        f.write(contents)

def geturl(url, filename, no_write=False):
    active.add(url)
    print "%d active" % len(active)
    try:
        resp = urllib2.urlopen(url, timeout=5)
    except:
        return False
    finally:
        active.remove(url)
    try:
        document = resp.read()
    except:
        return False
    if resp.code > 210:
        return False
    if not no_write:
        tpool.execute(write_file, 'feeds/%s' % (filename), document)
        directory[filename] = url
    return True

def main():
    opts, args = parse_args()
    pool = eventlet.GreenPool(opts.pool)
    with open(args[0]) as f:
        urls = map(str.strip, f.read().split('\n'))
    to_fetch = random.sample(urls, opts.max)
    filenames = ['%04d.dat' % i for i in range(1, opts.max+1)]
    responses = list(pool.imap(geturl, to_fetch, filenames, [opts.no_write]*opts.max))
    print "%d of %d succeeded" % (len(filter(None, responses)), opts.max)
    pprint(directory)

def parse_args():
    import optparse
    parser = optparse.OptionParser(usage='%prog [opts] urls.txt')
    parser.add_option('-n', '--pool', default=25, help='pool size')
    parser.add_option('-m', '--max', default=500, help='number of urls to download')
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

