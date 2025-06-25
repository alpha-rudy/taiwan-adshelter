# Air Defense Shelters

This project converts the air defense shelters of the NPA from KML files (https://adr.npa.gov.tw/) to OSM and Mapsforge files.

## OSM tags

* amenity=air_defense_shelter
* name={from name or 電腦編號 with capacity}
* capacity={from 可容納人數}
* floor={from 地下樓層數}
* cap={from rough 可容納人數}
* addr:housenumber={from 地址}
* desc:*={from parts of description}

## Migration steps for new KML files

1. Download the KML files from https://adr.npa.gov.tw/
2. Replace the old KML files in `srcs/` with the new ones.
3. Use `git diff` to revise the changes.
4. Run `make` to generate the new OSM and Mapsforge files.