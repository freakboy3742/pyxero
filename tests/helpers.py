import re
from collections import defaultdict
from xml.dom.minidom import parseString

import six


def assertXMLEqual(test_case, xml1, xml2, message=""):
    def to_str(s):
        return s.decode("utf-8") if six.PY3 and isinstance(s, bytes) else str(s)

    def clean_xml(xml):
        xml = "<root>%s</root>" % to_str(xml)
        return str(re.sub(">\n *<", "><", parseString(xml).toxml()))

    def xml_to_dict(xml):
        nodes = re.findall("(<([^>]*)>(.*?)</\\2>)", xml)
        if len(nodes) == 0:
            return xml
        d = defaultdict(list)
        for node in nodes:
            d[node[1]].append(xml_to_dict(node[2]))
        return d

    cleaned = map(clean_xml, (xml1, xml2))
    d1, d2 = tuple(map(xml_to_dict, cleaned))

    test_case.assertEqual(d1, d2, message)
