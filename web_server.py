"""
MongoDB Query Metrics Analyzer - Web Server Module
"""
import os
import json as json_lib
from flask import Flask, render_template, jsonify, request

def create_web_server(analyzed_results, shape_references):
    """Create and configure Flask app with routes"""
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        """Main page with summary table"""
        return render_template('index.html')
    
    @app.route('/api/data')
    def get_data():
        """API endpoint to get the analyzed data"""
        data = []
        for shape_id, result in analyzed_results.items():
            row = {
                "shapeId": f"Shape {shape_id}",
                "shapesCount": result["shapes_count"],
                "execCountTotal": result["execCount"]["total"],
                "avgExecMillis": round(result["avgExecMillis"]["avg"], 2),
                "avgTotalExecMillis": round(result["totalExecMillis"]["avg"], 2),
                "docsReturnedTotal": result["docsReturned"]["total"],
                "docsReturnedAvg": round(result["docsReturned"]["avg"], 2),
                "keysExaminedTotal": result["keysExamined"]["total"],
                "keysExaminedAvg": round(result["keysExamined"]["avg"], 2),
                "docsExaminedTotal": result["docsExamined"]["total"],
                "docsExaminedAvg": round(result["docsExamined"]["avg"], 2),
                "id": shape_id  # For drill-down
            }
            data.append(row)
        
        return jsonify(data)
    
    @app.route('/api/shape/<int:shape_id>')
    def get_shape_details(shape_id):
        """API endpoint to get details for a specific shape"""
        if shape_id in shape_references:
            shape_info = shape_references[shape_id]
            field_names = shape_info["field_names"]
            
            # Prepare hash details for drill-down
            hash_details = []
            for hash_val in shape_info["hashes"]:
                hash_data = shape_info["original_data"][hash_val]
                
                # Process metrics for this hash
                for metric in hash_data["metrics"]:
                    avg_exec_ms = 0
                    if "totalExecMicros" in metric and "sum" in metric["totalExecMicros"] and metric.get("execCount", 0) > 0:
                        avg_exec_ms = (metric["totalExecMicros"]["sum"] / metric["execCount"]) / 1000.0
                    
                    hash_details.append({
                        "hash": hash_val,  # Full hash for query details
                        "hashDisplay": hash_val[:8] + "...",  # Truncated hash for display
                        "execCount": metric.get("execCount", 0),
                        "avgExecMs": round(avg_exec_ms, 2),
                        "totalExecMs": round(metric.get("totalExecMicros", {}).get("sum", 0) / 1000.0, 2),
                        "docsReturned": metric.get("docsReturned", {}).get("sum", 0),
                        "keysExamined": metric.get("keysExamined", {}).get("sum", 0) if "keysExamined" in metric else 0,
                        "docsExamined": metric.get("docsExamined", {}).get("sum", 0) if "docsExamined" in metric else 0
                    })
            
            return jsonify({
                "shapeId": f"Shape {shape_id}",
                "fieldNames": field_names,
                "details": hash_details
            })
        
        return jsonify({"error": "Shape not found"}), 404
    
    @app.route('/api/query_details/<hash_val>')
    def get_query_details(hash_val):
        """API endpoint to get detailed query information for a specific hash"""
        for shape_id, shape_info in shape_references.items():
            if hash_val in shape_info["hashes"]:
                query_data = shape_info["original_data"][hash_val]
                
                # Extract command and pipeline information
                command_type = query_data.get("query_shape", {}).get("command", "Unknown")
                pipeline = query_data.get("query_shape", {}).get("pipeline", [])
                
                # Format JSON for display
                formatted_data = {
                    "command": command_type,
                    "pipeline": pipeline,
                    "fullQueryShape": query_data.get("query_shape", {})
                }
                
                return jsonify(formatted_data)
        
        return jsonify({"error": "Query hash not found"}), 404
    
    @app.route('/shape/<int:shape_id>')
    def shape_details_page(shape_id):
        """Page to show details for a specific shape"""
        return render_template('shape_details.html', shape_id=shape_id)
    
    @app.route('/query/<hash_val>')
    def query_details_page(hash_val):
        """Page to show query details for a specific hash"""
        return render_template('query_details.html', hash_val=hash_val)
    
    return app

