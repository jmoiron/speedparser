#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" """

from lxml import etree
import sys

if not len(sys.argv) == 2:
    print "Supply one xml file to xmlpprint.py"
    sys.exit(-1)

tree = etree.parse(sys.argv[1])
print etree.tostring(tree, pretty_print=True)

