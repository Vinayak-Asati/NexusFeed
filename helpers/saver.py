"""CSV/JSON/DB saving utilities."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import sqlite3
from datetime import datetime


class DataSaver:
    """Utility class for saving data in various formats."""
    
    def __init__(self, base_path: str = "data/raw"):
        """
        Initialize DataSaver.
        
        Args:
            base_path: Base directory for saving files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_csv(self, data: List[Dict[str, Any]], filename: str) -> str:
        """
        Save data to CSV file.
        
        Args:
            data: List of dictionaries to save
            filename: Output filename (without extension)
        
        Returns:
            Path to saved file
        """
        if not data:
            raise ValueError("Data list is empty")
        
        filepath = self.base_path / f"{filename}.csv"
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        return str(filepath)
    
    def save_json(self, data: Any, filename: str) -> str:
        """
        Save data to JSON file.
        
        Args:
            data: Data to save (dict, list, etc.)
            filename: Output filename (without extension)
        
        Returns:
            Path to saved file
        """
        filepath = self.base_path / f"{filename}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        return str(filepath)
    
    def save_to_db(self, data: List[Dict[str, Any]], db_path: str, table_name: str) -> str:
        """
        Save data to SQLite database.
        
        Args:
            data: List of dictionaries to save
            db_path: Path to SQLite database file
            table_name: Name of the table to create/insert into
        
        Returns:
            Path to database file
        """
        if not data:
            raise ValueError("Data list is empty")
        
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Get column names from first row
        columns = list(data[0].keys())
        columns_str = ', '.join(columns)
        placeholders = ', '.join(['?' for _ in columns])
        
        # Create table if it doesn't exist
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {', '.join([f'{col} TEXT' for col in columns])},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_table_sql)
        
        # Insert data
        insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        for row in data:
            values = [str(row.get(col, '')) for col in columns]
            cursor.execute(insert_sql, values)
        
        conn.commit()
        conn.close()
        
        return str(db_file)

