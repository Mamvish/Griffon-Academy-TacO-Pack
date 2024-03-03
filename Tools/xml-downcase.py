import argparse
import lxml.etree as etree

parser = argparse.ArgumentParser(description="Convert all XML tags and attributes in a file to lowercase, editing in-place")
parser.add_argument('file', type=str)
args = parser.parse_args()

xmlp = etree.XMLParser(encoding='utf-8', strip_cdata=False)

with open(args.file, "rb+") as f:
    root = etree.parse(f, parser=xmlp)
    root : etree.ElementTree
    
    for elt in [root.getroot(), *root.findall("//*")]:
        elt : etree.ElementBase
        elt.tag = elt.tag.lower()
        for k in elt.attrib:
            v = elt.attrib[k]
            del elt.attrib[k]
            elt.attrib[k.lower()] = v

    f.seek(0)
    root.write(f, encoding='utf-8', xml_declaration=True)
    f.truncate()