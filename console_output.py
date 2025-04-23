"""
MongoDB Query Metrics Analyzer - Console Output Module
"""
from prettytable import PrettyTable

def print_console_tables(results, shapes):
    """Print results as console tables"""
    # Create a table with shapes as rows and metrics as columns
    table = PrettyTable()
    
    # Define column headers
    table.field_names = [
        "Shape ID", 
        "Shapes Count", 
        "Exec Count (total)",
        "Avg Exec (ms)",
        "Avg Total Exec (ms)",
        "Docs Returned (total)",
        "Docs Returned (avg)",
        "Keys Examined (total)",
        "Keys Examined (avg)",
        "Docs Examined (total)",
        "Docs Examined (avg)"
    ]
    
    # Set right alignment for numeric columns
    for field in table.field_names:
        if field != "Shape ID":
            table.align[field] = "r"
    
    # Add a row for each query shape
    for shape_id, result in results.items():
        row = [
            f"Shape {shape_id}",
            result["shapes_count"],
            result["execCount"]["total"],
            f"{result['avgExecMillis']['avg']:.2f}",
            f"{result['totalExecMillis']['avg']:.2f}",
            result["docsReturned"]["total"],
            f"{result['docsReturned']['avg']:.2f}",
            result["keysExamined"]["total"],
            f"{result['keysExamined']['avg']:.2f}",
            result["docsExamined"]["total"],
            f"{result['docsExamined']['avg']:.2f}"
        ]
        table.add_row(row)
    
    # Sort by total execution count (descending)
    table.sortby = "Exec Count (total)"
    table.reversesort = True
    
    # Print the table
    print("\nMetrics Summary Table:")
    print(table)
    
    # Create and print reference table for shape IDs and field names
    print("\nQuery Shape Reference:")
    ref_table = PrettyTable()
    ref_table.field_names = ["Shape ID", "Field Names"]
    
    for shape_id, shape_info in shapes.items():
        field_str = ", ".join(shape_info["field_names"]) if shape_info["field_names"] else "No fields"
        ref_table.add_row([f"Shape {shape_id}", field_str])
    
    print(ref_table)

