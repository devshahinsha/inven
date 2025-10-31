# Inventory Pivot Script

A Python script and web app to process Shopify product export CSV files and generate Excel files with inventory data grouped by base SKU and size variants.

## Features

- Extracts base SKU from Variant SKU by removing the size suffix
- Groups inventory by base SKU and size
- **Automatically consolidates duplicate EU/US sizes** (keeps EU sizes only)
- Creates Excel output with:
  - Base SKU in the first column
  - One column per unique size (sorted numerically)
  - Total inventory column at the end
  - Empty cells for sizes that don't exist for a particular base SKU

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Or install directly:

```bash
pip install pandas openpyxl streamlit
```

## Usage

### Web App (Recommended)

Launch the web app:

```bash
streamlit run app.py
```

Then open your browser to the URL shown (typically `http://localhost:8501`). The web app provides:
- Drag-and-drop CSV file upload
- Real-time processing
- Preview of results
- One-click Excel download

### Command Line

Basic usage:

```bash
python process_inventory.py input.csv
```

Place your CSV file in the `input` folder, then run the script with just the filename. This will create `output/input.xlsx` in an `output` folder (created automatically if it doesn't exist).

Example:

```bash
# Place your CSV file in: input/products.csv
python process_inventory.py products.csv
# Output will be: output/products.xlsx
```

Specify output file:

```bash
python process_inventory.py products.csv output.xlsx
```

The output file will be saved in the `output` folder unless you specify an absolute path.

You can also provide full paths:

```bash
python process_inventory.py input/products.csv output/inventory.xlsx
```

## How It Works

1. **Base SKU Extraction**: The script extracts the base SKU by removing the last segment from the Variant SKU (after splitting by hyphens). For example:

   - `sku-1234-41` → base SKU: `sku-1234`
   - `sku-1234-black-41` → base SKU: `sku-1234-black`
   - `177525-LT_Brown-40` → base SKU: `177525-LT_Brown`

2. **Size Extraction**: The size is extracted from the last segment of the Variant SKU. The script handles cases where the last segment contains additional characters (e.g., `40_AN_AN` → size: `40`).

3. **Grouping**: All variants are grouped by base SKU, and inventory is collected for each size.

4. **EU/US Size Consolidation**: Automatically detects when the same physical size is represented in both EU and US sizing systems, merges them, and keeps only the EU size.

5. **Output**: Creates an Excel file with:
   - First column: Base SKU
   - Middle columns: Each unique size found across all products (sorted numerically)
   - Last column: Total inventory for that base SKU

## Example

**Input CSV** (Shopify export):

```
Variant SKU,Variant Inventory Qty
sku-1234-black-41,5
sku-1234-black-42,3
sku-1234-black-43,2
sku-1234-red-40,4
sku-1234-red-41,6
```

**Output Excel**:

```
SKU            | 40 | 41 | 42 | 43 | Total
---------------|----|----|----|----|------
sku-1234-black |    | 5  | 3  | 2  | 10
sku-1234-red   | 4  | 6  |    |    | 10
```

## Requirements

- Python 3.7+
- pandas >= 2.0.0
- openpyxl >= 3.0.0
- streamlit >= 1.28.0 (for web app)

## Error Handling

The script will:

- Validate that the input file exists
- Check for required columns (`Variant SKU`, `Variant Inventory Qty`)
- Skip rows where base SKU/size extraction fails
- Convert invalid inventory values to 0
- Handle missing data gracefully
