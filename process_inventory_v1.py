#!/usr/bin/env python3
"""
Process Shopify product export CSV and generate Excel file with inventory data
grouped by base SKU and size variants.

Usage:
    python process_inventory.py input.csv [output.xlsx]
"""

import pandas as pd
import re
import sys
from pathlib import Path
from collections import defaultdict


def get_us_to_eu_size_conversion():
    """
    Return a mapping of US shoe sizes to EU shoe sizes.
    This is a standard conversion table for men's/women's shoes.
    """
    # US to EU conversion (approximate, works for most standard sizes)
    # Format: US_size: EU_size
    return {
        5: 38, 5.5: 38.5,
        6: 39, 6.5: 39.5,
        7: 40, 7.5: 40.5,
        8: 41, 8.5: 41.5,
        9: 42, 9.5: 42.5,
        10: 43, 10.5: 43.5,
        11: 44, 11.5: 44.5,
        12: 45, 12.5: 45.5,
        13: 46, 13.5: 46.5,
        14: 47, 14.5: 47.5,
        15: 48, 15.5: 48.5,
    }


def is_eu_size(size_str):
    """
    Determine if a size string represents an EU size.
    EU shoe sizes are typically in the 35-50 range for standard sizes.
    
    Args:
        size_str: Size string to check
        
    Returns:
        bool: True if likely EU size, False otherwise
    """
    try:
        size_num = float(size_str)
        # EU shoe sizes typically range from 35-50
        return 35 <= size_num <= 50
    except (ValueError, TypeError):
        return False


def is_us_size(size_str):
    """
    Determine if a size string represents a US size.
    US shoe sizes are typically in the 5-15 range for standard sizes.
    
    Args:
        size_str: Size string to check
        
    Returns:
        bool: True if likely US size, False otherwise
    """
    try:
        size_num = float(size_str)
        # US shoe sizes typically range from 5-15
        return 5 <= size_num <= 15
    except (ValueError, TypeError):
        return False


def get_equivalent_eu_size(us_size_str):
    """
    Convert US size to equivalent EU size.
    
    Args:
        us_size_str: US size as string
        
    Returns:
        str: Equivalent EU size as string, or None if no conversion found
    """
    try:
        us_size = float(us_size_str)
        conversion = get_us_to_eu_size_conversion()
        
        # Check exact match first
        if us_size in conversion:
            return str(conversion[us_size])
        
        # Check for close matches (within 0.1)
        for us_key, eu_val in conversion.items():
            if abs(us_size - us_key) < 0.1:
                return str(eu_val)
        
        return None
    except (ValueError, TypeError):
        return None


