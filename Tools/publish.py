from pathlib import Path
import re
import subprocess
import zipfile
from datetime import date

with zipfile.ZipFile("wing.taco", 'w', compression=zipfile.ZIP_DEFLATED) as zip:
    for f in Path('.').glob('*.xml'):
        if f.name == "_wing_a_category.xml":
            try:
                text = f.read_text()
                match = re.search(r'<markercategory name="version" isseparator="1" displayname="version: (\[unspecified\])" />', text)
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
        zip.write(f)