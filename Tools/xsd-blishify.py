import argparse
import copy
import lxml.etree as etree

parser = argparse.ArgumentParser(description="Modify XMLSchema file to duplicate attributes into Blish HUD-specific versions")
parser.add_argument('--inplace', action="store_true")
parser.add_argument('--sort', action="store_true")
parser.add_argument('file', type=str)
args = parser.parse_args()

nsmap = {"xs": "http://www.w3.org/2001/XMLSchema"}

with open(args.file, "rb+") as f:
    parser = etree.XMLParser(encoding='utf-8', strip_cdata=False)
    root = etree.parse(f, parser=parser)

    agmap : "dict[str, list[etree.ElementBase | None]]" = {}

    for ag in root.findall(".//xs:attributeGroup", namespaces=nsmap):
        ag : etree.ElementBase
        name : "str | None" = ag.get("name")
        if name is not None:
            basename = name
            if name.startswith("bh-"):
                basename = name[3:]

            item = agmap.setdefault(basename, [None, None])

            if name.startswith("bh-"):
                item[1] = ag
            else:
                item[0] = ag

    for basename in agmap:
        base, bh = agmap[basename]
        if base is None or bh is None:
            continue

        if args.sort:
            def key(elt):
                if elt.tag == "{http://www.w3.org/2001/XMLSchema}attribute":
                    return elt.get("name")
                return ""

            base[:] = sorted(base, key=key)
        
        for attr in bh.findall('xs:attribute', namespaces=nsmap):
            bh.remove(attr)

        for attr in base.findall('xs:attribute', namespaces=nsmap):
            attr : etree.ElementBase
            attr = copy.deepcopy(attr)
            attr.set("name", "bh-%s" % attr.get("name"))
            if attr.get("use") == "required":
                del attr.attrib["use"]
            if attr.get("default"):
                del attr.attrib["default"]

            bh.insert(len(bh), attr)
        # print(etree.tostring(bh))

    # fixup ag refs
    for ref in root.findall('//xs:attributeGroup', namespaces=nsmap):
        ref : etree.ElementBase
        tgt = ref.get("ref")
        if tgt is None or tgt not in agmap:
            continue

        # should be left with just the basenames
        # check for existing bh-ref
        found = False
        for ref2 in ref.getparent().findall('xs:attributeGroup', namespaces=nsmap):
            tgt2 = ref2.get("ref")
            if tgt2 is None:
                continue
            if tgt2.startswith("bh-") and tgt2[3:] == tgt:
                found = True
                break
        if found:
            continue

        newref = copy.deepcopy(ref)
        newref.set("ref", "bh-%s" % tgt)
        ref.addnext(newref)
    
    if args.inplace:
        f.seek(0)
        root.write(f, encoding='utf-8', xml_declaration=True)
        f.truncate()
    else:
        print(etree.tostring(root, xml_declaration=True, encoding='utf-8').decode('utf-8'))