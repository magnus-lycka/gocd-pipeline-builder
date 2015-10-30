from xml.etree import ElementTree


class CruiseTree(ElementTree.ElementTree):
    @classmethod
    def fromstring(cls, text):
        return cls(ElementTree.fromstring(text))

    def tostring(self):
        return ElementTree.tostring(self.getroot())
