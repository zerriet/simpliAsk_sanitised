#!/usr/bin/env python
"""
Simple script to run the audit log viewer GUI.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audit_gui.app import app

if __name__ == '__main__':
    print("=" * 60)
    print("SimpliAsk Audit Log Viewer")
    print("=" * 60)
    print("\nStarting Flask server...")
    print("Open your browser to: http://localhost:5000")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)

