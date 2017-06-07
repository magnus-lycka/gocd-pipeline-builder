#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

import unittest
from xml.etree import ElementTree

from gocdpb.goserver_config import CruiseTree


class TestCruiseTree(unittest.TestCase):
    def test_read_minimal(self):
        text = '<?xml version="1.0"?>\n<info>abc</info>'
        tree = CruiseTree.fromstring(text)
        self.assertEqual('info', tree.getroot().tag)
        self.assertEqual('abc', tree.getroot().text)

    def test_tree_to_xml(self):
        text = ('<?xml version="1.0"?>\n'
                '<cruise>\n'
                '  <pipelines group="x" />\n'
                '</cruise>')
        tree = CruiseTree.fromstring(text)
        pipeline_group = tree.find('pipelines')
        pipeline = ElementTree.SubElement(pipeline_group, 'pipeline')
        pipeline.set('name', 'y')
        expected = ('<cruise>\n'
                    '  <pipelines group="x">\n'
                    '    <pipeline name="y" />\n'
                    '  </pipelines>\n'
                    '</cruise>\n')
        actual = tree.tostring()

        self.assertEqual(expected, actual)

    def test_move_all_pipelines_in_group(self):
        text = ('<cruise>\n'
                '  <server />\n'
                '  <pipelines group="x">\n'
                '    <authorization>\n'
                '      <view>\n'
                '        <role>Developer</role>\n'
                '      </view>\n'
                '      <operate>\n'
                '        <role>Developer</role>\n'
                '      </operate>\n'
                '    </authorization>\n'
                '    <pipeline name="p1" />\n'
                '    <pipeline name="p2" />\n'
                '  </pipelines>\n'
                '  <pipelines group="z" />\n'
                '  <agents />\n'
                '</cruise>\n')
        tree = CruiseTree.fromstring(text)

        tree.move_all_pipelines_in_group('x', 'y')

        expected = ('<cruise>\n'
                    '  <server />\n'
                    '  <pipelines group="y">\n'
                    '    <authorization>\n'
                    '      <view>\n'
                    '        <role>Developer</role>\n'
                    '      </view>\n'
                    '      <operate>\n'
                    '        <role>Developer</role>\n'
                    '      </operate>\n'
                    '    </authorization>\n'
                    '    <pipeline name="p1" />\n'
                    '    <pipeline name="p2" />\n'
                    '  </pipelines>\n'
                    '  <pipelines group="x">\n'
                    '    <authorization>\n'
                    '      <view>\n'
                    '        <role>Developer</role>\n'
                    '      </view>\n'
                    '      <operate>\n'
                    '        <role>Developer</role>\n'
                    '      </operate>\n'
                    '    </authorization>\n'
                    '  </pipelines>\n'
                    '  <pipelines group="z" />\n'
                    '  <agents />\n'
                    '</cruise>\n')
        actual = tree.tostring()
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
