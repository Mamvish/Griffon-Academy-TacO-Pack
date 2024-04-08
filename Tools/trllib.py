import collections.abc as abc
import struct

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