import unittest
from xml.etree import ElementTree

from goplbld import CruiseTree


class TestCruiseTree(unittest.TestCase):
    def test_read_minimal(self):
        text = '<?xml version="1.0"?>\n<info>abc</info>'
        tree = CruiseTree.fromstring(text)
        self.assertEqual('info', tree.getroot().tag)
        self.assertEqual('abc', tree.getroot().text)

    def test_tree_to_xml(self):
        text = ('<?xml version="1.0"?>\n'
                '<cruise>\n'
                '    <pipelines group="x" />\n'
                '</cruise>')
        tree = CruiseTree.fromstring(text)
        pipeline_group = tree.find('pipelines')
        pipeline = ElementTree.SubElement(pipeline_group, 'pipeline')
        pipeline.set('name', 'y')
        expected = ('<cruise>\n'
                    '    <pipelines group="x"><pipeline name="y" /></pipelines>\n'
                    '</cruise>')
        actual = tree.tostring()

        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
