#!/usr/bin/env python3
"""
ADS Clustering Validation Tool

This script validates the quality and correctness of clustered ADS nodes by performing
various checks including data integrity, geographic distribution, capacity conservation,
and clustering quality metrics.
"""

import xml.etree.ElementTree as ET
import math
import argparse
import os
from typing import Dict, List, Tuple, NamedTuple
from collections import defaultdict, Counter

# Optional imports for advanced validation
try:
    import numpy as np
    import matplotlib.pyplot as plt
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False


class ValidationNode(NamedTuple):
    """Represents a node for validation."""
    id: str
    lat: float
    lon: float
    tags: Dict[str, str]


class ClusterStats(NamedTuple):
    """Statistics for a cluster."""
    node_count: int
    total_capacity: int
    avg_capacity: float
    center_lat: float
    center_lon: float
    is_cluster: bool


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in meters."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return c * 6371000  # Earth's radius in meters


def parse_osm_file(filepath: str) -> List[ValidationNode]:
    """Parse OSM file and extract all nodes."""
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
        
        tags = {}
        for tag_elem in node_elem.findall('tag'):
            key = tag_elem.get('k')
            value = tag_elem.get('v')
            if key and value:
                tags[key] = value
        
        nodes.append(ValidationNode(node_id, lat, lon, tags))
    
    return nodes


def validate_data_integrity(nodes: List[ValidationNode], file_type: str) -> Dict:
    """Validate basic data integrity."""
    print(f"\n=== Data Integrity Validation ({file_type}) ===")
    
    results = {
        'total_nodes': len(nodes),
        'valid_coordinates': 0,
        'missing_tags': 0,
        'capacity_issues': 0,
        'coordinate_range': {}
    }
    
    lats, lons, capacities = [], [], []
    
    for node in nodes:
        # Check coordinates
        if -90 <= node.lat <= 90 and -180 <= node.lon <= 180:
            results['valid_coordinates'] += 1
            lats.append(node.lat)
            lons.append(node.lon)
        
        # Check required tags
        if file_type == 'cluster':
            required_tags = ['amenity', 'cluster:node_count', 'cluster:total_capacity']
            if not all(tag in node.tags for tag in required_tags):
                results['missing_tags'] += 1
        
        # Check capacity
        if file_type == 'cluster':
            try:
                capacity = int(node.tags.get('cluster:total_capacity', '0'))
                if capacity <= 0:
                    results['capacity_issues'] += 1
                capacities.append(capacity)
            except ValueError:
                results['capacity_issues'] += 1
        else:
            try:
                capacity = int(node.tags.get('cap', '0'))
                capacities.append(capacity)
            except ValueError:
                pass
    
    if lats and lons:
        results['coordinate_range'] = {
            'lat_min': min(lats), 'lat_max': max(lats),
            'lon_min': min(lons), 'lon_max': max(lons)
        }
    
    # Print results
    print(f"Total nodes: {results['total_nodes']:,}")
    print(f"Valid coordinates: {results['valid_coordinates']:,} ({results['valid_coordinates']/results['total_nodes']*100:.1f}%)")
    print(f"Missing required tags: {results['missing_tags']:,}")
    print(f"Capacity issues: {results['capacity_issues']:,}")
    
    if capacities:
        print(f"Capacity stats: min={min(capacities):,}, max={max(capacities):,}, avg={sum(capacities)/len(capacities):.0f}")
    
    if results['coordinate_range']:
        cr = results['coordinate_range']
        print(f"Coordinate range: lat [{cr['lat_min']:.6f}, {cr['lat_max']:.6f}], lon [{cr['lon_min']:.6f}, {cr['lon_max']:.6f}]")
    
    return results


def validate_capacity_conservation(original_nodes: List[ValidationNode], 
                                 clustered_nodes: List[ValidationNode]) -> Dict:
    """Validate that total capacity is conserved during clustering."""
    print(f"\n=== Capacity Conservation Validation ===")
    
    # Calculate original total capacity
    original_capacity = 0
    for node in original_nodes:
        try:
            capacity = int(node.tags.get('cap', '0'))
            original_capacity += capacity
        except ValueError:
            pass
    
    # Calculate clustered total capacity
    clustered_capacity = 0
    for node in clustered_nodes:
        try:
            capacity = int(node.tags.get('cluster:total_capacity', '0'))
            clustered_capacity += capacity
        except ValueError:
            pass
    
    difference = abs(original_capacity - clustered_capacity)
    conservation_rate = (min(original_capacity, clustered_capacity) / max(original_capacity, clustered_capacity) * 100) if max(original_capacity, clustered_capacity) > 0 else 0
    
    print(f"Original total capacity: {original_capacity:,}")
    print(f"Clustered total capacity: {clustered_capacity:,}")
    print(f"Difference: {difference:,}")
    print(f"Conservation rate: {conservation_rate:.2f}%")
    
    return {
        'original_capacity': original_capacity,
        'clustered_capacity': clustered_capacity,
        'difference': difference,
        'conservation_rate': conservation_rate
    }


