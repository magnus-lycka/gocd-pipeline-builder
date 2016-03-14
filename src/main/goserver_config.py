import copy
from xml.etree import ElementTree


class CruiseTree(ElementTree.ElementTree):
    """
    A thin layer on top of the cruise-config.xml used by the Go server.
    """

    @classmethod
    def fromstring(cls, text):
        return cls(ElementTree.fromstring(text))

    def tostring(self):
        self.indent(self.getroot())
        return ElementTree.tostring(self.getroot())

    def config_subset_tostring(self):
        """
        See GoProxy.set_test_settings_xml()
        """
        root = copy.deepcopy(self).getroot()
        for child in list(root):
            if child.tag not in ('pipelines', 'templates', 'environments'):
                root.remove(child)
        self.indent(root)
        return ElementTree.tostring(root)

    @classmethod
    def indent(cls, elem, level=0):
        """
        Fredrik Lundh's standard recipe.
        (Why isn't this in xml.etree???)
        :param elem: the XML element
        :param level: how much indentation
        """
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                cls.indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def set_test_settings_xml(self, test_settings_xml):
        """
        Replace parts of the Go server config for test purposes

        The main sections in the config are:
        - server
        - repositories
        - pipelines * N
        - templates
        - environments
        - agents
        We want to replace the sections pipelines*, templates and environments.
        Let server and agents stay as usual.
        We've never used repositories so far.
        :param test_settings_xml:
        """
        root = self.getroot()

        self.drop_sections_to_be_replaced(root)

        test_settings = CruiseTree().parse(test_settings_xml)

        ix = self.place_for_test_settings(root)

        for element_type in ('environments', 'templates', 'pipelines'):
            for elem in reversed(test_settings.findall(element_type)):
                root.insert(ix, elem)

    def drop_sections_to_be_replaced(self, root):
        for tag in ('pipelines', 'templates', 'environments'):
            for element_to_drop in self.findall(tag):
                root.remove(element_to_drop)

    @staticmethod
    def place_for_test_settings(root):
        ix = 0  # Silence lint about using ix after the loop. root != []
        for ix, element in enumerate(list(root)):
            if element.tag == 'agents':
                break
        return ix
