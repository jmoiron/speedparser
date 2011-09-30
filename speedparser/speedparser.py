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
from lxml import etree, html
from lxml.html import clean
import feedparser

keymap = feedparser.FeedParserDict.keymap
fpnamespaces = feedparser._FeedParserMixin.namespaces

xmlns_map = {
    'http://www.w3.org/2005/atom': 'atom10',
    'http://purl.org/rss/1.0/': 'rss10',
    'http://my.netscape.com/rdf/simple/0.9/': 'rss090',
}

default_cleaner = clean.Cleaner(comments=True, javascript=True,
        scripts=True, safe_attrs_only=True, page_structure=True)

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

nsre = re.compile(r'xmlns=[\'"](.+?)[\'"]')
def strip_namespace(document):
    if 'xmlns=' not in document[:300]:
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


class SpeedParserEntriesRss20(object):
    entry_xpath = '/rss/item | /rss/channel/item'
    tag_map = {
        'pubDate' : 'date',
        'date': 'date',
        'updated' : 'date',
        'link' : 'links',
        'title': 'title',
        'creator': 'author',
        'author': 'author',
        'comments': 'comments',
        'encoded': 'content',
        'content': 'content',
        'summary': 'summary',
        'description': 'summary',
        'media:content': 'media_content',
        'media:thumbnail': 'media_thumbnail',
        'media:group': 'media_group',
        'itunes:summary': 'content',
        'gr:annotation': 'annotation',
    }

    def __init__(self, root, namespaces={}, version='rss20', encoding='utf-8', cleaner=default_cleaner):
        self.encoding = encoding
        self.namespaces = namespaces
        self.nslookup = self.reverse_namespace_map()
        self.cleaner = cleaner
        self.entry_objects = root.xpath(self.entry_xpath, namespaces=namespaces)
        entries = []
        for obj in self.entry_objects:
            d = self.parse_entry(obj)
            if d: entries.append(d)
        self.entries = entries

    def reverse_namespace_map(self):
        d = dict([(v,k) for (k,v) in self.namespaces.iteritems()])
        d.update(fpnamespaces)
        return d

    def parse_entry(self, entry):
        """An attempt to parse pieces of an entry out w/o xpath, by looping
        over the entry root's children and slotting them into the right places.
        This is going to be way messier than SpeedParserEntries, and maybe
        less cleanly usable, but it should be faster."""

        def clean_ns(tag):
            if '}' in tag:
                split = tag.split('}')
                return split[0].strip('{'), split[-1]
            return '', tag

        e = feedparser.FeedParserDict()
        tag_map = self.tag_map
        nslookup = self.nslookup

        for child in entry.getchildren():
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

        return e

    def parse_date(self, node, entry, ns=''):
        value = unicoder(node.text)
        entry['updated'] = value
        entry['updated_parsed'] = feedparser._parse_date(value)

    def parse_title(self, node, entry, ns=''):
        entry['title'] = unicoder(node.text) or ''

    def parse_author(self, node, entry, ns=''):
        if ns and ns in ('itunes', 'dm'): return
        if node.text:
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

    def parse_annotation(self, node, entry, ns='gr'):
        if entry.get('author', '') and 'unknown' not in entry['author'].lower():
            return
        for child in node:
            if child.tag.endswith('author'):
                self.parse_author(child, entry, ns='')

    def parse_links(self, node, entry, ns=''):
        if node.text:
            entry['link'] = unicoder(node.text).strip('#')
        if 'link' not in entry and node.attrib.get('rel', '') == 'alternate':
            entry['link'] = unicoder(node.attrib['href']).strip('#')
        entry.setdefault('links', []).append(node.attrib)

    def parse_comments(self, node, entry, ns=''):
        if 'comments' in entry and ns: return
        entry['comments'] = unicoder(node.text)

    def parse_content(self, node, entry, ns=''):
        # media:content is usually nonsense we don't want
        if ns and node.tag.endswith('content') and ns not in ('itunes',):
            return
        content = unicoder(node.text)
        if content:
            content = self.cleaner.clean_html(content)
        entry['content'] = [{'value': content or ''}]

    def parse_summary(self, node, entry, ns=''):
        if ns in ('itunes', ): return
        summary = unicoder(node.text)
        if summary:
            summary = self.cleaner.clean_html(summary).strip()
        entry['summary'] = summary or ''

    def parse_media_content(self, node, entry, ns='media'):
        entry.setdefault('media_content', []).append(node.attrib)
        for child in node:
            if child.tag.endswith('thumbnail'):
                entry.setdefault('media_thumbnail', []).append(child.attrib)

    def parse_media_thumbnail(self, node, entry, ns='media'):
        entry.setdefault('media_thumbnail', []).append(node.attrib)

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

    def parse_author(self, node, entry, ns=''):
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

