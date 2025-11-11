"""Persistence utilities for market data."""

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd


class DataSaver:
    """Utility class for saving data in JSON or CSV format."""

    def __init__(self, base_path: str = "data/raw"):
        """
        Initialize DataSaver.

        Args:
            base_path: Base directory for saving files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def clear_data(self) -> int:
        """
        Clear all existing data files (CSV and JSON) in the base path directory.
        Only deletes files with .csv and .json extensions to avoid deleting other files.
        
        Returns:
            Number of files deleted
        """
        if not self.base_path.exists():
            return 0
        
        deleted_count = 0
        # Only clear CSV and JSON files (the files we create)
        allowed_extensions = {'.csv', '.json'}
        
        for file_path in self.base_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in allowed_extensions:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    # Log error but continue deleting other files
                    print(f"Error deleting {file_path}: {e}")
        
        return deleted_count

    def save_json(self, data: Any, filename: str) -> str:
        """
        Append JSON object to JSON file.

        Args:
            data: JSON object to append (dict, list, etc.)
            filename: Output filename (without extension)

        Returns:
            Path to saved file
        """
        filepath = self.base_path / f"{filename}.json"

        # Read existing data if file exists
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    # If file is corrupted or empty, start fresh
                    existing_data = []
        else:
            existing_data = []

        # Convert to list if it's not already
        if not isinstance(existing_data, list):
            existing_data = [existing_data]

        # Append new data
        existing_data.append(data)

        # Write back to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, default=str)

        return str(filepath)

    def save_csv(self, data: Dict[str, Any], filename: str) -> str:
        """
        Append a dictionary to a CSV file, creating headers if the file doesn't exist.

        Args:
            data: Dictionary representing a row to append.
            filename: Output filename (without extension).

        Returns:
            Path to saved file.
        """
        filepath = self.base_path / f"{filename}.csv"
        df = pd.DataFrame([data])
        file_exists = filepath.exists()
        df.to_csv(filepath, mode='a', header=not file_exists, index=False)
        return str(filepath)
