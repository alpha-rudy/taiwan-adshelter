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
    
def single_line(s):
    """Convert a string to a single line by removing newlines and excessive spaces."""
    if s is None:
        return None
    return ' '.join(s.split()).strip() if s else ''

def parse_coordinates_from_point(placemark, ns):
    point = placemark.find(".//kml:Point/kml:coordinates", ns)
    if point is not None:
        lon, lat = point.text.strip().split(",")[:2]
        return lat, lon
    return None, None

def parse_addresss_from_point(placemark, ns):
    address_el = placemark.find("kml:address", ns)
    if address_el is not None and address_el.text:
        return address_el.text.strip()
    return None

def parse_coordinates_from_extended_data(extended_data):
    if "經度" in extended_data and "緯度" in extended_data and extended_data["經度"] and extended_data["緯度"]:
        lon = extended_data["經度"].strip("\n ,")
        lat = extended_data["緯度"].strip("\n ,")
        return lat, lon
    
    if "unnamed (6)" in extended_data and "unnamed (5)" in extended_data and extended_data["unnamed (6)"] and extended_data["unnamed (5)"] and is_float(extended_data["unnamed (6)"]) and is_float(extended_data["unnamed (5)"]):
        lon = extended_data["unnamed (6)"].strip()
        lat = extended_data["unnamed (5)"].strip()
        return lat, lon

    if "unnamed (8)" in extended_data and "unnamed (7)" in extended_data and extended_data["unnamed (8)"] and extended_data["unnamed (7)"] and is_float(extended_data["unnamed (8)"]) and is_float(extended_data["unnamed (7)"]):
        lon = extended_data["unnamed (8)"].strip()
        lat = extended_data["unnamed (7)"].strip()
        return lat, lon

    if "地址" in extended_data and extended_data["地址"] is not None:
        coords = extended_data["地址"].strip("\n ,").split(",")
        if len(coords) == 2 and is_float(coords[0]) and is_float(coords[1]):
            return coords[0].strip(), coords[1].strip()

    return None, None

def parse_address_from_extended_data(extended_data):
    if "地址" in extended_data and extended_data["地址"]:
        return extended_data["地址"].strip()

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
    
    match = re.search(r"備註: ([\d.]+), ([\d.]+)", description)
    if match:
        return match.group(1), match.group(2)
    
    return None, None

def parse_address_from_description(description):
    if not description:
        return None

    address_match = re.search(r"地址[: ]*([^<\n]+)", description)
    if address_match:
        return address_match.group(1).strip()

    return None

def parse_lon_from_description(description):
    if not description:
        return None

    lon_match = re.search(r"經度[: ]*([\d.]+)[^\d]", description)
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

def safe_int(s):
    """Convert a string to an integer, returning None if conversion fails."""
    if s is None:
        return None
    try:
        s = s.replace(',', '').strip()
        s = s.replace('人', '').strip()
        return int(float(s))
    except (ValueError, TypeError):
        click.echo(f"Warning: could not convert '{s}' to int, returning None")
        return None

def build_node(lat, lon, name, address, extended_data):
    return {
        "lat": float(lat),
        "lon": float(lon),
        "tags": {
            "amenity": "air_defense_shelter",
            "name": single_line(name),
            "id": single_line(extended_data.get("電腦編號", None)),
            "address": single_line(address),
            "under_floor": single_line(extended_data.get("地下樓層數", None)),
            "capacity": safe_int(extended_data.get("可容納人數", None)),
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
        name = name_el.text.strip() if (name_el is not None and name_el.text is not None) else None

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
            node = build_node(lat, lon, name, address, extended_data)
            data.append(node)
        except ValueError as e:
            click.echo(f"Warning: ValueError on placemark '{extended_data.get('電腦編號', None) or extended_data or name}' in {kml_file}: {e}")

    click.echo(f"Extracted {len(data)} air defense shelter nodes from {kml_file}")
    return data

def extract_house_number(address: str) -> str:
    match = re.search(r'\d+號', address)
    return match.group() if match else ""

def build_osm(nodes, start_id=-1000):
    osm_body = []
    id_counter = start_id
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

        # create OSM node
        osm_node = [f'<node id="{id_counter}" visible="true" lat="{lat}" lon="{lon}">']
        # make mandatory amenity tag
        osm_node.append('<tag k="amenity" v="air_defense_shelter"/>')
        # make name tag as "id (capacity)"
        name = f"{tags.get('id', '')}"
        if tags.get('capacity'):
            name += f" ({tags['capacity']})"
        osm_node.append(f'<tag k="name" v="{escape(name)}"/>')
        # make zl tag depending on the capacity
        if tags.get('capacity'):
            if tags['capacity'] > 500:
                osm_node.append('<tag k="zl" v="0"/>')
            elif tags['capacity'] > 100:
                osm_node.append('<tag k="zl" v="1"/>')
            else:
                osm_node.append('<tag k="zl" v="2"/>')
        else:
            osm_node.append('<tag k="zl" v="2"/>')
        # make ref as address
        if tags.get('address'):
            osm_node.append(f'<tag k="ref" v="{escape(extract_house_number(tags["address"]))}"/>')
        osm_node.append('</node>')

        osm_body.append('\n'.join(osm_node))
        id_counter -= 1

    return f"{OSM_HEADER}\n{chr(10).join(osm_body)}\n{OSM_FOOTER}"


@click.command()
@click.argument('kml_dir', type=click.Path(exists=True, file_okay=False))
@click.argument('osm_file', type=click.Path())
@click.option('--start-id', default=-1000, help='Starting ID for OSM nodes (default: -1000)')
def convert(kml_dir, osm_file, start_id):
    """Convert all KML files in a directory to a single OSM file with air_defense_shelter amenity nodes."""
    all_nodes = []
    for filename in os.listdir(kml_dir):
        if filename.lower().endswith('.kml'):
            filepath = os.path.join(kml_dir, filename)
            nodes = parse_kml(filepath)
            all_nodes.extend(nodes)
            click.echo(f"Parsed {len(nodes)} placemarks from {filename}")

    osm_content = build_osm(all_nodes, start_id)
    with open(osm_file, 'w', encoding='utf-8') as f:
        f.write(osm_content)
    click.echo(f"Converted total {len(all_nodes)} placemarks into {osm_file}")


if __name__ == '__main__':
    convert()
