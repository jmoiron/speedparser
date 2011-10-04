speedparser
-----------

Speedparser is a black-box "style" reimplementation of the `Universal Feed
Parser <http://www.feedparser.org/>`_.  It uses some feedparser code for date
and authors, but mostly re-implements its data normalization algorithms based
on feedparser output.  It uses ``lxml`` for feed parsing and for optional HTML
cleaning.  Its compatibility with ``feedparser`` is very good for a strict 
subset of fields, but poor for fields outside that subset.  See
``tests/speedparsertests.py`` for more information on which fields are more or
less compatible and which are not.

On an Intel(R) Core(TM) i5 750, running only on one core, ``feedparser`` managed
``2.5 feeds/sec`` on the test feed set (roughly 4200 "feeds" in 
``tests/feeds.tar.bz2``), while ``speedparser`` manages around ``65 feeds/sec``
with HTML cleaning on and ``200 feeds/sec`` with cleaning off.

installing
----------

``pip install speedparser``

usage
-----

Usage is similar to feedparser::

    >>> import speedparser
    >>> result = speedparser.parse(feed)
    >>> result = speedparser.parse(feed, clean_html=False)

differences
-----------

There are a few interface differences and many result differences between
speedparser and feedparser.  The biggest similarity is that they both return
a ``FeedParserDict()`` object (with keys accessible as attributes), they both
set the ``bozo`` key when an error is encountered, and various aspects of the
``feed`` and ``entries`` keys are likely to be identical *or* very similar.

``speedparser`` uses different (and in some cases less or none; buyer beware)
data cleaning algorithms than ``feedparser``.  When it is enabled, lxml's
``html.cleaner`` library will be used to clean HTML and give similar but not
identical protection against various attributes and elements.  It will *only*
clean entry ``content`` and ``summary`` fields.

If your application is using ``feedparser`` to consume many feeds at once and
CPU is becoming a bottleneck, you might want to try out ``speedparser`` as an
alternative (using ``feedparser`` as a backup).  If you are writing an
application that does not ingest many feeds, or where CPU is not a problem,
you should use ``feedparser`` as it is flexible with bad or malformed data and
has a much better test suite.