def create_templates():
    """Create HTML templates for Flask app"""
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Create index.html
    with open('templates/index.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MongoDB Query Metrics Analyzer</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.min.css">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1, h2 {
            color: #333;
        }
        .container {
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        table.dataTable tbody tr:hover {
            background-color: #f0f8ff;
            cursor: pointer;
        }
        .highlight {
            background-color: #e6f7ff;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>MongoDB Query Metrics Analyzer</h1>
        <p>Click on a row to view detailed information about that query shape.</p>
        
        <table id="metricsTable" class="display">
            <thead>
                <tr>
                    <th>Shape ID</th>
                    <th>Shapes Count</th>
                    <th>Exec Count (total)</th>
                    <th>Avg Exec (ms)</th>
                    <th>Avg Total Exec (ms)</th>
                    <th>Docs Returned (total)</th>
                    <th>Docs Returned (avg)</th>
                    <th>Keys Examined (total)</th>
                    <th>Keys Examined (avg)</th>
                    <th>Docs Examined (total)</th>
                    <th>Docs Examined (avg)</th>
                </tr>
            </thead>
            <tbody>
                <!-- Data will be loaded here -->
            </tbody>
        </table>
    </div>

    <script>
        $(document).ready(function() {
            // Load data from API
            $.getJSON('/api/data', function(data) {
                // Initialize DataTable
                const table = $('#metricsTable').DataTable({
                    data: data,
                    columns: [
                        { data: 'shapeId' },
                        { data: 'shapesCount' },
                        { data: 'execCountTotal' },
                        { data: 'avgExecMillis' },
                        { data: 'avgTotalExecMillis' },
                        { data: 'docsReturnedTotal' },
                        { data: 'docsReturnedAvg' },
                        { data: 'keysExaminedTotal' },
                        { data: 'keysExaminedAvg' },
                        { data: 'docsExaminedTotal' },
                        { data: 'docsExaminedAvg' }
                    ],
                    order: [[2, 'desc']], // Sort by Exec Count (total) by default
                    pageLength: 25, // Set default page length to 25
                    lengthMenu: [10, 25, 50, 100], // Available page length options
                    columnDefs: [
                        {
                            targets: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                            className: 'dt-right'
                        }
                    ]
                });
                
                // Add click event to rows
                $('#metricsTable tbody').on('click', 'tr', function() {
                    const data = table.row(this).data();
                    window.location.href = '/shape/' + data.id;
                });
            });
        });
    </script>
</body>
</html>
        ''')
    
    # Create shape_details.html
    with open('templates/shape_details.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Query Shape Details</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.min.css">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1, h2 {
            color: #333;
        }
        .container {
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .field-names {
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-family: monospace;
            white-space: pre-wrap;
        }
        .back-link {
            margin-bottom: 20px;
            display: inline-block;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        table.dataTable tbody tr:hover {
            background-color: #f0f8ff;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← Back to Summary</a>
        <h1 id="shapeTitle">Loading...</h1>
        
        <h2>Field Names:</h2>
        <div class="field-names" id="fieldNames">Loading...</div>
        
        <h2>Query Details:</h2>
        <table id="detailsTable" class="display">
            <thead>
                <tr>
                    <th>Hash</th>
                    <th>Exec Count</th>
                    <th>Avg Exec (ms)</th>
                    <th>Total Exec (ms)</th>
                    <th>Docs Returned</th>
                    <th>Keys Examined</th>
                    <th>Docs Examined</th>
                </tr>
            </thead>
            <tbody>
                <!-- Data will be loaded here -->
            </tbody>
        </table>
    </div>

    <script>
        $(document).ready(function() {
            const shapeId = {{ shape_id }};
            
            // Load shape details
            $.getJSON('/api/shape/' + shapeId, function(data) {
                // Update page title and field names
                $('#shapeTitle').text(data.shapeId);
                $('#fieldNames').text(data.fieldNames.join(', '));
                
                // Initialize DataTable
                const table = $('#detailsTable').DataTable({
                    data: data.details,
                    columns: [
                        { 
                            data: 'hashDisplay',
                            render: function(data, type, row) {
                                if(type === 'display') {
                                    return '<a href="/query/' + row.hash + '">' + data + '</a>';
                                }
                                return data;
                            }
                        },
                        { data: 'execCount' },
                        { data: 'avgExecMs' },
                        { data: 'totalExecMs' },
                        { data: 'docsReturned' },
                        { data: 'keysExamined' },
                        { data: 'docsExamined' }
                    ],
                    order: [[1, 'desc']], // Sort by Exec Count by default
                    pageLength: 25, // Set default page length to 25
                    lengthMenu: [10, 25, 50, 100], // Available page length options
                    columnDefs: [
                        {
                            targets: [1, 2, 3, 4, 5, 6],
                            className: 'dt-right'
                        }
                    ]
                });
            });
        });
    </script>
</body>
</html>
        ''')
        
    # Create query_details.html for the additional drill-down
    with open('templates/query_details.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Query Command Details</title>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <!-- Add JSONTree for pretty printing and folding JSON -->
    <script src="https://cdn.jsdelivr.net/npm/jquery.json-viewer@1.4.0/json-viewer/jquery.json-viewer.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/jquery.json-viewer@1.4.0/json-viewer/jquery.json-viewer.css">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1, h2, h3 {
            color: #333;
        }
        .container {
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .back-link {
            margin-bottom: 20px;
            display: inline-block;
        }
        .json-container {
            background-color: #f8f8f8;
            padding: 15px;
            border-radius: 4px;
            margin-top: 10px;
            margin-bottom: 20px;
            overflow: auto;
        }
        .hash-display {
            font-family: monospace;
            background: #eee;
            padding: 5px 10px;
            border-radius: 3px;
            margin-left: 10px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div id="navigationLinks">
            <!-- Navigation links will be added dynamically -->
        </div>
        
        <h1>Query Details <span class="hash-display" id="hashDisplay">Loading...</span></h1>
        
        <h3>Command Type:</h3>
        <div id="commandType">Loading...</div>
        
        <h3>Pipeline:</h3>
        <div class="json-container">
            <pre id="pipelineJson"></pre>
        </div>
        
        <h3>Complete Query Shape:</h3>
        <div class="json-container">
            <pre id="fullQueryJson"></pre>
        </div>
    </div>

    <script>
        $(document).ready(function() {
            const hashVal = "{{ hash_val }}";
            let shapeId = null;
            
            // Get the parent shape ID to build navigation
            $.getJSON('/api/data', function(summaryData) {
                $.getJSON('/api/query_details/' + hashVal, function(queryData) {
                    // Display hash
                    $('#hashDisplay').text(hashVal);
                    
                    // Display command type
                    $('#commandType').text(queryData.command);
                    
                    // Display pipeline JSON with folding
                    $('#pipelineJson').jsonViewer(queryData.pipeline, {collapsed: false, rootCollapsable: false});
                    
                    // Display full query shape JSON with folding
                    $('#fullQueryJson').jsonViewer(queryData.fullQueryShape, {collapsed: true});
                    
                    // Find which shape this query belongs to
                    for (const entry of summaryData) {
                        $.getJSON('/api/shape/' + entry.id, function(shapeData) {
                            if (shapeData.details.some(item => item.hash === hashVal)) {
                                // Build navigation links
                                $('#navigationLinks').html(
                                    '<a href="/" class="back-link">← Back to Summary</a> | ' +
                                    '<a href="/shape/' + entry.id + '" class="back-link">← Back to ' + entry.shapeId + '</a>'
                                );
                            }
                        });
                    }
                });
            });
        });
    </script>
</body>
</html>
        ''')

