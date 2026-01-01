#!/usr/bin/env python3
"""
Streamlit web app for processing Shopify inventory CSV files.
Upload a CSV file and download the processed Excel output.
"""

import streamlit as st
import pandas as pd
import re
from collections import defaultdict
from io import BytesIO

# Import processing functions from process_inventory
from process_inventory import (
    extract_base_sku_and_size,
    get_us_to_eu_size_conversion,
    is_eu_size,
    is_us_size,
    get_equivalent_eu_size,
    consolidate_eu_us_sizes
)


def process_inventory_dataframe(df):
    """
    Process the DataFrame and return processed output DataFrame.
    
    Args:
        df: Input DataFrame with 'Variant SKU' and 'Variant Inventory Qty' columns
        
    Returns:
        DataFrame: Processed inventory data with consolidated sizes
    """
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
    inventory_data, removed_sizes = consolidate_eu_us_sizes(inventory_data)
    
    if removed_sizes:
        st.info(f"Removed US sizes (merged into EU equivalents): {sorted(removed_sizes)}")
        # Remove US sizes from all_sizes set
        all_sizes = all_sizes - removed_sizes
    
    # Sort sizes numerically
    try:
        sorted_sizes = sorted(all_sizes, key=lambda x: float(x) if '.' in str(x) else int(x))
    except ValueError:
        # If sizes can't be converted to int/float, sort alphabetically
        sorted_sizes = sorted(all_sizes)
    
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
    
    return output_df


def to_excel_bytes(df):
    """
    Convert DataFrame to Excel file in memory.
    
    Args:
        df: DataFrame to convert
        
    Returns:
        bytes: Excel file as bytes
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    output.seek(0)
    return output.getvalue()


# Streamlit UI
st.set_page_config(
    page_title="Inventory Processor",
    page_icon="📦",
    layout="centered"
)

st.title("📦 Inventory Processor")
st.markdown("Process Shopify product export CSV files and generate Excel output with consolidated EU/US sizes.")

# File upload
uploaded_file = st.file_uploader(
    "Upload CSV file",
    type=['csv'],
    help="Upload a Shopify export CSV file with 'Variant SKU' and 'Variant Inventory Qty' columns"
)

if uploaded_file is not None:
    try:
        # Read CSV file
        with st.spinner("Reading CSV file..."):
            df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
        
        # Validate required columns
        required_columns = ['Variant SKU', 'Variant Inventory Qty']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"❌ Required columns missing: {missing_columns}")
            st.info("Please ensure your CSV file contains 'Variant SKU' and 'Variant Inventory Qty' columns.")
        else:
            # Show preview
            st.success(f"✅ File loaded successfully! ({len(df)} rows)")
            
            with st.expander("Preview CSV data"):
                st.dataframe(df.head(10))
            
            # Process the data
            if st.button("Process Inventory", type="primary"):
                with st.spinner("Processing inventory data..."):
                    try:
                        output_df = process_inventory_dataframe(df)
                        
                        st.success(f"✅ Processing complete! ({len(output_df)} products)")
                        
                        # Show preview of results
                        with st.expander("Preview processed data"):
                            st.dataframe(output_df.head(20))
                        
                        # Show statistics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Products", len(output_df))
                        with col2:
                            st.metric("Total Sizes", len(output_df.columns) - 2)  # Exclude SKU and Total
                        with col3:
                            total_inventory = output_df['Total'].sum()
                            st.metric("Total Inventory", f"{int(total_inventory):,}")
                        
                        # Generate Excel file
                        excel_bytes = to_excel_bytes(output_df)
                        
                        # Download button
                        st.download_button(
                            label="📥 Download Excel File",
                            data=excel_bytes,
                            file_name=f"{uploaded_file.name.rsplit('.', 1)[0]}_processed.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary"
                        )
                        
                    except Exception as e:
                        st.error(f"❌ Error processing data: {e}")
                        st.exception(e)
    
    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
        st.exception(e)

else:
    # Show instructions when no file is uploaded
    st.info("👆 Please upload a CSV file to get started.")
    
    with st.expander("📋 Instructions"):
        st.markdown("""
        ### How to use:
        1. Export your Shopify products as CSV
        2. Upload the CSV file using the uploader above
        3. Click "Process Inventory" to process the data
        4. Download the processed Excel file
        
        ### Required CSV columns:
        - **Variant SKU**: The SKU for each variant (e.g., 'sku-1234-41')
        - **Variant Inventory Qty**: The inventory quantity for each variant
        
        ### Features:
        - ✅ Extracts base SKU and size from variant SKU
        - ✅ Groups inventory by base SKU and size
        - ✅ Consolidates duplicate EU/US sizes (keeps EU only)
        - ✅ Sorts by total inventory (highest first)
        """)
    
    # Show example
    with st.expander("📄 Example CSV format"):
        example_data = {
            'Variant SKU': [
                'sku-1234-black-41',
                'sku-1234-black-42',
                'sku-1234-black-9',  # US size
                'sku-1234-red-40',
                'sku-1234-red-41'
            ],
            'Variant Inventory Qty': ['5', '3', '2', '4', '6']
        }
        example_df = pd.DataFrame(example_data)
        st.dataframe(example_df)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; padding: 20px;'>"
    "Made with ❤️ by your momo to my favourite pinki"
    "</div>",
    unsafe_allow_html=True
)

