import argparse
import collections.abc as abc
import datetime
from functools import reduce
import os.path
from pathlib import Path
import re
import struct
import traceback
import tomllib
import uuid

from lxml.builder import ElementMaker
import lxml.etree as etree

def main():
    parser = argparse.ArgumentParser(description="Given a TOML config, generate a XML file with trail markers etc.")
    parser.add_argument('file', type=str, nargs='*')
    args = parser.parse_args()

    files = []
    for f in args.file:
        if os.path.isdir(f):
            files.extend(Path(f).rglob("*.toml"))
        else:
            files.append(Path(f))

    for f in files:
        f: Path
        try:
            out = process_file(f)
            with open(f.with_suffix(".xml"), 'wb') as outf:
                outf.write(out)
        except Exception as e:
            print(f"While processing {f.as_posix()!r}")
            print(traceback.format_exc())

# based on https://github.com/dlamkins/TmfLib/blob/master/Reader/TrlFileReader.cs
class TrlReader(abc.Iterator):
    def __init__(self, path):
        self._path = path
    def __enter__(self):
        self._fh = open(self._path, "rb")
        self.version = struct.unpack("<i", self._fh.read(4))[0]
        if self.version != 0:
            raise ValueError(f"Unknown TRL version {self.version}")
        self.mapid = struct.unpack("<i", self._fh.read(4))[0]
        return self
    def __exit__(self, *args):
        self._fh.close()
    def __next__(self):
        if p := self._fh.read(12):
            return struct.unpack("<fff", p)
        else:
            raise StopIteration

def read_trl(path):
    with TrlReader(path) as t:
        first = next(t)
        last = reduce(lambda x,y: y, t, first)
        return (t.mapid, first, last)

def prettyprint(element, **kwargs):
    xml = etree.tostring(element, pretty_print=True, **kwargs)
    print(xml.decode(), end='')        

catescape = re.compile('[^a-zA-Z0-9_]')
uuidns = "09c70591-b6c3-4e60-9fb9-4ad7b207454c" # a random uuid4

def process_file(path):
    with open(path, "rb") as f:
        data = tomllib.load(f)
        trailfile = data.get('trail', path.with_suffix(".trl"))

        mapid, first, last = read_trl(trailfile)

        kind = data.get('kind', 'route')

        difficultymap = ["easy", "medium", "hard", "expert", "insane"]
        difficulty = data.get('difficulty', 'unknown')
        if isinstance(difficulty, int):
            stars = difficulty
            difficulty = difficultymap[difficulty - 1]
        elif difficulty == "unknown":
            stars = 1
        elif difficulty in difficultymap:
            stars = difficultymap.index(difficulty) + 1
        else:
            raise ValueError(f"Unknown difficulty {difficulty!r}")

        name = data.get('name', path)
        catname = catescape.sub("_", name).lower()

        cat = f"griffon_flying.{kind}.{difficulty}.{catname}"

        if 'description' in data:
            desc = data['description']
        elif 'author' in data:
            desc = f"{name} Creator: {data['author']}"
        else:
            desc = name

        E = ElementMaker()

        def poi(mapid, pos, **kwargs):
            def maybe_str(x):
                if isinstance(x, str):
                    return x
                else:
                    return f"{x:.6g}"
            
            pos = [maybe_str(x) for x in pos]

            return E.poi(mapid=str(mapid), xpos=pos[0], ypos=pos[1], zpos=pos[2], **kwargs)
        
        def trail(**kwargs):
            return [E.trail(**kwargs),
                    E.trail(**kwargs, iswall="1", alpha="0", **{'bh-alpha': "0.9"})]

        def markercategory(name, displayname, *args, **kwargs):
            return E.markercategory(*args, name=name, displayname=displayname, **kwargs)

        extra_markers = []

        extra_marker_types = ['springer', 'griffon', 'sharp_turn_left', 'sharp_turn_right']
        nav_marker_types = ['sharp_turn_left', 'sharp_turn_right']

        for t in extra_marker_types:
            if t in nav_marker_types:
                mycat = f"{cat}.trail.nav"
            else:
                mycat = f"{cat}.trail"

            for m in data.get(t, []):
                pos = (m['xpos'], m['ypos'], m['zpos'])

                extra_markers.append(poi(mapid, pos, type=mycat,
                                         iconfile=f"Data/Markers/{t.replace('_', '')}.png",
                                         fadenear="4000", fadefar="6000"))

        has_nav_markers = any(t in data for t in nav_marker_types)
        nav_category = []
        if has_nav_markers:
            nav_category = [markercategory("nav", "Navigation hints")]

        doc = E.overlaydata(
            etree.Comment(f"Generated by autotrail.py from {path!r} at {datetime.datetime.now(datetime.timezone.utc)}"),

            markercategory(
                "griffon_flying", "Griffon Flying",
                markercategory(kind, kind.title() + "s",
                    markercategory(difficulty, f"{stars} Star - {difficulty.title()}",
                        markercategory(catname, name,
                            markercategory("trail", "Trail", *nav_category),
                            defaulttoggle="0", mapdisplaysize="2"
                        )
                    )
                ),
            ),

            E.pois(
                poi(mapid, first, type=cat,
                    togglecategory=f"{cat}.trail", toggle=f"{cat}.trail", triggerrange="4",
                    iconfile=f"Data/Markers/wingstart_{stars}star.png",
                    iconsize="1.5", fadenear="4000", fadefar="6000",
                    **{'tip-description': desc}),

                *trail(traildata=trailfile, type=f"{cat}.trail",
                    fadenear="4000", fadefar="5000", color="ff6611", animspeed="0.2",
                    texture="Data/Markers/feather.png"),

                poi(mapid, first, type=cat,
                    togglecategory=f"{cat}.trail", toggle=f"{cat}.trail", triggerrange="4",
                    iconfile=f"Data/Markers/wingfinish.png",
                    iconsize="1.8", fadenear="4000", fadefar="6000"),

                *extra_markers
            )
        )

        return etree.tostring(doc, pretty_print=True, encoding='utf-8', xml_declaration=True)

main()