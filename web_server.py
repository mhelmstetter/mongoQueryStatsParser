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
            # Get namespace from the first hash in this shape
            shape_info = shape_references[shape_id]
            first_hash = shape_info["hashes"][0] if shape_info["hashes"] else ""
            # Format namespace as 'db.coll'
            namespace = ""
            skip_this_shape = False
            if first_hash:
                ns_value = shape_info["original_data"][first_hash].get("namespace", "")
                if isinstance(ns_value, dict) and 'db' in ns_value and 'coll' in ns_value:
                    # Skip if db is 'admin'
                    if ns_value['db'] == 'admin':
                        skip_this_shape = True
                    else:
                        namespace = f"{ns_value['db']}.{ns_value['coll']}"
                else:
                    namespace = str(ns_value) if ns_value is not None else ""
            
            # Skip admin databases
            if skip_this_shape:
                continue
                
            row = {
                "shapeId": f"Shape {shape_id}",
                "namespace": namespace,
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
                # Format namespace as 'db.coll'
                ns_value = hash_data.get("namespace", "")
                skip_this_hash = False
                if isinstance(ns_value, dict) and 'db' in ns_value and 'coll' in ns_value:
                    # Skip if db is 'admin'
                    if ns_value['db'] == 'admin':
                        skip_this_hash = True
                    else:
                        namespace = f"{ns_value['db']}.{ns_value['coll']}"
                else:
                    namespace = str(ns_value) if ns_value is not None else ""
                
                # Skip admin databases
                if skip_this_hash:
                    continue
                
                # Process metrics for this hash
                for metric in hash_data["metrics"]:
                    avg_exec_ms = 0
                    if "totalExecMicros" in metric and "sum" in metric["totalExecMicros"] and metric.get("execCount", 0) > 0:
                        avg_exec_ms = (metric["totalExecMicros"]["sum"] / metric["execCount"]) / 1000.0
                    
                    hash_details.append({
                        "hash": hash_val,  # Full hash for query details
                        "hashDisplay": hash_val[:8] + "...",  # Truncated hash for display
                        "namespace": namespace,
                        "execCount": metric.get("execCount", 0),
                        "avgExecMs": round(avg_exec_ms, 2),
                        "totalExecMs": round(metric.get("totalExecMicros", {}).get("sum", 0) / 1000.0, 2),
                        "docsReturned": metric.get("docsReturned", {}).get("sum", 0),
                        "keysExamined": metric.get("keysExamined", {}).get("sum", 0) if "keysExamined" in metric else 0,
                        "docsExamined": metric.get("docsExamined", {}).get("sum", 0) if "docsExamined" in metric else 0
                    })
            
            # Get namespace for this shape (using the first hash)
            first_hash = shape_info["hashes"][0] if shape_info["hashes"] else ""
            # Format namespace as 'db.coll'
            namespace = ""
            if first_hash:
                ns_value = shape_info["original_data"][first_hash].get("namespace", "")
                if isinstance(ns_value, dict) and 'db' in ns_value and 'coll' in ns_value:
                    # Skip if db is 'admin'
                    if ns_value['db'] == 'admin':
                        # Just use an empty string if it's admin
                        namespace = ""
                    else:
                        namespace = f"{ns_value['db']}.{ns_value['coll']}"
                else:
                    namespace = str(ns_value) if ns_value is not None else ""
            
            return jsonify({
                "shapeId": f"Shape {shape_id}",
                "namespace": namespace,
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
                # Format namespace as 'db.coll'
                ns_value = query_data.get("namespace", "")
                skip_this_query = False
                if isinstance(ns_value, dict) and 'db' in ns_value and 'coll' in ns_value:
                    # Skip if db is 'admin'
                    if ns_value['db'] == 'admin':
                        skip_this_query = True
                    else:
                        namespace = f"{ns_value['db']}.{ns_value['coll']}"
                else:
                    namespace = str(ns_value) if ns_value is not None else ""
                
                # Skip admin databases
                if skip_this_query:
                    continue
                
                # Extract command and pipeline information
                command_type = query_data.get("query_shape", {}).get("command", "Unknown")
                pipeline = query_data.get("query_shape", {}).get("pipeline", [])
                
                # Format JSON for display
                formatted_data = {
                    "command": command_type,
                    "namespace": namespace,
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

# No need to generate templates as they're now stored in the templates directory
def create_templates():
    """Function kept for backwards compatibility, does nothing now"""
    pass