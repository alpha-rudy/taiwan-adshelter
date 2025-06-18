#!/usr/bin/env python3

import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import click

OSM_HEADER = '''<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="kml2osm">'''

OSM_FOOTER = '</osm>'


def parse_kml(kml_file):
    ns = {
        'kml': 'http://www.opengis.net/kml/2.2',
        'gx': 'http://www.google.com/kml/ext/2.2',
        'atom': 'http://www.w3.org/2005/Atom'
    }
    tree = ET.parse(kml_file)
    root = tree.getroot()
    placemarks = root.findall(".//kml:Placemark", ns)
    
    data = []
    for placemark in placemarks:
        name = placemark.find("kml:name", ns)
        name = name.text if name is not None else ""

        extended_data = {}
        for data_el in placemark.findall(".//kml:ExtendedData/kml:Data", ns):
            key = data_el.attrib.get("name")
            value_el = data_el.find("kml:value", ns)
            if key and value_el is not None:
                extended_data[key] = value_el.text

        point = placemark.find(".//kml:Point/kml:coordinates", ns)
        if point is not None:
            coords = point.text.strip().split(',')
            if len(coords) >= 2:
                lon, lat = coords[:2]
                node = {
                    'lat': float(lat),
                    'lon': float(lon),
                    'tags': {
                        'amenity': 'air_defense_shelter',
                        'name': name,
                        'address': extended_data.get('地址', ''),
                        'under_floor': extended_data.get('地下樓層數', ''),
                        'capacity': extended_data.get('可容納人數', '')
                    }
                }
                data.append(node)

    return data


def build_osm(nodes):
    osm_body = []
    id_counter = -1000
    for node in nodes:
        lat = node['lat']
        lon = node['lon']
        tags = node['tags']

        escaped_tags = {k: escape(v) for k, v in tags.items() if v}

        osm_node = [f'<node id="{id_counter}" visible="true" lat="{lat}" lon="{lon}">']
        osm_node.extend([f'<tag k="{k}" v="{v}"/>' for k, v in escaped_tags.items()])
        osm_node.append('</node>')

        osm_body.append('\n'.join(osm_node))
        id_counter -= 1

    return f"{OSM_HEADER}\n{chr(10).join(osm_body)}\n{OSM_FOOTER}"

@click.command()
@click.argument('kml_file', type=click.Path(exists=True))
@click.argument('osm_file', type=click.Path())
def convert(kml_file, osm_file):
    """Convert KML to OSM file with air_defense_shelter amenity nodes."""
    nodes = parse_kml(kml_file)
    osm_content = build_osm(nodes)
    with open(osm_file, 'w', encoding='utf-8') as f:
        f.write(osm_content)
    click.echo(f"Converted {len(nodes)} placemarks to {osm_file}")


if __name__ == '__main__':
    convert()
