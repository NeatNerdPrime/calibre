#!/usr/bin/env python


__license__   = 'GPL v3'
__copyright__ = '2009, Kovid Goyal <kovid@kovidgoyal.net>'
__docformat__ = 'restructuredtext en'

import os
import sys

from calibre.customize.conversion import InputFormatPlugin
from calibre.utils.resources import get_path as P


class LRFInput(InputFormatPlugin):

    name        = 'LRF Input'
    author      = 'Kovid Goyal'
    description = _('Convert LRF files to HTML')
    file_types  = {'lrf'}
    commit_name = 'lrf_input'

    def convert(self, stream, options, file_ext, log,
                accelerators):
        from calibre.ebooks.lrf.input import Canvas, ImageBlock, MediaType, RuledLine, Styles, TextBlock
        self.log = log
        self.log('Generating XML')
        from lxml import etree

        from calibre.ebooks.lrf.lrfparser import LRFDocument
        from calibre.utils.xml_parse import safe_xml_fromstring
        d = LRFDocument(stream)
        d.parse()
        xml = d.to_xml(write_files=True)
        if options.verbose > 2:
            open('lrs.xml', 'wb').write(xml.encode('utf-8'))
        doc = safe_xml_fromstring(xml)

        char_button_map = {}
        for x in doc.xpath('//CharButton[@refobj]'):
            ro = x.get('refobj')
            jump_button = doc.xpath(f'//*[@objid="{ro}"]')
            if jump_button:
                jump_to = jump_button[0].xpath('descendant::JumpTo[@refpage and @refobj]')
                if jump_to:
                    char_button_map[ro] = '{}.xhtml#{}'.format(jump_to[0].get('refpage'),
                            jump_to[0].get('refobj'))
        plot_map = {}
        for x in doc.xpath('//Plot[@refobj]'):
            ro = x.get('refobj')
            image = doc.xpath(f'//Image[@objid="{ro}" and @refstream]')
            if image:
                imgstr = doc.xpath('//ImageStream[@objid="{}" and @file]'.format(image[0].get('refstream')))
                if imgstr:
                    plot_map[ro] = imgstr[0].get('file')

        self.log('Converting XML to HTML...')
        styledoc = safe_xml_fromstring(P('templates/lrf.xsl', data=True))
        media_type = MediaType()
        styles = Styles()
        text_block = TextBlock(styles, char_button_map, plot_map, log)
        canvas = Canvas(doc, styles, text_block, log)
        image_block = ImageBlock(canvas)
        ruled_line = RuledLine()
        extensions = {
                ('calibre', 'media-type') : media_type,
                ('calibre', 'text-block') : text_block,
                ('calibre', 'ruled-line') : ruled_line,
                ('calibre', 'styles')     : styles,
                ('calibre', 'canvas')     : canvas,
                ('calibre', 'image-block'): image_block,
                }
        transform = etree.XSLT(styledoc, extensions=extensions)
        try:
            result = transform(doc)
        except RuntimeError:
            sys.setrecursionlimit(5000)
            result = transform(doc)

        with open('content.opf', 'wb') as f:
            f.write(result)
        styles.write()
        return os.path.abspath('content.opf')
