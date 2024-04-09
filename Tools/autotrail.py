import argparse
import collections.abc as abc
import datetime
from functools import reduce
import itertools
import json
import math
import os.path
from pathlib import Path
import re
import struct
import tomllib
import traceback
import uuid

from lxml.builder import E
import lxml.etree as etree
from trllib import TrlReader

# toggle for minimap merge feature
# combines nearby start markers into one for minimap/map purposes to avoid clutter & z-fighting
mm_merge = True

# mapid -> {path -> (x, y, z)} for mm-merge
start_positions = {}
# path -> short desc for mm-merge
merge_descriptions = {}

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
            out = process_file(f, 1)
            with open(f.with_suffix(".xml"), 'wb') as outf:
                outf.write(out)
        except Exception as e:
            print(f"While processing {f.as_posix()!r}")
            print(traceback.format_exc())

    if mm_merge:
        merged_pois = []

        for mapid in sorted(start_positions):
            map = start_positions[mapid]
            merges = {}

            for patha, pathb in itertools.combinations(map, 2):
                a = map[patha]
                b = map[pathb]
                # 2d (minimap) distance, not 3d distance
                if math.dist((a[0], a[2]), (b[0], b[2])) < 16:
                    merges.setdefault(patha, set()).add(pathb)
                    merges.setdefault(pathb, set()).add(patha)

            if len(merges) == 0:
                continue

            merged = {}
            for patha in merges:
                if patha in merged:
                    continue

                avg = [0.0, 0.0, 0.0]
                for coords in [map[patha], *[map[p] for p in merges[patha]]]:
                    avg[0] += coords[0]
                    avg[1] += coords[1]
                    avg[2] += coords[2]
                    pass

                avg[0] /= len(merges[patha]) + 1
                avg[1] /= len(merges[patha]) + 1
                avg[2] /= len(merges[patha]) + 1

                for p in [patha, *merges[patha]]:
                    merged[p] = avg

                    out = process_file(p, 0)
                    with open(p.with_suffix(".xml"), 'wb') as outf:
                        outf.write(out)
                
                pos = pos_to_string(avg)
                merged_pois.append(
                    E.POI(MapID=str(mapid), xpos=pos[0], ypos=pos[1], zpos=pos[2],
                          Type="griffon_flying",
                          inGameVisibility="0",
                          IconFile="Data/Markers/wingstart.png", IconSize="1.5",
                          MapDisplaySize="40",
                          **{'tip-name': f"{len(merges[patha]) + 1} routes start here",
                             'tip-description': "\n".join(merge_descriptions[p] for p in [patha, *merges[patha]])}))
        
        with open("Data/merged_map_icons.xml", "wb") as mf:
            mf.write(etree.tostring(E.OverlayData(E.POIs(*merged_pois)), pretty_print=True, encoding='utf-8', xml_declaration=True))
    else:
        Path("Data/merged_map_icons.xml").unlink(missing_ok=True)

maps = {}
try:
    # Generated from https://api.guildwars2.com/v2/maps?ids=all
    # piped through jq -c '.[]' | sed 's/$/,/g;1s/^/[\n/;$s/,$/\n]/' to render it in jsonl style
    with open('Tools/maps.json') as f:
        for obj in json.load(f):
            maps[obj['id']] = obj
except:
    print("Failed to load Tools/maps.json")
    maps = {}
    pass

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

def toml_to_pos(obj):
    return obj['xpos'], obj['ypos'], obj['zpos']

def pos_to_number(pos):
    return float(pos[0]), float(pos[1]), float(pos[2])

def pos_to_string(pos):
    def maybe_str(x):
        if isinstance(x, str):
            return x
        else:
            return f"{x:.6g}"

    return (maybe_str(pos[0]), maybe_str(pos[1]), maybe_str(pos[2]))

