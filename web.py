#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""A webserver that serves feeds from the feed download directory, but
does so after a 500msec (non-blocking) delay."""

import os
import random
import eventlet
from eventlet import wsgi

def serve_file(filename):
    path = 'feeds/%s' % filename
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return ''

def hello_world(env, start_response):
    if env['PATH_INFO'] != '/':
        # sleep an average of 0.5s
        time = random.random()
        print "%s sleeping for %0.2fs" % (env['PATH_INFO'], time)
        eventlet.sleep(time)
        start_response('200 OK', [('Content-Type', 'text/xml')])
        return [serve_file(env['PATH_INFO'].strip('/'))]
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return ['{"status": "ok"}']

wsgi.server(eventlet.listen(('', 9898)), hello_world)

