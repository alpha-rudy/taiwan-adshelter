#!/usr/bin/env python3
"""
ADS (Air Defense Shelter) Node Clustering Tool

This script generates clustered nodes for different zoom levels from the original 
NPA_Taiwan_ADShelter.osm file. It creates clusters suitable for zoom levels 16 and 15
from the original Z17 density data.

Zoom Level Guidelines:
- Z17: All individual nodes (original data) - suitable for detailed view
- Z16: Clustered for medium density view
- Z15: More heavily clustered for overview

Grid-based clustering approach:
- Z16: ~500m grid cells (approximately 1/2 the detail of Z17)
- Z15: ~1000m grid cells (approximately 1/4 the detail of Z17)
"""

import xml.etree.ElementTree as ET
import math
import argparse
import os
from collections import defaultdict
from typing import Dict, List, Tuple, NamedTuple


class Node(NamedTuple):
    """Represents an OSM node with its attributes."""
    id: str
    lat: float
    lon: float
    tags: Dict[str, str]


class Cluster(NamedTuple):
    """Represents a cluster of nodes."""
    center_lat: float
    center_lon: float
    node_count: int
    total_capacity: int
    nodes: List[Node]


def deg_to_meters_lat(lat_deg: float) -> float:
    """Convert latitude degrees to meters (approximately)."""
    return lat_deg * 111000  # 1 degree ≈ 111km


def deg_to_meters_lon(lon_deg: float, lat: float) -> float:
    """Convert longitude degrees to meters at given latitude."""
    return lon_deg * 111000 * math.cos(math.radians(lat))


def meters_to_deg_lat(meters: float) -> float:
    """Convert meters to latitude degrees."""
    return meters / 111000


def meters_to_deg_lon(meters: float, lat: float) -> float:
    """Convert meters to longitude degrees at given latitude."""
    return meters / (111000 * math.cos(math.radians(lat)))


