from pathlib import Path
import re
import subprocess
import zipfile
from datetime import date

def main():
    with zipfile.ZipFile("wing.taco", 'w', compression=zipfile.ZIP_DEFLATED) as zip:
        for f in Path('.').glob('*.xml'):
            if f.name == "_wing_a_category.xml":
                try:
                    text = f.read_text()
                    match = re.search(r'<MarkerCategory name="version" isseparator="1" displayname="version: (\[unspecified\])" />', text)
                    if match:
                        version = date.today().isoformat()

                        try:
                            gitversion = subprocess.run(["git", "describe"], capture_output=True, check=True, text=True).stdout.strip()
                            version = f"{gitversion} {version}"
                        except Exception as e:
                            print("Failed to detect Git version:", e)

                        text = text[:match.start(1)] + version + text[match.end(1):]
                        zip.writestr(f.as_posix(), text)
                        continue
                except Exception as e:
                    print("Failed to substitute version string into _wing_a_category.xml:", e)
            zip.write(f)
        for f in Path('Data/Markers').rglob('*'):
            zip.write(f)
        for f in Path('Data').rglob('*.xml'):
            zip.write(f)
        for f in Path('Data/Trails').rglob('*.trl'):
            munge_trl(zip, f)

def lerp(a, b, t):
    return (1.0 - t) * a + t * b

def munge_trl(zipfile, path):
    """Hack up a .trl file while inserting it into the zip, such that sharp corners become segment breaks.
    This improves rendering in (at least) Blish."""

    from trllib import TrlReader, TrlWriter
    import math

    # based on https://stackoverflow.com/a/13849249
    def dotproduct(v1, v2):
        return sum((a*b) for a, b in zip(v1, v2))

    def length(v):
        return math.sqrt(dotproduct(v, v))

    def clip(v, min, max):
        if v < min:
            return min
        elif v > max:
            return max
        else:
            return v

    def angle(v1, v2):
        return math.acos(clip(dotproduct(v1, v2) / (length(v1) * length(v2)), -1.0, 1.0))

    points = []
    with TrlReader(path) as r:
        for p in r:
            points.append(p)

    # find all the pivot points
    pivots = []
    for i in range(1, len(points)-1):
        v1 = [points[i][j] - points[i-1][j] for j in range(0, 3)]
        v2 = [points[i+1][j] - points[i][j] for j in range(0, 3)]
        if angle(v1, v2) > 1.2: # approx. 68 degrees
            pivots.append(i)

    # turn a, [b], c into a, [b, 0, b], c where b is the pivot point
    # thus, breaking the path into two segments
    pivots.reverse()
    for p in pivots:
        point = points[p]
        points.insert(p, (0, 0, 0))
        points.insert(p, point)

    with TrlWriter(zipfile.open(path.as_posix(), 'w'), r.mapid) as w:
        for point in points:
            w.append(point)

if __name__ == "__main__":
    main()