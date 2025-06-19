#!/usr/bin/env python3

import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import click
import os
import re

OSM_HEADER = '''<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="kml2osm">'''

OSM_FOOTER = '</osm>'

def is_float(s):
    if not s:
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False

def parse_coordinates_from_point(placemark, ns):
    point = placemark.find(".//kml:Point/kml:coordinates", ns)
    if point is not None:
        lon, lat = point.text.strip().split(",")[:2]
        return lat, lon
    return None, None

def parse_addresss_from_point(placemark, ns):
    address_el = placemark.find("kml:address", ns)
    if address_el is not None and address_el.text:
        return address_el.text.strip(' \n\r')
    return None

def parse_coordinates_from_extended_data(extended_data):
    if "經度" in extended_data and "緯度" in extended_data and extended_data["經度"] and extended_data["緯度"]:
        lon = extended_data["經度"].strip("\n ,")
        lat = extended_data["緯度"].strip("\n ,")
        return lat, lon
    
    if "unnamed (6)" in extended_data and "unnamed (5)" in extended_data and extended_data["unnamed (6)"] and extended_data["unnamed (5)"] and is_float(extended_data["unnamed (6)"]) and is_float(extended_data["unnamed (5)"]):
        lon = extended_data["unnamed (6)"].strip("\n ,")
        lat = extended_data["unnamed (5)"].strip("\n ,")
        return lat, lon

    if "unnamed (8)" in extended_data and "unnamed (7)" in extended_data and extended_data["unnamed (8)"] and extended_data["unnamed (7)"] and is_float(extended_data["unnamed (8)"]) and is_float(extended_data["unnamed (7)"]):
        lon = extended_data["unnamed (8)"].strip("\n ,")
        lat = extended_data["unnamed (7)"].strip("\n ,")
        return lat, lon

    return None, None

def parse_address_from_extended_data(extended_data):
    if "地址" in extended_data and extended_data["地址"]:
        return extended_data["地址"].strip("\n ")

    return None

def parse_coordinates_from_description(description):
    if not description:
        return None, None

    match = re.search(r"緯經度[^\d]*([\d.]+),[^\d]*([\d.]+)[^\d]", description)
    if match:
        return match.group(1), match.group(2)

    lat_match = re.search(r"緯度[: ]*([\d.]+)", description)
    lon_match = re.search(r"經度[: ]*([\d.]+)", description)
    if lat_match and lon_match:
        return lat_match.group(1), lon_match.group(1)
    
    match = re.search(r"備註[^\d]*([\d.]+),[^\d]*([\d.]+)[^\d]", description)
    if match:
        return match.group(1), match.group(2)
    
    return None, None

def parse_address_from_description(description):
    if not description:
        return None

    address_match = re.search(r"地址[: ]*([^<\n]+)", description)
    if address_match:
        return address_match.group(1).strip(' \n')

    return None

def parse_lon_from_description(description):
    if not description:
        return None

    lon_match = re.search(r"經度[^\d]*([\d.]+)", description)
    if lon_match:
        return lon_match.group(1)

    return None

def extract_extended_data(placemark, ns):
    data = {}
    for data_el in placemark.findall(".//kml:ExtendedData/kml:Data", ns):
        key = data_el.attrib.get("name")
        value_el = data_el.find("kml:value", ns)
        if key and value_el is not None:
            data[key] = value_el.text
    return data

def build_node(lat, lon, name, extended_data):
    return {
        "lat": float(lat),
        "lon": float(lon),
        "tags": {
            "amenity": "air_defense_shelter",
            "name": name,
            "address": extended_data.get("地址", "").strip("\n "),
            "under_floor": extended_data.get("地下樓層數", "").strip("\n "),
            "capacity": extended_data.get("可容納人數", "").strip("\n "),
        },
    }

