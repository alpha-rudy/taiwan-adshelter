#!/usr/bin/env python3
"""
ADS Clustering Method Comparison Tool

This script compares the results of different clustering algorithms:
- Grid-based clustering
- HDBSCAN clustering  
- DBSCAN clustering

It provides comprehensive statistics and analysis to help choose the best method
for different use cases.
"""

import xml.etree.ElementTree as ET
import argparse
import os
from typing import Dict, List, NamedTuple
from collections import Counter


class ClusterAnalysis(NamedTuple):
    """Analysis results for a clustering method."""
    method: str
    zoom_level: int
    total_clusters: int
    single_node_clusters: int
    multi_node_clusters: int
    total_capacity: int
    compression_ratio: float
    size_distribution: Dict[int, int]
    avg_cluster_size: float
    max_cluster_size: int


def parse_osm_file(filepath: str) -> List[Dict]:
    """Parse OSM file and extract cluster information."""
    if not os.path.exists(filepath):
        return []
    
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    clusters = []
    for node_elem in root.findall('node'):
        tags = {}
        for tag_elem in node_elem.findall('tag'):
            key = tag_elem.get('k')
            value = tag_elem.get('v')
            if key and value:
                tags[key] = value
        
        # Extract cluster information
        if 'cluster:node_count' in tags:
            try:
                node_count = int(tags.get('cluster:node_count', '1'))
                total_capacity = int(tags.get('cluster:total_capacity', '0'))
                clusters.append({
                    'node_count': node_count,
                    'total_capacity': total_capacity,
                    'tags': tags
                })
            except ValueError:
                pass
        else:
            # Original individual node
            try:
                capacity = int(tags.get('cap', '0'))
                clusters.append({
                    'node_count': 1,
                    'total_capacity': capacity,
                    'tags': tags
                })
            except ValueError:
                pass
    
    return clusters


def analyze_clustering_method(clusters: List[Dict], method: str, zoom_level: int, 
                            original_node_count: int) -> ClusterAnalysis:
    """Analyze clustering results for a specific method."""
    
    if not clusters:
        return ClusterAnalysis(
            method=method,
            zoom_level=zoom_level,
            total_clusters=0,
            single_node_clusters=0,
            multi_node_clusters=0,
            total_capacity=0,
            compression_ratio=0,
            size_distribution={},
            avg_cluster_size=0,
            max_cluster_size=0
        )
    
    total_clusters = len(clusters)
    single_node_clusters = sum(1 for c in clusters if c['node_count'] == 1)
    multi_node_clusters = total_clusters - single_node_clusters
    total_capacity = sum(c['total_capacity'] for c in clusters)
    
    # Calculate compression ratio
    total_original_nodes = sum(c['node_count'] for c in clusters)
    compression_ratio = total_original_nodes / total_clusters if total_clusters > 0 else 0
    
    # Size distribution
    sizes = [c['node_count'] for c in clusters]
    size_distribution = dict(Counter(sizes))
    avg_cluster_size = sum(sizes) / len(sizes) if sizes else 0
    max_cluster_size = max(sizes) if sizes else 0
    
    return ClusterAnalysis(
        method=method,
        zoom_level=zoom_level,
        total_clusters=total_clusters,
        single_node_clusters=single_node_clusters,
        multi_node_clusters=multi_node_clusters,
        total_capacity=total_capacity,
        compression_ratio=compression_ratio,
        size_distribution=size_distribution,
        avg_cluster_size=avg_cluster_size,
        max_cluster_size=max_cluster_size
    )


def print_analysis_table(analyses: List[ClusterAnalysis], original_count: int):
    """Print a comparison table of all clustering methods."""
    
    print("=" * 120)
    print("ADS CLUSTERING METHOD COMPARISON")
    print("=" * 120)
    print()
    
    # Table header
    header = f"{'Method':<12} {'Zoom':<4} {'Clusters':<9} {'Single':<7} {'Multi':<6} {'Compression':<11} {'Avg Size':<8} {'Max Size':<8} {'Capacity':<10}"
    print(header)
    print("-" * len(header))
    
    # Original data row
    print(f"{'Original':<12} {'Z17':<4} {original_count:<9,} {original_count:<7,} {'0':<6} {'1.0:1':<11} {'1.0':<8} {'1':<8} {'N/A':<10}")
    
    # Clustering methods
    for analysis in analyses:
        compression_str = f"{analysis.compression_ratio:.1f}:1"
        capacity_str = f"{analysis.total_capacity:,}" if analysis.total_capacity > 0 else "N/A"
        
        print(f"{analysis.method:<12} Z{analysis.zoom_level:<3} {analysis.total_clusters:<9,} "
              f"{analysis.single_node_clusters:<7,} {analysis.multi_node_clusters:<6,} "
              f"{compression_str:<11} {analysis.avg_cluster_size:<8.1f} "
              f"{analysis.max_cluster_size:<8,} {capacity_str:<10}")
    
    print()


def print_detailed_analysis(analyses: List[ClusterAnalysis]):
    """Print detailed analysis for each clustering method."""
    
    for analysis in analyses:
        print(f"=== {analysis.method} Z{analysis.zoom_level} Detailed Analysis ===")
        print(f"Total clusters: {analysis.total_clusters:,}")
        print(f"Single-node clusters: {analysis.single_node_clusters:,} ({analysis.single_node_clusters/analysis.total_clusters*100:.1f}%)")
        print(f"Multi-node clusters: {analysis.multi_node_clusters:,} ({analysis.multi_node_clusters/analysis.total_clusters*100:.1f}%)")
        print(f"Compression ratio: {analysis.compression_ratio:.1f}:1")
        print(f"Average cluster size: {analysis.avg_cluster_size:.1f}")
        print(f"Maximum cluster size: {analysis.max_cluster_size:,}")
        print(f"Total capacity: {analysis.total_capacity:,}")
        
        # Size distribution (top 10)
        print("Top cluster sizes:")
        sorted_sizes = sorted(analysis.size_distribution.items(), key=lambda x: x[1], reverse=True)
        for size, count in sorted_sizes[:10]:
            percentage = count / analysis.total_clusters * 100
            print(f"  Size {size}: {count:,} clusters ({percentage:.1f}%)")
        
        print()