def validate_geographic_distribution(nodes: List[ValidationNode], zoom_level: int) -> Dict:
    """Validate geographic distribution and clustering quality."""
    print(f"\n=== Geographic Distribution Validation (Z{zoom_level}) ===")
    
    if not nodes:
        return {}
    
    # Calculate center point
    center_lat = sum(node.lat for node in nodes) / len(nodes)
    center_lon = sum(node.lon for node in nodes) / len(nodes)
    
    # Calculate distances from center
    distances = []
    for node in nodes:
        distance = haversine_distance(center_lat, center_lon, node.lat, node.lon)
        distances.append(distance)
    
    # Find nearest neighbor distances
    nn_distances = []
    for i, node1 in enumerate(nodes):
        min_dist = float('inf')
        for j, node2 in enumerate(nodes):
            if i != j:
                dist = haversine_distance(node1.lat, node1.lon, node2.lat, node2.lon)
                min_dist = min(min_dist, dist)
        if min_dist != float('inf'):
            nn_distances.append(min_dist)
    
    # Calculate coverage area (rough estimate)
    if len(nodes) > 2:
        lat_span = max(node.lat for node in nodes) - min(node.lat for node in nodes)
        lon_span = max(node.lon for node in nodes) - min(node.lon for node in nodes)
        # Convert to approximate area in km²
        lat_km = lat_span * 111
        lon_km = lon_span * 111 * math.cos(math.radians(center_lat))
        coverage_area = lat_km * lon_km
    else:
        coverage_area = 0
    
    # Density calculation
    density = len(nodes) / max(coverage_area, 1)  # nodes per km²
    
    results = {
        'center_lat': center_lat,
        'center_lon': center_lon,
        'coverage_area_km2': coverage_area,
        'density_per_km2': density,
        'distances_from_center': {
            'min': min(distances) if distances else 0,
            'max': max(distances) if distances else 0,
            'avg': sum(distances) / len(distances) if distances else 0
        },
        'nearest_neighbor': {
            'min': min(nn_distances) if nn_distances else 0,
            'max': max(nn_distances) if nn_distances else 0,
            'avg': sum(nn_distances) / len(nn_distances) if nn_distances else 0
        }
    }
    
    print(f"Geographic center: {center_lat:.6f}, {center_lon:.6f}")
    print(f"Coverage area: {coverage_area:.1f} km²")
    print(f"Node density: {density:.2f} nodes/km²")
    print(f"Distance from center: min={results['distances_from_center']['min']:.0f}m, "
          f"max={results['distances_from_center']['max']:.0f}m, "
          f"avg={results['distances_from_center']['avg']:.0f}m")
    print(f"Nearest neighbor: min={results['nearest_neighbor']['min']:.0f}m, "
          f"max={results['nearest_neighbor']['max']:.0f}m, "
          f"avg={results['nearest_neighbor']['avg']:.0f}m")
    
    return results


