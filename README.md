# The Griffon Academy \[Wing] TacO/Blish Marker Pack

## Layout
- `_legacy` contains the previous version of the pack, kept easily accessible for reference
- `_wing_a_category.xml` contains the basic top-level categories
- `Data/Markers` contains marker and trail icons
- `Data/Trails` contains both trails (`.trl`) and trail metadata (`.toml`)
- `Tools` contains various scripts and data used for maintaining and releasing this pack

## Tools
- `Tools/autotrail.py` generates `.xml` files from the combination of `.trl` data and `.toml` metadata
- `Tools/maps.json` is a list of the various maps in Guild Wars 2, downloaded from the API; this is used by `Tools/autotrail.py`
- `Tools/markers.xsd` is an XML Schema for TacO XML as used here (all tags/attributes lowercase)
- `Tools/publish.py` generates a `wing.taco` zip file for publication
- `Tools/toml-schema.json` is a JSON Schema for the TOML metadata files used here
- `Tools/xml-downcase.py` can be used to convert mixed-case XML files into lowercase ones
- `Tools/xsd-blishify.py` is used to maintain the `bh-foo` duplicate attributes in `Tools/markers.xsd`

## Adding a trail
- Add a `.trl` file somewhere under `Data/Trails`
- Add a `.toml` file with the same name in the same place, specify at least
    - name
    - kind (route/stunt/cave)
    - difficulty (easy/medium/hard/expert/insane or a number from 1 to 5)
- `python Tools/autotrail.py Data` to update the `.xml` files
- `python Tools/publish.py` to update the `wing.taco` file

## Bumping the version
- `git tag -am 1.0.0 1.0.0` to mark the current state as a version
- `python Tools/publish.py` to update the `wing.taco` file
- `git push --tags` to upload your version mark to GitHub for others to see