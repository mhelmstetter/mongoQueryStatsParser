#!/usr/bin/env python3
"""
MongoDB Query Metrics Analyzer - Main Entry Point
"""
import json
import argparse
import threading
import time
import webbrowser

from analyzer import analyze_metrics
from console_output import print_console_tables
from web_server import create_web_server, create_templates

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='MongoDB Query Metrics Analyzer')
    parser.add_argument('file', help='JSON file to analyze')
    parser.add_argument('--web', action='store_true', help='Display results in web browser')
    args = parser.parse_args()
    
    # Load JSON data from file
    try:
        with open(args.file, 'r') as file:
            data = json.load(file)
        
        # Analyze the metrics
        results, shapes = analyze_metrics(data)
        
        # Print to console if web option is not selected
        if not args.web:
            print_console_tables(results, shapes)
        else:
            # Create HTML templates and initialize the web server
            create_templates()
            app = create_web_server(results, shapes)
            
            # Start Flask app in a separate thread
            flask_thread = threading.Thread(target=lambda: app.run(debug=False, port=5000))
            flask_thread.daemon = True
            flask_thread.start()
            
            # Open browser
            time.sleep(1)
            webbrowser.open('http://localhost:5000')
            
            print("Opening web browser. Press Ctrl+C to exit.")
            
            # Keep the main thread running
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nExiting...")
    
    except FileNotFoundError:
        print(f"Error: File '{args.file}' not found.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in the input file.")
    except ImportError as e:
        print(f"Error: Missing required package: {str(e)}.")
        print("Please install required packages:")
        print("pip install prettytable flask")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()