def consolidate_eu_us_sizes(inventory_data):
    """
    Consolidate duplicate sizes that represent the same physical size in EU and US.
    Merges US size inventory into equivalent EU sizes and removes US size entries.
    
    Args:
        inventory_data: Dictionary of base_sku -> {size: inventory}
        
    Returns:
        tuple: (updated_inventory_data, removed_sizes_set)
    """
    consolidated_data = defaultdict(dict)
    removed_sizes = set()
    all_sizes_seen = set()
    
    # First pass: collect all sizes for each base SKU
    for base_sku, sizes_dict in inventory_data.items():
        all_sizes_seen.update(sizes_dict.keys())
    
    # Build a mapping of US sizes to EU sizes that exist in the data
    us_to_eu_map = {}
    eu_sizes = {s for s in all_sizes_seen if is_eu_size(s)}
    us_sizes = {s for s in all_sizes_seen if is_us_size(s)}
    
    # Find equivalent pairs (only if both US and EU sizes exist in the data)
    for us_size_str in us_sizes:
        equivalent_eu = get_equivalent_eu_size(us_size_str)
        if equivalent_eu and equivalent_eu in eu_sizes:
            us_to_eu_map[us_size_str] = equivalent_eu
    
    # Second pass: consolidate inventory for each base SKU
    for base_sku, sizes_dict in inventory_data.items():
        # Track which sizes we've already processed for this base SKU
        processed_sizes = set()
        
        for size, inventory in sizes_dict.items():
            # Skip if already processed (e.g., if we merged it into another size)
            if size in processed_sizes:
                continue
            
            # If this is a US size with an equivalent EU size, merge into EU
            if size in us_to_eu_map:
                eu_size = us_to_eu_map[size]
                # Get EU inventory (if it exists) and US inventory, sum them
                eu_inventory = sizes_dict.get(eu_size, 0)
                us_inventory = inventory
                total_inventory = eu_inventory + us_inventory
                
                consolidated_data[base_sku][eu_size] = total_inventory
                removed_sizes.add(size)
                processed_sizes.add(size)
                processed_sizes.add(eu_size)  # Mark EU size as processed too
            else:
                # Check if this EU size has a corresponding US size that will be merged
                # (i.e., is there a US size that maps to this EU size?)
                has_corresponding_us = any(
                    eu == size for us, eu in us_to_eu_map.items() 
                    if us in sizes_dict
                )
                
                if has_corresponding_us:
                    # This EU size will be handled when we process the US size, skip for now
                    # (it will be processed when we encounter the matching US size)
                    pass  # Will be handled when US size is processed
                else:
                    # Keep EU sizes and other sizes as-is (no corresponding US size)
                    consolidated_data[base_sku][size] = inventory
                    processed_sizes.add(size)
    
    return consolidated_data, removed_sizes


def extract_base_sku_and_size(variant_sku):
    """
    Extract base SKU and size from variant SKU.
    
    Pattern: Remove the last segment (size) from Variant SKU
    Examples:
        'sku-1234-41' -> ('sku-1234', '41')
        'sku-1234-black-41' -> ('sku-1234-black', '41')
        '177525-LT_Brown-40' -> ('177525-LT_Brown', '40')
        'KF040033-Coffee-40_AN_AN' -> ('KF040033-Coffee', '40')  # Extract numeric part
    
    Args:
        variant_sku: The variant SKU string
        
    Returns:
        tuple: (base_sku, size) or (None, None) if extraction fails
    """
    if pd.isna(variant_sku) or not variant_sku or not isinstance(variant_sku, str):
        return None, None
    
    # Split by hyphen
    parts = variant_sku.split('-')
    
    if len(parts) < 2:
        return None, None
    
    # Get the last segment
    last_segment = parts[-1]
    
    # Try to extract numeric part from the last segment
    # Handle cases like '40_AN_AN' -> extract '40'
    numeric_match = re.search(r'(\d+)', last_segment)
    if numeric_match:
        size = numeric_match.group(1)
        # Base SKU is everything except the last segment
        base_sku = '-'.join(parts[:-1])
        return base_sku, size
    
    # If no numeric found in last segment, check if entire last segment is numeric
    if last_segment.isdigit():
        size = last_segment
        base_sku = '-'.join(parts[:-1])
        return base_sku, size
    
    return None, None