def generate_recommendations(analyses: List[ClusterAnalysis]):
    """Generate recommendations for different use cases."""
    
    print("=== CLUSTERING METHOD RECOMMENDATIONS ===")
    print()
    
    # Find best methods for different criteria
    z16_methods = [a for a in analyses if a.zoom_level == 16]
    z15_methods = [a for a in analyses if a.zoom_level == 15]
    
    print("📊 For Z16 (Medium Detail):")
    if z16_methods:
        # Best compression
        best_compression = max(z16_methods, key=lambda x: x.compression_ratio)
        print(f"  • Best compression: {best_compression.method} ({best_compression.compression_ratio:.1f}:1)")
        
        # Most natural clusters (highest ratio of multi-node clusters)
        best_natural = max(z16_methods, key=lambda x: x.multi_node_clusters / max(x.total_clusters, 1))
        natural_ratio = best_natural.multi_node_clusters / best_natural.total_clusters * 100
        print(f"  • Most natural clustering: {best_natural.method} ({natural_ratio:.1f}% multi-node clusters)")
        
        # Balanced approach
        print(f"  • Recommended: HDBSCAN or DBSCAN for natural geographic grouping")
    
    print()
    print("🗺️ For Z15 (Overview):")
    if z15_methods:
        # Best compression
        best_compression = max(z15_methods, key=lambda x: x.compression_ratio)
        print(f"  • Best compression: {best_compression.method} ({best_compression.compression_ratio:.1f}:1)")
        
        # Most natural clusters
        best_natural = max(z15_methods, key=lambda x: x.multi_node_clusters / max(x.total_clusters, 1))
        natural_ratio = best_natural.multi_node_clusters / best_natural.total_clusters * 100
        print(f"  • Most natural clustering: {best_natural.method} ({natural_ratio:.1f}% multi-node clusters)")
        
        print(f"  • Recommended: DBSCAN for large area overview with natural boundaries")
    
    print()
    print("🎯 Use Case Recommendations:")
    print("  • Web maps with smooth zooming: HDBSCAN (hierarchical, consistent)")
    print("  • Mobile apps with limited bandwidth: DBSCAN (best compression)")
    print("  • Administrative/planning use: Grid-based (predictable, regular)")
    print("  • Emergency response: HDBSCAN (respects geographic barriers)")
    print("  • Data analysis: DBSCAN (finds natural population centers)")
    print("  • Even distribution needed: K-means (balanced cluster sizes)")
    print("  • Performance critical: K-means (fast, predictable)")
    print()


def main():
    parser = argparse.ArgumentParser(description='Compare ADS clustering methods')
    parser.add_argument('original_file', help='Original OSM file path')
    parser.add_argument('--build-dir', default='build', help='Build directory with clustered files')
    parser.add_argument('--detailed', action='store_true', help='Show detailed analysis')
    
    args = parser.parse_args()
    
    print("ADS Clustering Method Comparison Tool")
    print("=" * 50)
    
    # Get original node count
    original_clusters = parse_osm_file(args.original_file)
    original_count = len(original_clusters)
    
    # Define files to analyze
    clustering_files = [
        # Grid-based
        (os.path.join(args.build_dir, 'NPA_Taiwan_ADShelter_Z16.osm'), 'Grid', 16),
        (os.path.join(args.build_dir, 'NPA_Taiwan_ADShelter_Z15.osm'), 'Grid', 15),
        # HDBSCAN
        (os.path.join(args.build_dir, 'NPA_Taiwan_ADShelter_HDBSCAN_Z16.osm'), 'HDBSCAN', 16),
        (os.path.join(args.build_dir, 'NPA_Taiwan_ADShelter_HDBSCAN_Z15.osm'), 'HDBSCAN', 15),
        # DBSCAN
        (os.path.join(args.build_dir, 'NPA_Taiwan_ADShelter_DBSCAN_Z16.osm'), 'DBSCAN', 16),
        (os.path.join(args.build_dir, 'NPA_Taiwan_ADShelter_DBSCAN_Z15.osm'), 'DBSCAN', 15),
        # K-means
        (os.path.join(args.build_dir, 'NPA_Taiwan_ADShelter_KMEANS_Z16.osm'), 'K-means', 16),
        (os.path.join(args.build_dir, 'NPA_Taiwan_ADShelter_KMEANS_Z15.osm'), 'K-means', 15),
    ]
    
    # Analyze each method
    analyses = []
    for filepath, method, zoom_level in clustering_files:
        clusters = parse_osm_file(filepath)
        if clusters:  # Only analyze if file exists
            analysis = analyze_clustering_method(clusters, method, zoom_level, original_count)
            analyses.append(analysis)
        else:
            print(f"File not found: {filepath}")
    
    if not analyses:
        print("No clustering files found to analyze!")
        return
    
    # Print comparison table
    print_analysis_table(analyses, original_count)
    
    # Print detailed analysis if requested
    if args.detailed:
        print_detailed_analysis(analyses)
    
    # Generate recommendations
    generate_recommendations(analyses)


if __name__ == '__main__':
    main()
