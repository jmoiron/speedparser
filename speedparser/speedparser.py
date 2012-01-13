#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""An attempt to be able to parse 80% of feeds that feedparser would parse
in about 1% of the time feedparser would parse them in.

LIMITATIONS:

 * result.feed.namespaces will only contain namespaces declaed on the
   root object, not those declared later in the file
 * general lack of support for many types of feeds
 * only things verified in test.py are guaranteed to be there;  many fields
   which were not considered important were skipped

"""

import re
import os
import sys
import time
from lxml import etree, html
from lxml.html import clean

try:
    import feedparser
except:
    import feedparsercompat as feedparser

keymap = feedparser.FeedParserDict.keymap
fpnamespaces = feedparser._FeedParserMixin.namespaces

xmlns_map = {
    'http://www.w3.org/2005/atom': 'atom10',
    'http://purl.org/rss/1.0/': 'rss10',
    'http://my.netscape.com/rdf/simple/0.9/': 'rss090',
}

default_cleaner = clean.Cleaner(comments=True, javascript=True,
        scripts=True, safe_attrs_only=True, page_structure=True,
        style=True)

simple_cleaner = clean.Cleaner(safe_attrs_only=True, page_structure=True)

class FakeCleaner(object):
    def clean_html(self, x): return x

class IncompatibleFeedError(Exception):
    pass

fake_cleaner = FakeCleaner()

# --- text utilities ---

def unicoder(txt, hint=None, strip=True):
    if txt is None:
        return None
    if strip:
        txt = txt.strip()
    if hint:
        try: return txt.decode(hint)
        except: return unicoder(txt)
    try:
        return txt.decode('utf-8')
    except:
        try: return txt.decode('latin-1')
        except: return txt

def first_text(xpath_result, default='', encoding='utf-8'):
    if xpath_result:
        return unicoder(xpath_result[0].text, encoding) or default
    return default

def strip_outer_tag(text):
    """Strips the outer tag, if text starts with a tag.  Not entity aware;
    designed to quickly strip outer tags from lxml cleaner output.  Only
    checks for <p> and <div> outer tags."""
    if not text or not isinstance(text, basestring):
        return text
    stripped = text.strip()
    if (stripped.startswith('<p>') or stripped.startswith('<div>')) and \
        (stripped.endswith('</p>') or stripped.endswith('</div>')):
        return stripped[stripped.index('>')+1:stripped.rindex('<')]
    return text

nsre = re.compile(r'xmlns=[\'"](.+?)[\'"]')
def strip_namespace(document):
    if document[:1000].count('xmlns') > 5:
        if 'xmlns=' not in document[:1000]:
            return None, document
    elif 'xmlns=' not in document[:400]:
        return None, document
    match = nsre.search(document)
    if match:
        return match.groups()[0], nsre.sub('', document)
    return None, document

def munge_author(author):
    """If an author contains an email and a name in it, make sure it is in
    the format: "name (email)"."""
    # this loveliness is from feedparser but was not usable as a function
    if '@' in author:
        emailmatch = re.search(ur'''(([a-zA-Z0-9\_\-\.\+]+)@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)|(([a-zA-Z0-9\-]+\.)+))([a-zA-Z]{2,4}|[0-9]{1,3})(\]?))(\?subject=\S+)?''', author)
        if emailmatch:
            email = emailmatch.group(0)
            # probably a better way to do the following, but it passes all the tests
            author = author.replace(email, u'')
            author = author.replace(u'()', u'')
            author = author.replace(u'<>', u'')
            author = author.replace(u'&lt;&gt;', u'')
            author = author.strip()
            if author and (author[0] == u'('):
                author = author[1:]
            if author and (author[-1] == u')'):
                author = author[:-1]
            author = author.strip()
            return '%s (%s)' % (author, email)
    return author

# --- common xml utilities ---

def reverse_namespace_map(nsmap):
    d = fpnamespaces.copy()
    d.update(dict([(v,k) for (k,v) in nsmap.iteritems()]))
    return d

def base_url(root):
    """Determine the base url for a root element."""
    for attr,value in root.attrib.iteritems():
        if attr.endswith('base') and 'http' in value:
            return value
    return None

def full_href(href, base=None):
    if base is None:
        return href
    if href.startswith('javascript:'):
        return href
    if 'http://' in href or 'https://' in href:
        return href
    return '%s/%s' % (base.rstrip('/'), href.lstrip('/'))

def full_href_attribs(attribs, base=None):
    if base is None: return dict(attribs)
    d = dict(attribs)
    for key,value in d.iteritems():
        if key == 'href':
            d[key] = full_href(value, base)
    return d

def clean_ns(tag):
    """Return a tag and its namespace separately."""
    if '}' in tag:
        split = tag.split('}')
        return split[0].strip('{'), split[-1]
    return '', tag

def xpath(node, query, namespaces={}):
    """A safe xpath that only uses namespaces if available."""
    if namespaces and 'None' not in namespaces:
        return node.xpath(query, namespaces=namespaces)
    return node.xpath(query)

def innertext(node):
    """Return the inner text of a node.  If a node has no sub elements, this
    is just node.text.  Otherwise, it's node.text + sub-element-text +
    node.tail."""
    if not len(node): return node.text
    return (node.text or '') + ''.join([etree.tostring(c) for c in node]) + (node.tail or '')

class SpeedParserEntriesRss20(object):
    entry_xpath = '/rss/item | /rss/channel/item'
    tag_map = {
        'pubDate' : 'date',
        'pubdate' : 'date',
        'date': 'date',
        'updated' : 'date',
        'modified' : 'date',
        'link' : 'links',
        'title': 'title',
        'creator': 'author',
        'author': 'author',
        'name': 'author',
        'guid': 'guid',
        'id': 'guid',
        'comments': 'comments',
        'encoded': 'content',
        'content': 'content',
        'summary': 'summary',
        'description': 'summary',
        'media:content': 'media_content',
        'media:thumbnail': 'media_thumbnail',
        'media_thumbnail': 'media_thumbnail',
        'media:group': 'media_group',
        'itunes:summary': 'content',
        'gr:annotation': 'annotation',
    }

    def __init__(self, root, namespaces={}, version='rss20', encoding='utf-8', feed={},
            cleaner=default_cleaner, unix_timestamp=False):
        self.encoding = encoding
        self.namespaces = namespaces
        self.unix_timestamp = unix_timestamp
        self.nslookup = reverse_namespace_map(namespaces)
        self.cleaner = cleaner
        self.entry_objects = xpath(root, self.entry_xpath, namespaces)
        self.feed = feed
        self.baseurl = base_url(root)
        if not self.baseurl and 'link' in self.feed:
            self.baseurl = self.feed.link
        entries = []
        for obj in self.entry_objects:
            d = self.parse_entry(obj)
            if d: entries.append(d)
        self.entries = entries

    def clean(self, text):
        if text and isinstance(text, basestring):
            return self.cleaner.clean_html(text)
        return text

    def parse_entry(self, entry):
        """An attempt to parse pieces of an entry out w/o xpath, by looping
        over the entry root's children and slotting them into the right places.
        This is going to be way messier than SpeedParserEntries, and maybe
        less cleanly usable, but it should be faster."""

        e = feedparser.FeedParserDict()
        tag_map = self.tag_map
        nslookup = self.nslookup

        for child in entry.getchildren():
            if isinstance(child, etree._Comment):
                continue
            ns, tag = clean_ns(child.tag)
            mapping = tag_map.get(tag, None)
            if mapping:
                getattr(self, 'parse_%s' % mapping)(child, e, nslookup.get(ns, ns))
            if not ns:
                continue
            fulltag = '%s:%s' % (nslookup.get(ns, ''), tag)
            mapping = tag_map.get(fulltag, None)
            if mapping:
                getattr(self, 'parse_%s' % mapping)(child, e, nslookup[ns])

        lacks_summary = 'summary' not in e or e['summary'] is None
        lacks_content = 'content' not in e or not bool(e.get('content', None))

        if not lacks_summary and lacks_content:
            e['content'] = [{'value': e.summary}]

        # feedparser sometimes copies the first content value into the 
        # summary field when summary was completely missing;  we want
        # to do that as well, but avoid the case where summary was given as ''
        if lacks_summary and not lacks_content:
            e['summary'] = e['content'][0]['value']

        if e.get('summary', False) is None:
            e['summary'] = u''

        # support feed entries that have a guid but no link
        if 'guid' in e and 'link' not in e:
            e['link'] = full_href(e['guid'], self.baseurl)

        return e

    def parse_date(self, node, entry, ns=''):
        value = unicoder(node.text)
        entry['updated'] = value
        date = feedparser._parse_date(value)
        if self.unix_timestamp and date:
            date = time.mktime(date)
        entry['updated_parsed'] = date

    def parse_title(self, node, entry, ns=''):
        if ns in ('media',) and 'title' in entry:
            return
        title = unicoder(node.text) or ''
        title = strip_outer_tag(self.clean(title))
        entry['title'] = title or ''

    def parse_author(self, node, entry, ns=''):
        if ns and ns in ('itunes', 'dm') and 'author' in entry:
            return
        if node.text and len(list(node)) == 0:
            entry['author'] = munge_author(unicoder(node.text))
            return
        name, email = None, None
        for child in node:
            if child.tag == 'name': name = unicoder(child.text or '')
            if child.tag == 'email': email = unicoder(child.text or '')
        if name and not email:
            entry['author'] = munge_author(name)
        elif not name and not email:
            entry['author'] = ''
        else:
            entry['author'] = '%s (%s)' % (name, email)

    def parse_guid(self, node, entry, ns=''):
        entry['guid'] = unicoder(node.text)

    def parse_annotation(self, node, entry, ns='gr'):
        if entry.get('author', '') and 'unknown' not in entry['author'].lower():
            return
        for child in node:
            if child.tag.endswith('author'):
                self.parse_author(child, entry, ns='')

    def parse_links(self, node, entry, ns=''):
        if unicoder(node.text):
            entry['link'] = full_href(unicoder(node.text).strip('#'), self.baseurl)
        if 'link' not in entry and node.attrib.get('rel', '') == 'alternate' and 'href' in node.attrib:
            entry['link'] = full_href(unicoder(node.attrib['href']).strip('#'), self.baseurl)
        if 'link' not in entry and 'rel' not in node.attrib and 'href' in node.attrib:
            entry['link'] = full_href(unicoder(node.attrib['href']).strip('#'), self.baseurl)
        entry.setdefault('links', []).append(full_href_attribs(node.attrib, self.baseurl))
        # media can be embedded within links..
        for child in node:
            ns, tag = clean_ns(child.tag)
            if self.nslookup[ns] == 'media' and tag == 'content':
                self.parse_media_content(child, entry)

    def parse_comments(self, node, entry, ns=''):
        if 'comments' in entry and ns: return
        entry['comments'] = strip_outer_tag(self.clean(unicoder(node.text)))

    def parse_content(self, node, entry, ns=''):
        # media:content is processed as media_content below
        if ns and node.tag.endswith('content') and ns not in ('itunes',):
            return
        content = unicoder(innertext(node))
        content = self.clean(content)
        entry.setdefault('content', []).append({'value': content or ''})

    def parse_summary(self, node, entry, ns=''):
        if ns in ('media', ): return
        if ns == 'itunes' and entry.get('summary', None):
            return
        if 'content' in entry:
            entry['summary'] = entry['content'][0]['value']
            return
        summary = unicoder(innertext(node))
        summary = self.clean(summary)
        entry['summary'] = summary or ''

    def parse_media_content(self, node, entry, ns='media'):
        entry.setdefault('media_content', []).append(dict(node.attrib))
        for child in node:
            if child.tag.endswith('thumbnail'):
                entry.setdefault('media_thumbnail', []).append(dict(child.attrib))

    def parse_media_thumbnail(self, node, entry, ns='media'):
        entry.setdefault('media_thumbnail', []).append(dict(node.attrib))

    def parse_media_group(self, node, entry, ns='media'):
        for child in node:
            if child.tag.endswith('content'):
                self.parse_media_content(child, entry)
            elif child.tag.endswith('thumbnail'):
                self.parse_media_thumbnail(child, entry)

    def entry_list(self):
        return self.entries

class SpeedParserEntriesRdf(SpeedParserEntriesRss20):
    entry_xpath = '/rdf:RDF/item | /rdf:RDF/channel/item'

class SpeedParserEntriesAtom(SpeedParserEntriesRss20):
    entry_xpath = '/feed/entry'

    def parse_summary(self, node, entry, ns=''):
        if 'content' in entry:
            entry['summary'] = entry['content'][0]['value']
        else:
            super(SpeedParserEntriesAtom, self).parse_summary(node, entry, ns)

class SpeedParserFeedRss20(object):
    channel_xpath = '/rss/channel'
    tag_map = {
        'title' : 'title',
        'description' : 'subtitle',
        'tagline' : 'subtitle',
        'subtitle' : 'subtitle',
        'link' : 'links',
        'pubDate': 'date',
        'updated' : 'date',
        'modified' : 'date',
        'date': 'date',
        'generator' : 'generator',
        'generatorAgent': 'generator',
        'language' : 'lang',
        'id': 'id',
        'lastBuildDate' : 'date',
    }

    def __init__(self, root, namespaces={}, encoding='utf-8', type='rss20', cleaner=default_cleaner,
            unix_timestamp=False):
        """A port of SpeedParserFeed that uses far fewer xpath lookups, which
        ends up simplifying parsing and makes it easier to catch the various
        names that different tags might come under."""
        self.root = root
        self.unix_timestamp = unix_timestamp
        nslookup = reverse_namespace_map(namespaces)
        self.cleaner = cleaner
        self.baseurl = base_url(root)

        feed = feedparser.FeedParserDict()
        tag_map = self.tag_map

        channel = xpath(root, self.channel_xpath, namespaces)
        if len(channel) == 1:
            channel = channel[0]

        for child in channel:
            if isinstance(child, etree._Comment):
                continue
            ns, tag = clean_ns(child.tag)
            mapping = tag_map.get(tag, None)
            if mapping:
                getattr(self, 'parse_%s' % mapping)(child, feed, nslookup.get(ns, ns))
            if not ns:
                continue
            fulltag = '%s:%s' % (nslookup.get(ns, ''), tag)
            mapping = tag_map.get(fulltag, None)
            if mapping:
                getattr(self, 'parse_%s' % mapping)(child, feed, nslookup[ns])


        # this copies feedparser behavior if, say, xml:lang is defined in the
        # root feed element, even though this element tends to have garbage like
        # "utf-8" in it rather than an actual language
        if 'language' not in feed:
            for attr in root.attrib:
                if attr.endswith('lang'):
                    feed['language'] = root.attrib[attr]

        if 'id' in feed and 'link' not in feed:
            feed['link'] = feed['id']

        self.feed = feed

    def clean(self, text, outer_tag=True):
        if text and isinstance(text, basestring):
            if not outer_tag:
                txt = self.cleaner.clean_html(text)
                frag = lxml.html.fragment_fromstring(txt)
                import ipdb; ipdb.set_trace();
            return self.cleaner.clean_html(text)
        return text

    def parse_title(self, node, feed, ns=''):
        feed['title'] = strip_outer_tag(self.clean(unicoder(node.text))) or ''

    def parse_subtitle(self, node, feed, ns=''):
        feed['subtitle'] = strip_outer_tag(self.clean(unicoder(node.text))) or ''

    def parse_links(self, node, feed, ns=''):
        if node.text:
            feed['link'] = full_href(unicoder(node.text).strip('#'), self.baseurl)
        if 'link' not in feed and node.attrib.get('rel', '') == 'alternate' and 'href' in node.attrib:
            feed['link'] = full_href(unicoder(node.attrib['href']).strip('#'), self.baseurl)
        if 'link' not in feed and 'rel' not in node.attrib and 'href' in node.attrib:
            feed['link'] = full_href(unicoder(node.attrib['href']).strip('#'), self.baseurl)
        feed.setdefault('links', []).append(full_href_attribs(node.attrib, self.baseurl))

    def parse_date(self, node, feed, ns=''):
        value = unicoder(node.text)
        feed['updated'] = value
        date = feedparser._parse_date(value)
        if self.unix_timestamp and date:
            date = time.mktime(date)
        feed['updated_parsed'] = date

    def parse_lang(self, node, feed, ns=''):
        feed['language'] = unicoder(node.text)

    def parse_generator(self, node, feed, ns=''):
        value = unicoder(node.text)
        if value:
            feed['generator'] = value
        else:
            for value in node.attrib.itervalues():
                if 'http://' in value:
                    feed['generator'] = value

    def parse_id(self, node, feed, ns=''):
        feed['id'] = unicoder(node.text)

    def feed_dict(self):
        return self.feed

class SpeedParserFeedAtom(SpeedParserFeedRss20):
    channel_xpath = '/feed'

class SpeedParserFeedRdf(SpeedParserFeedRss20):
    channel_xpath = '/rdf:RDF/channel'

class SpeedParser(object):
    def __init__(self, content, cleaner=default_cleaner, unix_timestamp=False):
        self.cleaner = cleaner
        self.xmlns, content = strip_namespace(content)
        self.unix_timestamp = unix_timestamp
        if self.xmlns and '#' in self.xmlns:
            self.xmlns = self.xmlns.strip('#')
        tree = etree.fromstring(content)
        if isinstance(tree, etree._ElementTree):
            self.tree = tree
            self.root = tree.getroot()
        else:
            self.tree = tree.getroottree()
            self.root = tree
        self.encoding = self.parse_encoding()
        self.version = self.parse_version()
        if 'unk' in self.version:
            raise IncompatibleFeedError("Could not determine version of this feed.")
        self.namespaces = self.parse_namespaces()
        self.feed = self.parse_feed(self.version, self.encoding)
        self.entries = self.parse_entries(self.version, self.encoding)

    def parse_version(self):
        r = self.root
        root_ns, root_tag = clean_ns(r.tag)
        root_tag = root_tag.lower()
        vers = 'unk'
        if self.xmlns and self.xmlns.lower() in xmlns_map:
            value =  xmlns_map[self.xmlns.lower()]
            if value == 'rss10' and root_tag == 'rss':
                value = 'rss010'
            if not (value.startswith('atom') and root_tag == 'rss'):
                return value
        elif self.xmlns:
            vers = self.xmlns.split('/')[-2].replace('.', '')
        tag = root_tag
        if r.attrib.get('version', None):
            vers = r.attrib['version'].replace('.', '')
        if root_tag in ('rss', 'rdf'):
            tag = 'rss'
        if root_tag in ('feed'):
            tag = 'atom'
        if root_tag == 'rss' and vers == '10' and root_tag == 'rss':
            vers = ''
        return '%s%s' % (tag, vers)

    def parse_namespaces(self):
        nsmap = self.root.nsmap.copy()
        for key in nsmap.keys():
            if key is None:
                nsmap[self.xmlns] = nsmap[key]
                del nsmap[key]
                break
        return nsmap

    def parse_encoding(self):
        return self.tree.docinfo.encoding.lower()

    def parse_feed(self, version, encoding):
        kwargs = dict(
            encoding=encoding,
            unix_timestamp=self.unix_timestamp,
            namespaces=self.namespaces
        )
        if version in ('rss20', 'rss092', 'rss091', 'rss'):
            return SpeedParserFeedRss20(self.root, **kwargs).feed_dict()
        if version == 'rss10':
            return SpeedParserFeedRdf(self.root, **kwargs).feed_dict()
        if version in ('atom10', 'atom03'):
            return SpeedParserFeedAtom(self.root, **kwargs).feed_dict()
        raise IncompatibleFeedError("Feed not compatible with speedparser.")

    def parse_entries(self, version, encoding):
        kwargs = dict(encoding=encoding, namespaces=self.namespaces,
            cleaner=self.cleaner, feed=self.feed, unix_timestamp=self.unix_timestamp)
        if version in ('rss20', 'rss092', 'rss091', 'rss'):
            return SpeedParserEntriesRss20(self.root, **kwargs).entry_list()
        if version == 'rss10':
            return SpeedParserEntriesRdf(self.root, **kwargs).entry_list()
        if version in ('atom10', 'atom03'):
            return SpeedParserEntriesAtom(self.root, **kwargs).entry_list()
        raise IncompatibleFeedError("Feed not compatible with speedparser.")

    def update(self, result):
        if self.version:
            result['version'] = self.version
        if self.namespaces:
            result['namespaces'] = self.namespaces
        if self.feed:
            result.feed.update(self.feed)
        if self.entries:
            result['entries'] = self.entries
        if self.encoding:
            result['encoding'] = self.encoding


def parse(document, clean_html=True, unix_timestamp=False):
    """Parse a document and return a feedparser dictionary with attr key access.
    If clean_html is False, the html in the feed will not be cleaned.  If
    clean_html is True, a sane version of lxml.html.clean.Cleaner will be used.
    If it is a Cleaner object, that cleaner will be used.  If unix_timestamp is
    True, the date information will be a numerical unix
    timestamp rather than a struct_time."""
    if isinstance(clean_html, bool):
        cleaner = default_cleaner if clean_html else fake_cleaner
    else:
        cleaner = clean_html
    result = feedparser.FeedParserDict()
    result['feed'] = feedparser.FeedParserDict()
    result['entries'] = []
    result['bozo'] = 0
    try:
        parser = SpeedParser(document, cleaner, unix_timestamp)
        parser.update(result)
    except Exception, e:
        import traceback
        result['bozo'] = 1
        result['bozo_exception'] = e
        result['bozo_tb'] = traceback.format_exc()
    return result


