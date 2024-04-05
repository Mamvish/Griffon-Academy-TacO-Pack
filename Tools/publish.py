import zipfile
from pathlib import Path

with zipfile.ZipFile("wing.taco", 'w', compression=zipfile.ZIP_DEFLATED) as zip:
    for f in Path('.').glob('*.xml'):
        zip.write(f)
    for f in Path('Data/Markers').rglob('*'):
        zip.write(f)
    for f in Path('Data/Trails').rglob('*.xml'):
        zip.write(f)
    for f in Path('Data/Trails').rglob('*.trl'):
        zip.write(f)