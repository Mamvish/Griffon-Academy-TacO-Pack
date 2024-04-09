import collections.abc as abc
from io import BufferedIOBase
import struct

def open_or_fh(thing, mode):
    if isinstance(thing, BufferedIOBase):
        return thing
    else:
        return open(thing, mode)

# based on https://github.com/dlamkins/TmfLib/blob/master/Reader/TrlFileReader.cs
class TrlReader(abc.Iterator):
    def __init__(self, src):
        self._src = src
    def __enter__(self):
        self._fh = open_or_fh(self._src, "rb")
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

class TrlWriter():
    def __init__(self, dest, mapid):
        self._dest = dest
        self._mapid = mapid
    def __enter__(self):
        self._fh = open_or_fh(self._dest, "wb")
        self._fh.write(struct.pack("<i", 0)) # version
        self._fh.write(struct.pack("<i", self._mapid))
        return self
    def __exit__(self, *args):
        self._fh.close()
    def append(self, p):
        self._fh.write(struct.pack("<fff", *p))

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str)
    args = parser.parse_args()

    with TrlReader(args.file) as f:
        print(f"mapid={f.mapid}")
        for point in f:
            print(f"{point[0]:10.6f}\t{point[1]:10.6f}\t{point[2]:10.6f}")

if __name__ == "__main__":
    main()