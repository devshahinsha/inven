#!/usr/bin/env python3
"""
Process Shopify product export CSV and generate Excel file with inventory cost summary.
Version 2: Simplified output with SKU, Total Quantity, Cost Price, Total Cost Price.

Usage:
    python process_inventory_v2.py input.csv [output.xlsx]
"""

import pandas as pd
import re
import sys
from pathlib import Path
from collections import defaultdict


def extract_base_sku(variant_sku):
    """
    Extract base SKU from variant SKU by removing the size suffix.
    
    Examples:
        'sku-1234-41' -> 'sku-1234'
        'sku-1234-black-41' -> 'sku-1234-black'
        '177525-LT_Brown-40' -> '177525-LT_Brown'
    
    Args:
        variant_sku: The variant SKU string
        
    Returns:
        str: Base SKU or None if extraction fails
    """
    if pd.isna(variant_sku) or not variant_sku or not isinstance(variant_sku, str):
        return None
    
    # Split by hyphen
    parts = variant_sku.split('-')
    
    if len(parts) < 2:
        return None
    
    # Get the last segment
    last_segment = parts[-1]
    
    # Check if last segment contains a number (likely a size)
    numeric_match = re.search(r'(\d+)', last_segment)
    if numeric_match:
        # Base SKU is everything except the last segment
        return '-'.join(parts[:-1])
    
    # If no numeric found, check if entire last segment is numeric
    if last_segment.isdigit():
        return '-'.join(parts[:-1])
    
    return None


def parse_numeric(value):
    """
    Parse a numeric value from string, handling various formats.
    
    Args:
        value: Value to parse (string, float, or int)
        
    Returns:
        float: Parsed numeric value or 0 if parsing fails
    """
    if pd.isna(value) or value == '' or value is None:
        return 0.0
    
    try:
        # Handle string with currency symbols or commas
        if isinstance(value, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r'[^\d.\-]', '', value)
            return float(cleaned) if cleaned else 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def process_inventory_csv_v2(input_file, output_file=None):
    """
    Process the Shopify CSV and generate Excel output with cost summary.
    
    Output columns: SKU, Total Quantity, Cost Price, Total Cost Price
    
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
        output_file = output_folder / f"{input_path.stem}_v2.xlsx"
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
    
    # Check for cost column
    cost_column = None
    possible_cost_columns = ['Cost per item', 'Variant Cost', 'Cost Price', 'Cost']
    for col in possible_cost_columns:
        if col in df.columns:
            cost_column = col
            break
    
    if cost_column is None:
        print("Warning: No cost column found. Using 0 for all cost values.")
        print(f"Looked for columns: {possible_cost_columns}")
    else:
        print(f"Using cost column: '{cost_column}'")
    
    print("Processing inventory data...")
    
    # Dictionary to store base SKU -> {total_qty, cost_price}
    inventory_data = defaultdict(lambda: {'total_qty': 0, 'cost_price': None})
    
    # Process each row
    for idx, row in df.iterrows():
        variant_sku = row['Variant SKU']
        inventory_qty_str = row['Variant Inventory Qty']
        
        # Extract base SKU
        base_sku = extract_base_sku(variant_sku)
        
        if base_sku is None:
            continue
        
        # Parse inventory quantity
        inventory_qty = parse_numeric(inventory_qty_str)
        
        # Parse cost price
        cost_price = 0.0
        if cost_column and cost_column in row:
            cost_price = parse_numeric(row[cost_column])
        
        # Accumulate inventory
        inventory_data[base_sku]['total_qty'] += inventory_qty
        
        # Use the first non-zero cost price found for this SKU
        if inventory_data[base_sku]['cost_price'] is None and cost_price > 0:
            inventory_data[base_sku]['cost_price'] = cost_price
    
    if not inventory_data:
        raise ValueError("No valid inventory data found. Check if Variant SKU format is correct.")
    
    print(f"Found {len(inventory_data)} unique base SKUs")
    
    # Build output DataFrame
    output_rows = []
    for base_sku in sorted(inventory_data.keys()):
        data = inventory_data[base_sku]
        total_qty = data['total_qty']
        cost_price = data['cost_price'] if data['cost_price'] is not None else 0.0
        total_cost_price = total_qty * cost_price
        
        output_rows.append({
            'SKU': base_sku,
            'Total Quantity': int(total_qty) if total_qty == int(total_qty) else total_qty,
            'Cost Price': round(cost_price, 2),
            'Total Cost Price': round(total_cost_price, 2)
        })
    
    # Create DataFrame
    output_df = pd.DataFrame(output_rows)
    
    # Sort by Total Cost Price in descending order
    output_df = output_df.sort_values('Total Cost Price', ascending=False).reset_index(drop=True)
    
    print(f"Writing output to: {output_file}")
    # Write to Excel
    try:
        output_df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"Successfully created Excel file with {len(output_df)} rows")
        
        # Print summary
        total_inventory = output_df['Total Quantity'].sum()
        total_cost = output_df['Total Cost Price'].sum()
        print(f"\nSummary:")
        print(f"  Total Products: {len(output_df)}")
        print(f"  Total Inventory: {int(total_inventory):,}")
        print(f"  Total Cost Value: ${total_cost:,.2f}")
    except Exception as e:
        raise ValueError(f"Error writing Excel file: {e}")


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python process_inventory_v2.py input.csv [output.xlsx]")
        print("\nInstructions:")
        print("  1. Place your Shopify export CSV file in the 'input' folder")
        print("  2. Run the script with the CSV filename")
        print("\nExamples:")
        print("  python process_inventory_v2.py products_export.csv")
        print("  python process_inventory_v2.py products_export.csv inventory.xlsx")
        print("\n  Output will be saved in the 'output' folder")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        process_inventory_csv_v2(input_file, output_file)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