def validate_cluster_quality(clustered_nodes: List[ValidationNode]) -> Dict:
    """Validate clustering quality metrics."""
    print(f"\n=== Cluster Quality Validation ===")
    
    cluster_sizes = []
    cluster_capacities = []
    single_node_clusters = 0
    multi_node_clusters = 0
    
    for node in clustered_nodes:
        try:
            node_count = int(node.tags.get('cluster:node_count', '1'))
            capacity = int(node.tags.get('cluster:total_capacity', '0'))
            
            cluster_sizes.append(node_count)
            cluster_capacities.append(capacity)
            
            if node_count == 1:
                single_node_clusters += 1
            else:
                multi_node_clusters += 1
                
        except ValueError:
            pass
    
    # Calculate statistics
    if cluster_sizes:
        size_stats = {
            'min': min(cluster_sizes),
            'max': max(cluster_sizes),
            'avg': sum(cluster_sizes) / len(cluster_sizes),
            'median': sorted(cluster_sizes)[len(cluster_sizes)//2]
        }
    else:
        size_stats = {'min': 0, 'max': 0, 'avg': 0, 'median': 0}
    
    if cluster_capacities:
        capacity_stats = {
            'min': min(cluster_capacities),
            'max': max(cluster_capacities),
            'avg': sum(cluster_capacities) / len(cluster_capacities)
        }
    else:
        capacity_stats = {'min': 0, 'max': 0, 'avg': 0}
    
    # Size distribution
    size_distribution = Counter(cluster_sizes)
    
    results = {
        'total_clusters': len(clustered_nodes),
        'single_node_clusters': single_node_clusters,
        'multi_node_clusters': multi_node_clusters,
        'size_stats': size_stats,
        'capacity_stats': capacity_stats,
        'size_distribution': dict(size_distribution)
    }
    
    print(f"Total clusters: {results['total_clusters']:,}")
    print(f"Single-node clusters: {single_node_clusters:,} ({single_node_clusters/len(clustered_nodes)*100:.1f}%)")
    print(f"Multi-node clusters: {multi_node_clusters:,} ({multi_node_clusters/len(clustered_nodes)*100:.1f}%)")
    print(f"Cluster size: min={size_stats['min']}, max={size_stats['max']}, avg={size_stats['avg']:.1f}, median={size_stats['median']}")
    print(f"Cluster capacity: min={capacity_stats['min']:,}, max={capacity_stats['max']:,}, avg={capacity_stats['avg']:.0f}")
    
    # Show size distribution
    print("Cluster size distribution:")
    for size, count in sorted(size_distribution.items()):
        percentage = count / len(clustered_nodes) * 100
        print(f"  Size {size}: {count:,} clusters ({percentage:.1f}%)")
    
    return results


def compare_zoom_levels(z16_nodes: List[ValidationNode], z15_nodes: List[ValidationNode]) -> Dict:
    """Compare clustering results between zoom levels."""
    print(f"\n=== Zoom Level Comparison ===")
    
    z16_count = len(z16_nodes)
    z15_count = len(z15_nodes)
    
    compression_ratio = z16_count / z15_count if z15_count > 0 else 0
    
    print(f"Z16 clusters: {z16_count:,}")
    print(f"Z15 clusters: {z15_count:,}")
    print(f"Z16→Z15 compression: {compression_ratio:.1f}:1")
    
    return {
        'z16_count': z16_count,
        'z15_count': z15_count,
        'compression_ratio': compression_ratio
    }


def generate_validation_report(results: Dict, output_file: str):
    """Generate a comprehensive validation report."""
    print(f"\n=== Generating Validation Report ===")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# ADS Clustering Validation Report\n\n")
        f.write(f"Generated on: {os.popen('date').read().strip()}\n\n")
        
        # Write all validation results
        for section, data in results.items():
            f.write(f"## {section.replace('_', ' ').title()}\n\n")
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict):
                        f.write(f"### {key.replace('_', ' ').title()}\n")
                        for subkey, subvalue in value.items():
                            f.write(f"- {subkey}: {subvalue}\n")
                        f.write("\n")
                    else:
                        f.write(f"- {key}: {value}\n")
            f.write("\n")
    
    print(f"Validation report saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Validate ADS clustering results')
    parser.add_argument('original_file', help='Original OSM file path')
    parser.add_argument('--z16-file', help='Z16 clustered file path')
    parser.add_argument('--z15-file', help='Z15 clustered file path')
    parser.add_argument('--output-report', default='validation_report.md', 
                       help='Output validation report file')
    
    args = parser.parse_args()
    
    print("=== ADS Clustering Validation Tool ===")
    
    # Parse original file
    print(f"\nParsing original file: {args.original_file}")
    original_nodes = parse_osm_file(args.original_file)
    
    validation_results = {}
    
    # Validate original data
    validation_results['original_data'] = validate_data_integrity(original_nodes, 'original')
    validation_results['original_distribution'] = validate_geographic_distribution(original_nodes, 17)
    
    z16_nodes, z15_nodes = None, None
    
    # Validate Z16 if provided
    if args.z16_file and os.path.exists(args.z16_file):
        print(f"\nParsing Z16 file: {args.z16_file}")
        z16_nodes = parse_osm_file(args.z16_file)
        validation_results['z16_data'] = validate_data_integrity(z16_nodes, 'cluster')
        validation_results['z16_distribution'] = validate_geographic_distribution(z16_nodes, 16)
        validation_results['z16_quality'] = validate_cluster_quality(z16_nodes)
        validation_results['z16_conservation'] = validate_capacity_conservation(original_nodes, z16_nodes)
    
    # Validate Z15 if provided
    if args.z15_file and os.path.exists(args.z15_file):
        print(f"\nParsing Z15 file: {args.z15_file}")
        z15_nodes = parse_osm_file(args.z15_file)
        validation_results['z15_data'] = validate_data_integrity(z15_nodes, 'cluster')
        validation_results['z15_distribution'] = validate_geographic_distribution(z15_nodes, 15)
        validation_results['z15_quality'] = validate_cluster_quality(z15_nodes)
        validation_results['z15_conservation'] = validate_capacity_conservation(original_nodes, z15_nodes)
    
    # Compare zoom levels
    if z16_nodes and z15_nodes:
        validation_results['zoom_comparison'] = compare_zoom_levels(z16_nodes, z15_nodes)
    
    # Generate report
    generate_validation_report(validation_results, args.output_report)
    
    print("\n=== Validation Summary ===")
    if 'z16_conservation' in validation_results:
        print(f"Z16 capacity conservation: {validation_results['z16_conservation']['conservation_rate']:.2f}%")
    if 'z15_conservation' in validation_results:
        print(f"Z15 capacity conservation: {validation_results['z15_conservation']['conservation_rate']:.2f}%")
    
    print("\n✓ Validation completed successfully!")


if __name__ == '__main__':
    main()