def get_grid_cell(lat: float, lon: float, grid_size_meters: float, reference_lat: float) -> Tuple[int, int]:
    """
    Get grid cell coordinates for a given lat/lon.
    
    Args:
        lat: Latitude
        lon: Longitude
        grid_size_meters: Size of grid cells in meters
        reference_lat: Reference latitude for longitude conversion
    
    Returns:
        Tuple of (grid_x, grid_y) coordinates
    """
    # Convert to relative positions in meters from origin
    lat_meters = deg_to_meters_lat(lat - reference_lat)
    lon_meters = deg_to_meters_lon(lon, reference_lat)
    
    # Calculate grid cell
    grid_x = int(lon_meters // grid_size_meters)
    grid_y = int(lat_meters // grid_size_meters)
    
    return (grid_x, grid_y)


def parse_osm_file(filepath: str) -> List[Node]:
    """Parse OSM file and extract all nodes."""
    print(f"Parsing OSM file: {filepath}")
    
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    nodes = []
    for node_elem in root.findall('node'):
        node_id = node_elem.get('id')
        lat_str = node_elem.get('lat')
        lon_str = node_elem.get('lon')
        
        if not lat_str or not lon_str:
            continue
            
        try:
            lat = float(lat_str)
            lon = float(lon_str)
        except ValueError:
            continue
        
        # Extract tags
        tags = {}
        for tag_elem in node_elem.findall('tag'):
            key = tag_elem.get('k')
            value = tag_elem.get('v')
            if key and value:
                tags[key] = value
        
        nodes.append(Node(node_id, lat, lon, tags))
    
    print(f"Parsed {len(nodes)} nodes")
    return nodes


def cluster_nodes(nodes: List[Node], grid_size_meters: float) -> List[Cluster]:
    """
    Cluster nodes using a grid-based approach.
    
    Args:
        nodes: List of nodes to cluster
        grid_size_meters: Size of grid cells in meters
    
    Returns:
        List of clusters
    """
    if not nodes:
        return []
    
    # Calculate reference latitude (center of Taiwan approximately)
    lats = [node.lat for node in nodes]
    reference_lat = sum(lats) / len(lats)
    
    print(f"Clustering with grid size: {grid_size_meters}m (reference lat: {reference_lat:.6f})")
    
    # Group nodes by grid cell
    grid_cells = defaultdict(list)
    for node in nodes:
        grid_cell = get_grid_cell(node.lat, node.lon, grid_size_meters, reference_lat)
        grid_cells[grid_cell].append(node)
    
    # Create clusters
    clusters = []
    for (grid_x, grid_y), cell_nodes in grid_cells.items():
        if not cell_nodes:
            continue
        
        # Calculate cluster center (average position)
        center_lat = sum(node.lat for node in cell_nodes) / len(cell_nodes)
        center_lon = sum(node.lon for node in cell_nodes) / len(cell_nodes)
        
        # Calculate total capacity
        total_capacity = 0
        for node in cell_nodes:
            cap_str = node.tags.get('cap', '0')
            try:
                capacity = int(cap_str)
                total_capacity += capacity
            except ValueError:
                pass
        
        cluster = Cluster(
            center_lat=center_lat,
            center_lon=center_lon,
            node_count=len(cell_nodes),
            total_capacity=total_capacity,
            nodes=cell_nodes
        )
        clusters.append(cluster)
    
    print(f"Created {len(clusters)} clusters from {len(nodes)} nodes")
    return clusters


def generate_cluster_tags(cluster: Cluster, zoom_level: int) -> Dict[str, str]:
    """Generate tags for a cluster node."""
    tags = {
        'amenity': 'air_defense_shelter_cluster',
        'cluster:zoom_level': str(zoom_level),
        'cluster:node_count': str(cluster.node_count),
        'cluster:total_capacity': str(cluster.total_capacity),
        'name': f'ADS Cluster ({cluster.node_count} shelters, {cluster.total_capacity} capacity)'
    }
    
    # Add representative information from the largest shelter in the cluster
    if cluster.nodes:
        largest_node = max(cluster.nodes, key=lambda n: int(n.tags.get('cap', '0') or '0'))
        
        # Add some representative tags
        if '所在縣市' in largest_node.tags:
            tags['cluster:primary_city'] = largest_node.tags['所在縣市']
        if '轄管分局' in largest_node.tags:
            tags['cluster:primary_authority'] = largest_node.tags['轄管分局']
    
    return tags


def write_clustered_osm(clusters: List[Cluster], output_filepath: str, zoom_level: int):
    """Write clusters to an OSM file."""
    print(f"Writing {len(clusters)} clusters to: {output_filepath}")
    
    # Create OSM root element
    osm_elem = ET.Element('osm')
    osm_elem.set('version', '0.6')
    osm_elem.set('generator', f'ads-cluster-tool-z{zoom_level}')
    
    # Add clustered nodes
    for i, cluster in enumerate(clusters):
        node_elem = ET.SubElement(osm_elem, 'node')
        node_elem.set('id', str(-2000 - i))  # Use negative IDs starting from -2000
        node_elem.set('visible', 'true')
        node_elem.set('lat', f"{cluster.center_lat:.7f}")
        node_elem.set('lon', f"{cluster.center_lon:.7f}")
        
        # Add tags
        tags = generate_cluster_tags(cluster, zoom_level)
        for key, value in tags.items():
            tag_elem = ET.SubElement(node_elem, 'tag')
            tag_elem.set('k', key)
            tag_elem.set('v', value)
    
    # Write to file
    tree = ET.ElementTree(osm_elem)
    ET.indent(tree, space="  ", level=0)
    tree.write(output_filepath, encoding='utf-8', xml_declaration=True)
    print(f"Successfully wrote clustered OSM file: {output_filepath}")


def main():
    parser = argparse.ArgumentParser(description='Cluster ADS nodes for different zoom levels')
    parser.add_argument('input_file', help='Input OSM file path')
    parser.add_argument('--output-dir', default='build', help='Output directory for clustered files')
    parser.add_argument('--zoom-levels', nargs='+', type=int, default=[16, 15], 
                       help='Zoom levels to generate clusters for')
    parser.add_argument('--grid-sizes', nargs='+', type=float, 
                       help='Custom grid sizes in meters for each zoom level')
    
    args = parser.parse_args()
    
    # Default grid sizes for different zoom levels
    default_grid_sizes = {
        16: 500,   # 500m grid for Z16
        15: 1000,  # 1000m grid for Z15
        14: 2000,  # 2000m grid for Z14 (if needed)
        13: 4000   # 4000m grid for Z13 (if needed)
    }
    
    # Parse input file
    nodes = parse_osm_file(args.input_file)
    if not nodes:
        print("No nodes found in input file!")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate clusters for each zoom level
    for i, zoom_level in enumerate(args.zoom_levels):
        print(f"\n--- Processing Zoom Level {zoom_level} ---")
        
        # Determine grid size
        if args.grid_sizes and i < len(args.grid_sizes):
            grid_size = args.grid_sizes[i]
        else:
            grid_size = default_grid_sizes.get(zoom_level, 1000)
        
        # Generate clusters
        clusters = cluster_nodes(nodes, grid_size)
        
        if clusters:
            # Generate output filename
            base_name = os.path.splitext(os.path.basename(args.input_file))[0]
            output_filename = f"{base_name}_Z{zoom_level}.osm"
            output_filepath = os.path.join(args.output_dir, output_filename)
            
            # Write clustered OSM file
            write_clustered_osm(clusters, output_filepath, zoom_level)
            
            print(f"Z{zoom_level}: {len(clusters)} clusters (grid: {grid_size}m)")
        else:
            print(f"Z{zoom_level}: No clusters generated!")
    
    print("\nClustering completed!")


if __name__ == '__main__':
    main()
