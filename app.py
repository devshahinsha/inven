#!/usr/bin/env python3
"""
Streamlit web app for processing Shopify inventory CSV files.
Version 2: Simplified output with SKU, Total Quantity, Cost Price, Total Cost Price.
"""

import streamlit as st
import pandas as pd
import re
from collections import defaultdict
from io import BytesIO


def extract_base_sku(variant_sku):
    """
    Extract base SKU from variant SKU by removing the size suffix.
    """
    if pd.isna(variant_sku) or not variant_sku or not isinstance(variant_sku, str):
        return None
    
    parts = variant_sku.split('-')
    
    if len(parts) < 2:
        return None
    
    last_segment = parts[-1]
    numeric_match = re.search(r'(\d+)', last_segment)
    if numeric_match:
        return '-'.join(parts[:-1])
    
    if last_segment.isdigit():
        return '-'.join(parts[:-1])
    
    return None


def parse_numeric(value):
    """Parse a numeric value from string."""
    if pd.isna(value) or value == '' or value is None:
        return 0.0
    
    try:
        if isinstance(value, str):
            cleaned = re.sub(r'[^\d.\-]', '', value)
            return float(cleaned) if cleaned else 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def process_inventory_dataframe_v2(df, cost_column=None):
    """
    Process the DataFrame and return cost summary output DataFrame.
    """
    inventory_data = defaultdict(lambda: {'total_qty': 0, 'cost_price': None})
    
    for idx, row in df.iterrows():
        variant_sku = row['Variant SKU']
        inventory_qty_str = row['Variant Inventory Qty']
        
        base_sku = extract_base_sku(variant_sku)
        
        if base_sku is None:
            continue
        
        inventory_qty = parse_numeric(inventory_qty_str)
        
        cost_price = 0.0
        if cost_column and cost_column in row:
            cost_price = parse_numeric(row[cost_column])
        
        inventory_data[base_sku]['total_qty'] += inventory_qty
        
        if inventory_data[base_sku]['cost_price'] is None and cost_price > 0:
            inventory_data[base_sku]['cost_price'] = cost_price
    
    if not inventory_data:
        raise ValueError("No valid inventory data found. Check if Variant SKU format is correct.")
    
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
    
    output_df = pd.DataFrame(output_rows)
    output_df = output_df.sort_values('Total Cost Price', ascending=False).reset_index(drop=True)
    
    return output_df


def to_excel_bytes(df):
    """Convert DataFrame to Excel file in memory."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory Cost')
    output.seek(0)
    return output.getvalue()


# Streamlit UI
st.set_page_config(
    page_title="Inventory Cost Processor v2",
    page_icon="💰",
    layout="centered"
)

st.title("💰 Inventory Cost Processor v2")
st.markdown("Process Shopify CSV files and generate cost summary with **SKU, Total Quantity, Cost Price, Total Cost Price**.")

# File upload
uploaded_file = st.file_uploader(
    "Upload CSV file",
    type=['csv'],
    help="Upload a Shopify export CSV file with 'Variant SKU', 'Variant Inventory Qty', and 'Cost per item' columns"
)

if uploaded_file is not None:
    try:
        with st.spinner("Reading CSV file..."):
            df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
        
        # Validate required columns
        required_columns = ['Variant SKU', 'Variant Inventory Qty']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"❌ Required columns missing: {missing_columns}")
            st.info("Please ensure your CSV file contains 'Variant SKU' and 'Variant Inventory Qty' columns.")
        else:
            # Find cost column
            cost_column = None
            possible_cost_columns = ['Cost per item', 'Variant Cost', 'Cost Price', 'Cost']
            for col in possible_cost_columns:
                if col in df.columns:
                    cost_column = col
                    break
            
            st.success(f"✅ File loaded successfully! ({len(df)} rows)")
            
            if cost_column:
                st.info(f"📊 Using cost column: **{cost_column}**")
            else:
                st.warning("⚠️ No cost column found. Cost values will be 0.")
            
            with st.expander("Preview CSV data"):
                st.dataframe(df.head(10))
            
            if st.button("Process Inventory", type="primary"):
                with st.spinner("Processing inventory data..."):
                    try:
                        output_df = process_inventory_dataframe_v2(df, cost_column)
                        
                        st.success(f"✅ Processing complete! ({len(output_df)} products)")
                        
                        # Show preview of results
                        with st.expander("Preview processed data", expanded=True):
                            st.dataframe(output_df.head(20))
                        
                        # Show statistics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Products", len(output_df))
                        with col2:
                            total_qty = output_df['Total Quantity'].sum()
                            st.metric("Total Inventory", f"{int(total_qty):,}")
                        with col3:
                            total_cost = output_df['Total Cost Price'].sum()
                            st.metric("Total Cost Value", f"${total_cost:,.2f}")
                        
                        # Generate Excel file
                        excel_bytes = to_excel_bytes(output_df)
                        
                        # Download button
                        st.download_button(
                            label="📥 Download Excel File",
                            data=excel_bytes,
                            file_name=f"{uploaded_file.name.rsplit('.', 1)[0]}_cost_summary.xlsx",
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
        - **Cost per item** (optional): The cost price per unit
        
        ### Output columns:
        | Column | Description |
        |--------|-------------|
        | SKU | Base SKU (without size suffix) |
        | Total Quantity | Sum of all size variants |
        | Cost Price | Cost per unit |
        | Total Cost Price | Total Quantity × Cost Price |
        """)
    
    with st.expander("📄 Example"):
        st.markdown("**Input CSV:**")
        example_input = pd.DataFrame({
            'Variant SKU': ['sku-1234-black-41', 'sku-1234-black-42', 'sku-1234-red-40'],
            'Variant Inventory Qty': ['5', '3', '4'],
            'Cost per item': ['25.00', '25.00', '30.00']
        })
        st.dataframe(example_input)
        
        st.markdown("**Output:**")
        example_output = pd.DataFrame({
            'SKU': ['sku-1234-black', 'sku-1234-red'],
            'Total Quantity': [8, 4],
            'Cost Price': [25.00, 30.00],
            'Total Cost Price': [200.00, 120.00]
        })
        st.dataframe(example_output)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; padding: 20px;'>"
    "Made with ❤️ by your momo to my favourite pinki"
    "</div>",
    unsafe_allow_html=True
)
