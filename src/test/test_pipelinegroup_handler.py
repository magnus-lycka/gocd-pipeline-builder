import unittest
from cruise_tree import CruiseTree


class PipelineGroupHandler(object):
    class PipelineGroup:
        def __init__(self, group_element):
            self._element = group_element

        @property
        def name(self):
            return self._element.attrib['group']

    def __init__(self, tree):
        self.tree = tree

    def __len__(self):
        return len(self.tree.getroot().findall('pipelines'))

    def __getitem__(self, item):
        return self.PipelineGroup(self.tree.getroot().findall('pipelines')[item])


class TestPipelineGroupHandler(unittest.TestCase):
    def test_get_no_pipeline_groups(self):
        xml = '''<?xml version="1.0" encoding="utf-8"?>
            <cruise xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                    xsi:noNamespaceSchemaLocation="cruise-config.xsd"
                    schemaVersion="75">
            </cruise>'''
        tree = CruiseTree.fromstring(xml)
        handler = PipelineGroupHandler(tree)
        self.assertEqual(0, len(handler))

    def test_get_two_pipeline_groups(self):
        xml = '''<?xml version="1.0" encoding="utf-8"?>
            <cruise xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                    xsi:noNamespaceSchemaLocation="cruise-config.xsd"
                    schemaVersion="75">
                <pipelines group="ppg1" />
                <pipelines group="ppg2" />
            </cruise>'''
        tree = CruiseTree.fromstring(xml)
        handler = PipelineGroupHandler(tree)
        self.assertEqual(2, len(handler))
        self.assertEqual('ppg1', handler[0].name)
        self.assertEqual('ppg2', handler[1].name)


if __name__ == '__main__':
    unittest.main()
