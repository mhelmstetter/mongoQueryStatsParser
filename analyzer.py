"""
MongoDB Query Metrics Analyzer - Analysis Module
"""
import statistics
from collections import defaultdict
from typing import Dict, List, Any, DefaultDict, Tuple

def extract_match_shape_and_hash(batch: Dict) -> Tuple[str, tuple]:
    """Extract the shape of the $match query"""
    pipeline = batch.get("key", {}).get("queryShape", {}).get("pipeline", [])
    original_hash = batch.get("queryShapeHash", "")
    
    field_names = []
    for stage in pipeline:
        if "$match" in stage:
            # Get all field names recursively
            field_names = get_field_names(stage["$match"])
            # Sort field names for consistent identification
            field_names.sort()
            break
    
    return original_hash, tuple(field_names)  # Use tuple for hashability

def get_field_names(obj: Dict, prefix="") -> List[str]:
    """Recursively get all field names in a dictionary"""
    field_names = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            # Skip operators (keys starting with $)
            if key.startswith("$"):
                # If it's a logical operator, process its contents
                if key in ["$and", "$or", "$nor"]:
                    for item in value:
                        field_names.extend(get_field_names(item, prefix))
                continue
                
            new_prefix = f"{prefix}.{key}" if prefix else key
            # If value is a dict and contains operators, add the field name
            if isinstance(value, dict) and any(k.startswith("$") for k in value.keys()):
                field_names.append(new_prefix)
            
            # Continue recursion
            field_names.extend(get_field_names(value, new_prefix))
    elif isinstance(obj, list):
        for item in obj:
            field_names.extend(get_field_names(item, prefix))
            
    return field_names

def analyze_metrics(data: Dict) -> tuple:
    """Analyze metrics from MongoDB aggregation data"""
    # Group hashes by field names (shape)
    shape_to_hashes = defaultdict(list)
    hash_to_metrics = defaultdict(list)
    original_data = {}  # Store original data for drill-down
    
    for batch in data.get("cursor", {}).get("firstBatch", []):
        query_shape_hash, field_names = extract_match_shape_and_hash(batch)
        
        if query_shape_hash and "metrics" in batch:
            shape_to_hashes[field_names].append(query_shape_hash)
            hash_to_metrics[query_shape_hash].append(batch["metrics"])
            
            # Store original data for drill-down
            if query_shape_hash not in original_data:
                original_data[query_shape_hash] = {
                    "query_shape": batch.get("key", {}).get("queryShape", {}),
                    "metrics": []
                }
            original_data[query_shape_hash]["metrics"].append(batch["metrics"])
    
    # Assign shape IDs
    shapes = {}
    shape_id_counter = 1
    
    for field_names in shape_to_hashes.keys():
        shapes[shape_id_counter] = {
            "field_names": list(field_names),
            "hashes": shape_to_hashes[field_names],
            "original_data": {hash_val: original_data[hash_val] for hash_val in shape_to_hashes[field_names]}
        }
        shape_id_counter += 1
    
    # Calculate statistics for each shape
    results = {}
    for shape_id, shape_info in shapes.items():
        # Initialize metrics containers
        shape_results = {
            "shapes_count": 0,
            "execCount": {
                "total": 0
            },
            "avgExecMillis": {
                "values": [],
                "avg": 0
            },
            "totalExecMillis": {
                "avg": 0
            },
            "docsReturned": {
                "avg": 0,
                "total": 0
            },
            "keysExamined": {
                "avg": 0,
                "total": 0
            },
            "docsExamined": {
                "avg": 0,
                "total": 0
            }
        }
        
        # Process each hash separately to calculate per-hash average execution time
        for hash_val in shape_info["hashes"]:
            metrics_list = hash_to_metrics[hash_val]
            shape_results["shapes_count"] += len(metrics_list)
            
            # Calculate average execution time for this hash
            for metric in metrics_list:
                # Execution count
                exec_count = metric.get("execCount", 0)
                shape_results["execCount"]["total"] += exec_count
                
                # Calculate avg exec time for this hash (totalExecMicros.sum / execCount)
                if "totalExecMicros" in metric and "sum" in metric["totalExecMicros"] and exec_count > 0:
                    total_exec_sum = metric["totalExecMicros"]["sum"]
                    avg_exec_time = (total_exec_sum / exec_count) / 1000.0  # Convert to ms
                    shape_results["avgExecMillis"]["values"].append(avg_exec_time)
                
                # Total execution time in ms
                if "totalExecMicros" in metric and "sum" in metric["totalExecMicros"]:
                    total_exec_ms = metric["totalExecMicros"]["sum"] / 1000.0
                    shape_results["totalExecMillis"]["avg"] += total_exec_ms
                
                # Docs returned
                if "docsReturned" in metric and "sum" in metric["docsReturned"]:
                    docs_sum = metric["docsReturned"]["sum"]
                    shape_results["docsReturned"]["total"] += docs_sum
                
                # Keys examined
                if "keysExamined" in metric and "sum" in metric["keysExamined"]:
                    keys_sum = metric["keysExamined"]["sum"]
                    shape_results["keysExamined"]["total"] += keys_sum
                
                # Docs examined
                if "docsExamined" in metric and "sum" in metric["docsExamined"]:
                    docs_exam_sum = metric["docsExamined"]["sum"]
                    shape_results["docsExamined"]["total"] += docs_exam_sum
        
        # Calculate the average of averages for exec time
        if shape_results["avgExecMillis"]["values"]:
            shape_results["avgExecMillis"]["avg"] = statistics.mean(shape_results["avgExecMillis"]["values"])
        
        # Calculate average for total execution time
        metric_count = shape_results["shapes_count"]
        if metric_count > 0:
            shape_results["totalExecMillis"]["avg"] /= metric_count
            shape_results["docsReturned"]["avg"] = shape_results["docsReturned"]["total"] / metric_count
            shape_results["keysExamined"]["avg"] = shape_results["keysExamined"]["total"] / metric_count
            shape_results["docsExamined"]["avg"] = shape_results["docsExamined"]["total"] / metric_count
        
        results[shape_id] = shape_results
    
    return results, shapes