def parse_kml(kml_file):
    ns = {
        'kml': 'http://www.opengis.net/kml/2.2',
        'gx': 'http://www.google.com/kml/ext/2.2',
        'atom': 'http://www.w3.org/2005/Atom'
    }
    tree = ET.parse(kml_file)
    root = tree.getroot()
    placemarks = root.findall(".//kml:Placemark", ns)
    # show the number of placemarks found
    click.echo(f"Found {len(placemarks)} placemarks in {kml_file}")

    data = []

    for placemark in placemarks:
        name_el = placemark.find("kml:name", ns)
        name = name_el.text.strip(' \n') if name_el and name_el.text is not None else ""

        extended_data = extract_extended_data(placemark, ns)
        
        address = parse_addresss_from_point(placemark, ns) or parse_address_from_extended_data(extended_data) or parse_address_from_description(placemark.find("kml:description", ns).text if placemark.find("kml:description", ns) is not None else "DNF")

        lat, lon = parse_coordinates_from_point(placemark, ns)

        if lat is None or lon is None:
            lat, lon = parse_coordinates_from_extended_data(extended_data)

        if lat is None or lon is None:
            desc_el = placemark.find("kml:description", ns)
            description = desc_el.text if desc_el is not None else ""
            lat, lon = parse_coordinates_from_description(description)
        
        def friendly_name():
            return address or extended_data.get('電腦編號', None) or extended_data or name
        
        if lat is None or lon is None:
            if is_float(name):
                lat = name.strip()
            desc_el = placemark.find("kml:description", ns)
            description = desc_el.text if desc_el is not None else ""
            lon = parse_lon_from_description(description)

        if lat is None or lon is None:
            click.echo(f"Warning: no coordinates found for placemark '{friendly_name()}' in {kml_file}")
            continue

        try:
            node = build_node(lat, lon, name, extended_data)
            data.append(node)
        except ValueError as e:
            click.echo(f"Warning: ValueError on placemark '{extended_data.get('電腦編號', None) or extended_data or name}' in {kml_file}: {e}")

    click.echo(f"Extracted {len(data)} air defense shelter nodes from {kml_file}")
    return data


def build_osm(nodes):
    osm_body = []
    id_counter = -1000
    for node in nodes:
        lat = node['lat']
        lon = node['lon']
        tags = node['tags']
        
        # validate coordinates
        if not (21.8 <= lat <= 26.5) or not (118.2 <= lon <= 122.0):
            # switch lat and lon and try again
            if not (21.8 <= lon <= 26.5) or not (118.2 <= lat <= 122.0):
                click.echo(f"Warning: invalid coordinates: lat={lat}, lon={lon}, skipping the problematic node({tags['name']}/{tags['address']})")
                continue
            else:
                lat, lon = lon, lat
                click.echo(f"Switched coordinates: lat={lat}, lon={lon} for node({tags['name']}/{tags['address']})")

        escaped_tags = {k: escape(v) for k, v in tags.items() if v}

        osm_node = [f'<node id="{id_counter}" visible="true" lat="{lat}" lon="{lon}">']
        osm_node.extend([f'<tag k="{k}" v="{v}"/>' for k, v in escaped_tags.items()])
        osm_node.append('</node>')

        osm_body.append('\n'.join(osm_node))
        id_counter -= 1

    return f"{OSM_HEADER}\n{chr(10).join(osm_body)}\n{OSM_FOOTER}"


@click.command()
@click.argument('kml_dir', type=click.Path(exists=True, file_okay=False))
@click.argument('osm_file', type=click.Path())
def convert(kml_dir, osm_file):
    """Convert all KML files in a directory to a single OSM file with air_defense_shelter amenity nodes."""
    all_nodes = []
    for filename in os.listdir(kml_dir):
        if filename.lower().endswith('.kml'):
            filepath = os.path.join(kml_dir, filename)
            nodes = parse_kml(filepath)
            all_nodes.extend(nodes)
            click.echo(f"Parsed {len(nodes)} placemarks from {filename}")

    osm_content = build_osm(all_nodes)
    with open(osm_file, 'w', encoding='utf-8') as f:
        f.write(osm_content)
    click.echo(f"Converted total {len(all_nodes)} placemarks into {osm_file}")


if __name__ == '__main__':
    convert()
