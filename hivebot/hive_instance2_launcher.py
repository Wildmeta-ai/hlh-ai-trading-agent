#!/usr/bin/env python
"""
Launcher script for second hivebot instance with separate database
"""
import os
import sys

# Set environment variable for database file before importing
os.environ['HIVE_DB_FILE'] = 'hive_strategies_instance2.db'
os.environ['HIVE_INSTANCE'] = '2'
os.environ['HIVE_PORT'] = '8082'

if __name__ == "__main__":
    # Pass through command line arguments and run the main script directly
    sys.argv[0] = 'hive_dynamic_core_modular.py'  # Preserve expected script name
    exec(open('hive_dynamic_core_modular.py').read())