def process_file(path, map_visible):
    with open(path, "rb") as f:
        data = tomllib.load(f)
        trailfile = data.get('trail', path.with_suffix(".trl"))

        mapid, trl_first, trl_last = read_trl(trailfile)

        if data.get('start'):
            start = toml_to_pos(data['start'])
        else:
            start = trl_first

        start_positions.setdefault(mapid, {})[path] = pos_to_number(start)

        if data.get('finish'):
            finish = toml_to_pos(data['finish'])
        else:
            finish = trl_last

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

        cat = f"griffon_flying.{kind}s.{difficulty}.{catname}"

        tip_name = name
        tip_desc = f"{difficulty} {kind}"

        if 'author' in data:
            tip_desc = f"{tip_desc}\nCreator: {data['author']}"

        merge_descriptions[path] = f"{difficulty} {kind}: {name}"

        def poi(mapid, pos, **kwargs):
            pos = pos_to_string(pos)
            return E.POI(MapID=str(mapid), xpos=pos[0], ypos=pos[1], zpos=pos[2], **kwargs)
        
        def trail(**kwargs):
            return [E.Trail(**{**kwargs, 'miniMapVisibility': "0", 'mapVisibility': "0"}),
                    E.Trail(**{**kwargs, 'Texture': "Data/Markers/taco-minimap-path.png", 'inGameVisibility': "0", "MapDisplaySize": "1"}),
                    E.Trail(**{**kwargs, 'miniMapVisibility': "0", 'mapVisibility': "0", 'iswall': "1", 'Alpha': "0", 'bh-alpha': "0.9"})
                    ]

        def markercategory(name, displayname, *args, **kwargs):
            return E.MarkerCategory(*args, name=name, displayname=displayname, **kwargs)

        extra_markers = []

        extra_marker_types = ['springer', 'griffon', 'sharp_turn_left', 'sharp_turn_right']
        nav_marker_types = ['sharp_turn_left', 'sharp_turn_right']

        for t in extra_marker_types:
            if t in nav_marker_types:
                mycat = f"{cat}.trail.nav"
            else:
                mycat = f"{cat}.trail"

            for m in data.get(t, []):
                pos = toml_to_pos(m)

                extra_markers.append(poi(mapid, pos, type=mycat,
                                         iconfile=f"Data/Markers/{t.replace('_', '')}.png",
                                         fadenear="4000", fadefar="6000"))

        has_nav_markers = any(t in data for t in nav_marker_types)
        nav_category = []
        if has_nav_markers or 'hints' in data:
            nav_category = [markercategory("nav", "Navigation hints", defaulttoggle="0")]
            # hints enable
            if 'hints' in data:
                enable_pos = (data['hints']['xpos'], data['hints']['ypos'], data['hints']['zpos'])
            else:
                enable_pos = (start[0], start[1] + 24.0, start[2])

            extra_markers.append(
                poi(mapid, enable_pos,
                    Type=f"{cat}.trail",
                    ToggleCategory=f"{cat}.trail.nav", Toggle=f"{cat}.trail.nav",
                    TriggerRange="4",
                    mapVisibility="0",
                    miniMapvisibility="0",
                    IconFile=f"Data/Markers/winghints.png"))

            # hints disable at finish
            extra_markers.append(
                poi(mapid, finish,
                    Type=f"{cat}.trail",
                    Hide=f"{cat}.trail.nav",
                    TriggerRange="4",
                    inGameVisibility="0",
                    mapVisibility="0",
                    miniMapVisibility="0"))

        wp_category = []
        if 'waypoint' in data:
            wp_category = [markercategory("waypoint", isseparator="1", displayname=f"Nearest Waypoint: {data['waypoint']}", copy=data['waypoint'])]
        elif mapid in maps:
            obj = maps[mapid]
            region = obj.get('region_name', '')
            continent = obj.get('continent_name', '')
            mapname = obj.get('name', '')
            if region != '' and continent != '':
                mapname = f"{mapname}, {region}, {continent}"
            elif region != '':
                mapname = f"{mapname}, {region}"
            elif continent != '':
                mapname = f"{mapname}, {continent}"

            if mapname:
                wp_category = [markercategory("mapname", isseparator="1", displayname=f"Map: {mapname}")]

        popup_text = f"{name}\n{difficulty} {kind}"
        author_category = []
        if 'author' in data:
            author_category = [markercategory("creator", isseparator="1", displayname=f"Created by {data['author']}")]
            popup_text = f"{popup_text}\nCreator: {data['author']}"

        if 'description' in data:
            popup_text = f"{popup_text}\n{data['description']}"

        doc = E.OverlayData(
            etree.Comment(f"Generated by autotrail.py from {path.as_posix()!r} at {datetime.datetime.now(datetime.timezone.utc)}"),

            markercategory(
                "griffon_flying", "Griffon Flying",
                markercategory(kind + "s", kind.title() + "s",
                    markercategory(difficulty, f"{stars} Star - {difficulty.title()}",
                        markercategory(catname, name,
                            *wp_category,
                            *author_category,
                            markercategory("trail", "Trail",
                                *nav_category,
                                defaulttoggle="0"),
                        )
                    )
                ),
            ),

            E.POIs(
                poi(mapid, start, Type=cat,
                    Info=popup_text,
                    ToggleCategory=f"{cat}.trail", Toggle=f"{cat}.trail", TriggerRange="4",
                    IconFile=f"Data/Markers/wingstart_{stars}star.png",
                    IconSize="1.5", MapDisplaySize="40", FadeNear="4000", FadeFar="6000",
                    mapVisibility=str(map_visible).lower(), miniMapVisibility=str(map_visible).lower(),
                    **{'tip-name': f"start: {tip_name}", 'tip-description': tip_desc}),

                *trail(trailData=trailfile.as_posix(), type=f"{cat}.trail",
                    FadeNear="4000", FadeFar="5000", Color=data.get('color', 'ff6611'),
                    Texture="Data/Markers/wingpath.png"),

                poi(mapid, finish, Type=f"{cat}.trail",
                    ToggleCategory=f"{cat}.trail", Toggle=f"{cat}.trail", TriggerRange="4",
                    IconFile=f"Data/Markers/wingfinish.png",
                    IconSize="1.8", FadeNear="4000", FadeFar="6000",
                    **{'tip-name': f"finish: {tip_name}", 'tip-description': tip_desc}),

                *extra_markers
            )
        )

        return etree.tostring(doc, pretty_print=True, encoding='utf-8', xml_declaration=True)

if __name__ == "__main__":
    main()