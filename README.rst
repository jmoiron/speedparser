speedparser
-----------

Speedparser is a black-box reimplementation of the `Universal Feed
Parser <http://www.feedparser.org/>`_.  It uses ``lxml`` for feed parsing and 
for optional HTML cleaning.  Its compatibility with ``feedparser`` is very
good for a strict subset of fields, but poor for fields outside that subset.  See
``tests/speedparsertests.py`` for more information on which fields are more or
less compatible and which are not.

On an Intel(R) Core(TM) i5 750, running only on one core, ``feedparser`` managed
``2.5 feeds/sec`` on the test feed set (roughly 4200 "feeds" in 
``tests/feeds.tar.bz2``), while ``speedparser`` manages around ``65 feeds/sec``
with HTML cleaning on and ``200 feeds/sec`` with cleaning off.