def process_inventory_csv(input_file, output_file=None):
    """
    Process the Shopify CSV and generate Excel output with pivoted inventory data.
    
    Args:
        input_file: Path to input CSV file (if just filename, will look in 'input' folder)
        output_file: Path to output Excel file (optional, defaults to input_file with .xlsx extension)
    """
    # Handle input file path - if just filename, look in input folder
    input_path = Path(input_file)
    if not input_path.is_absolute() and input_path.parent == Path('.'):
        # Just a filename, check in input folder
        input_folder = Path('input')
        input_folder.mkdir(exist_ok=True)
        input_path = input_folder / input_path.name
    
    # Validate input file
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Create output folder if it doesn't exist
    output_folder = Path('output')
    output_folder.mkdir(exist_ok=True)
    
    # Set default output file name if not provided
    if output_file is None:
        output_file = output_folder / input_path.with_suffix('.xlsx').name
    else:
        output_file = Path(output_file)
        # If output_file is just a filename, put it in output folder
        if not output_file.is_absolute() and output_file.parent == Path('.'):
            output_file = output_folder / output_file.name
    
    print(f"Reading CSV file: {input_path}")
    # Read CSV file
    try:
        df = pd.read_csv(input_path, dtype=str, keep_default_na=False)
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")
    
    # Validate required columns
    required_columns = ['Variant SKU', 'Variant Inventory Qty']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Required columns missing: {missing_columns}")
    
    print("Processing inventory data...")
    
    # Dictionary to store base SKU -> {size: inventory}
    inventory_data = defaultdict(dict)
    all_sizes = set()
    
    # Process each row
    for idx, row in df.iterrows():
        variant_sku = row['Variant SKU']
        inventory_qty_str = row['Variant Inventory Qty']
        
        # Extract base SKU and size
        base_sku, size = extract_base_sku_and_size(variant_sku)
        
        if base_sku is None or size is None:
            # Skip rows where we can't extract base SKU and size
            continue
        
        # Parse inventory quantity
        try:
            # Try to convert to int/float
            inventory_qty = float(inventory_qty_str) if inventory_qty_str else 0
            inventory_qty = int(inventory_qty) if inventory_qty == int(inventory_qty) else inventory_qty
        except (ValueError, TypeError):
            inventory_qty = 0
        
        # Store inventory data
        inventory_data[base_sku][size] = inventory_qty
        all_sizes.add(size)
    
    if not inventory_data:
        raise ValueError("No valid inventory data found. Check if Variant SKU format is correct.")
    
    # Consolidate EU/US duplicate sizes
    print("Consolidating EU/US duplicate sizes...")
    inventory_data, removed_sizes = consolidate_eu_us_sizes(inventory_data)
    
    if removed_sizes:
        print(f"Removed US sizes (merged into EU equivalents): {sorted(removed_sizes)}")
        # Remove US sizes from all_sizes set
        all_sizes = all_sizes - removed_sizes
    
    # Sort sizes numerically
    try:
        sorted_sizes = sorted(all_sizes, key=lambda x: float(x) if '.' in str(x) else int(x))
    except ValueError:
        # If sizes can't be converted to int/float, sort alphabetically
        sorted_sizes = sorted(all_sizes)
    
    print(f"Found {len(inventory_data)} unique base SKUs")
    print(f"Found sizes (after consolidation): {sorted_sizes}")
    
    # Build output DataFrame
    output_rows = []
    for base_sku in sorted(inventory_data.keys()):
        row_data = {'SKU': base_sku}
        
        # Add inventory for each size
        total_inventory = 0
        for size in sorted_sizes:
            inventory = inventory_data[base_sku].get(size, None)
            if inventory is not None:
                row_data[size] = inventory
                total_inventory += inventory
            else:
                row_data[size] = None  # Empty cell for missing sizes
        
        # Add total column
        row_data['Total'] = total_inventory
        output_rows.append(row_data)
    
    # Create DataFrame
    output_df = pd.DataFrame(output_rows)
    
    # Reorder columns: SKU, sizes (sorted), Total
    column_order = ['SKU'] + sorted_sizes + ['Total']
    output_df = output_df[column_order]
    
    # Sort by Total column in descending order (highest first)
    output_df = output_df.sort_values('Total', ascending=False).reset_index(drop=True)
    
    print(f"Writing output to: {output_file}")
    # Write to Excel
    try:
        output_df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"Successfully created Excel file with {len(output_df)} rows")
    except Exception as e:
        raise ValueError(f"Error writing Excel file: {e}")


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python process_inventory.py input.csv [output.xlsx]")
        print("\nInstructions:")
        print("  1. Place your Shopify export CSV file in the 'input' folder")
        print("  2. Run the script with the CSV filename")
        print("\nExamples:")
        print("  python process_inventory.py products_export.csv")
        print("  python process_inventory.py products_export.csv inventory.xlsx")
        print("\n  Output will be saved in the 'output' folder")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        process_inventory_csv(input_file, output_file)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