class SpeedParserFeed(object):
    date_path = '''
        /rss/channel/lastBuildDate |
        /rss/channel/pubDate
    '''.strip()
    root_tag = 'rss'

    def __init__(self, root, namespaces={}, encoding='utf-8', type='rss20'):
        self.root = root
        self.nsmap = namespaces or root.nsmap
        self.encoding = encoding
        for k in self.nsmap.keys():
            if not k:
                # not allowed in xpath (grumble)
                del self.nsmap[k]
        feed = {}
        feed['title'], feed['subtitle'] = self.parse_title()
        feed['link'], feed['links'] = self.parse_links()
        feed['updated'], feed['updated_parsed'] = self.parse_updated()
        feed['generator'] = self.parse_generator()
        feed['language'] = self.parse_lang()
        # filter out crap we don't need
        for key in feed.keys():
            if feed[key] is None:
                del feed[key]
        self.feed = feed

    def xpath(self, query):
        try:
            return self.root.xpath(query, namespaces=self.nsmap)
        except:
            import traceback
            traceback.print_exc()

    def rq(self, query):
        return '/%s%s' % (self.root_tag, query)

    def parse_title(self):
        title = first_text(self.xpath(self.rq('/channel/title')))
        subtitle = first_text(self.xpath(self.rq('/channel/description')))
        return title, subtitle

    def parse_generator(self):
        return first_text(self.xpath('/rss/channel/generator'), None)

    def parse_lang(self):
        return first_text(self.xpath('/rss/channel/language'), None)

    def parse_updated(self):
        updated = first_text(self.xpath(self.date_path), None)
        updated_parsed = feedparser._parse_date(updated)
        return updated, updated_parsed

    def parse_links(self):
        elems = self.xpath(self.rq('/channel/*[local-name()="link"]'))
        link = ''
        links = []
        for e in elems:
            if e.tag == 'link':
                link = e.text or ''
            else:
                links.append(e.attrib)
        return link, links

    def feed_dict(self):
        return self.feed

class SpeedParserFeedRdf(SpeedParserFeed):
    root_tag = '/rdf:RDF'
    date_path = '''/rdf:RDF/channel/*[local-name()="date"]'''

    def __init__(self, root, namespaces={}, encoding='utf-8', type='rss20'):
        if None in namespaces:
            namespaces['rdf'] = namespaces[None]
            del namespaces[None]
        super(SpeedParserFeedRdf, self).__init__(root, namespaces, type)

    def parse_lang(self):
        langkey = [k for k in self.root.keys() if k.endswith('lang')]
        if langkey:
            return self.root.attrib[langkey[0]]
        return super(SpeedParserFeedRdf, self).parse_lang()

class SpeedParserFeedAtom(SpeedParserFeed):
    root_tag = '/feed'
    date_path = '/feed/updated'

    def parse_title(self):
        title = first_text(self.xpath('/feed/title'))
        subtitle = first_text(self.xpath('/feed/subtitle'))
        return title, subtitle

    def parse_generator(self):
        return first_text(self.xpath('/feed/generator'))

    def parse_lang(self):
        langkey = [k for k in self.root.keys() if k.endswith('lang')]
        if langkey:
            return self.root.attrib[langkey[0]]
        return super(SpeedParserFeedAtom, self).parse_lang()

    def parse_links(self):
        id = first_text(self.xpath('/feed/id'))
        elems = self.xpath('/feed/link')
        link = ''
        links = []
        for e in elems:
            links.append(e.attrib)
            if e.attrib.get('rel', '') == 'alternate':
                link = e.attrib['href']
        if id and not link:
            link = id
        return link, links

class SpeedParser(object):
    def __init__(self, content, cleaner=default_cleaner):
        self.cleaner = cleaner
        self.xmlns, content = strip_namespace(content)
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
        vers = 'unk'
        if self.xmlns and self.xmlns.lower() in xmlns_map:
            return xmlns_map[self.xmlns.lower()]
        elif self.xmlns:
            vers = self.xmlns.split('/')[-2].replace('.', '')
        if r.attrib.get('version', None):
            vers = r.attrib['version'].replace('.', '')
        tag = r.tag.split('}')[-1].lower()
        if tag in ('rss', 'rdf'):
            tag = 'rss'
        if tag in ('feed'):
            tag = 'atom'
        return '%s%s' % (tag, vers)

    def parse_namespaces(self):
        nsmap = self.root.nsmap.copy()
        for key in nsmap.keys():
            if key is None:
                nsmap[''] = nsmap[key]
                del nsmap[key]
                break
        return nsmap

    def parse_encoding(self):
        return self.tree.docinfo.encoding.lower()

    def parse_feed(self, version, encoding):
        if version in ('rss20', 'rss092', 'rss091'):
            return SpeedParserFeed(self.root, encoding=encoding).feed_dict()
        if version == 'rss10':
            return SpeedParserFeedRdf(self.root, namespaces=self.namespaces, encoding=encoding).feed_dict()
        if version == 'atom10':
            return SpeedParserFeedAtom(self.root, namespaces=self.namespaces, encoding=encoding).feed_dict()
        raise IncompatibleFeedError("Feed not compatible with speedparser.")

    def parse_entries(self, version, encoding):
        kwargs = dict(encoding=encoding, namespaces=self.namespaces, cleaner=self.cleaner)
        if version in ('rss20', 'rss092', 'rss091'):
            return SpeedParserEntriesRss20(self.root, **kwargs).entry_list()
        if version == 'rss10':
            return SpeedParserEntriesRdf(self.root, **kwargs).entry_list()
        if version == 'atom10':
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


def parse(document, clean_html=True):
    cleaner = default_cleaner if clean_html else fake_cleaner
    result = feedparser.FeedParserDict()
    result['feed'] = feedparser.FeedParserDict()
    result['entries'] = []
    result['bozo'] = 0
    try:
        parser = SpeedParser(document, cleaner)
        parser.update(result)
    except Exception, e:
        import traceback
        result['bozo'] = 1
        result['bozo_exception'] = e
        result['bozo_tb'] = traceback.format_exc()
    return result



