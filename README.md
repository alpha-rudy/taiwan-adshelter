# Air Defense Shelters

This project converts the air defense shelters of the NPA from KML files (https://adr.npa.gov.tw/) to a single Mapsforge file.

## OSM tags

amenity=air_defense_shelter
name={from Placemark/name}
address={from Placemark/ExtendedData/Data(@name=地址)/value}
floor={from Placemark/ExtendedData/Data(@name=地下樓層數)/value}
capacity={from Placemark/ExtendedData/Data(@name=可容納人數)/value}
