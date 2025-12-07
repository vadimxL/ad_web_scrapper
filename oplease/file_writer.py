#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Any

import pandas as pd

from oplease.config import Config
from oplease.data_parser import DataParser


class FileWriter:
    """Handles writing data to Excel and CSV files"""
    
    def __init__(self, config: Config, data_parser: DataParser):
        self.config = config
        self.data_parser = data_parser

    @staticmethod
    def auto_adjust_columns(ws: Any, df: pd.DataFrame) -> None:
        """Auto-adjust column widths in Excel worksheet"""
        for col_idx, col_name in enumerate(df.columns, start=1):
            lengths = [len(str(col_name))]
            if not df.empty:
                lengths.extend(len(str(v)) if not pd.isna(v) else 0 for v in df.iloc[:, col_idx - 1])
            max_len = max(lengths) if lengths else 0
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = min(max_len + 2, 60)

    def write_excel(self, current_df: pd.DataFrame, price_changes_df: Optional[pd.DataFrame]) -> None:
        """Write current data and price changes to Excel file"""
        current_sorted = current_df.sort_values(
            by=["price", "manufacturer", "model"],
            ascending=[False, True, True],
            na_position="last",
        )
        if price_changes_df is None or price_changes_df.empty:
            price_changes_sorted = pd.DataFrame(columns=self.config.PRICE_DIFF_COLUMNS)
        else:
            price_changes_sorted = price_changes_df[self.config.PRICE_DIFF_COLUMNS].sort_values(
                by="price_change",
                ascending=True,
                na_position="last",
            )

        with pd.ExcelWriter(self.config.OUT_PATH, engine="openpyxl") as writer:
            current_sorted.to_excel(writer, index=False, sheet_name="cars")
            self.auto_adjust_columns(writer.sheets["cars"], current_sorted)

            price_changes_sorted.to_excel(writer, index=False, sheet_name=self.config.PRICE_CHANGES_SHEET)
            self.auto_adjust_columns(writer.sheets[self.config.PRICE_CHANGES_SHEET], price_changes_sorted)

    def write_csv(self, current_df: pd.DataFrame) -> None:
        """Write current car data to CSV file"""
        current_sorted = current_df.sort_values(
            by=["price", "manufacturer", "model"],
            ascending=[False, True, True],
            na_position="last",
        )
        current_sorted.to_csv(self.config.OUT_CSV_PATH, index=False)

    def save_price_changes_csv(self, price_changes_df: pd.DataFrame) -> None:
        """Save only price changes (not removed cars) to CSV"""
        # Filter to only price_changed status
        price_changed_df = price_changes_df[price_changes_df["status"] == "price_changed"].copy()
        if price_changed_df.empty:
            return
        timestamp = pd.Timestamp.now(tz="UTC")
        export_df = price_changed_df.copy()
        export_df.insert(0, "scrape_timestamp", timestamp)
        export_df = export_df.reset_index(drop=True)

        existing_df: Optional[pd.DataFrame]
        if self.config.PRICE_CHANGES_CSV.exists():
            try:
                existing_df = pd.read_csv(self.config.PRICE_CHANGES_CSV)
            except Exception as exc:
                print(f"Warning: unable to read existing price change log {self.config.PRICE_CHANGES_CSV}: {exc}. Rewriting file.")
                existing_df = None
        else:
            existing_df = None

        desired_columns = ["scrape_timestamp"] + self.config.PRICE_DIFF_COLUMNS

        if existing_df is None or existing_df.empty:
            export_df.to_csv(self.config.PRICE_CHANGES_CSV, mode="a", header=True, index=False, columns=desired_columns)
            return

        if list(existing_df.columns) != desired_columns:
            if "status" not in existing_df.columns:
                existing_df["status"] = "price_changed"
            for col in desired_columns:
                if col not in existing_df.columns:
                    existing_df[col] = pd.NA
            existing_df = existing_df[desired_columns]
            combined_df = pd.concat([existing_df, export_df[desired_columns]], ignore_index=True, sort=False)
            combined_df.to_csv(self.config.PRICE_CHANGES_CSV, index=False)
        else:
            export_df.to_csv(self.config.PRICE_CHANGES_CSV, mode="a", header=False, index=False, columns=desired_columns)

    def save_removed_cars_csv(self, price_changes_df: pd.DataFrame) -> None:
        """Save removed cars to CSV"""
        # Filter to only removed status
        removed_df = price_changes_df[price_changes_df["status"] == "removed"].copy()
        
        # Filter out excluded manufacturers (case-insensitive comparison)
        if self.config.EXCLUDED_MANUFACTURERS and not removed_df.empty and "manufacturer" in removed_df.columns:
            excluded_lower = [excluded.lower().strip() for excluded in self.config.EXCLUDED_MANUFACTURERS]
            mask = ~removed_df["manufacturer"].astype(str).str.lower().str.strip().isin(excluded_lower)
            removed_df = removed_df[mask].copy()
        
        # Filter out excluded models (case-insensitive, partial matching supported)
        if self.config.EXCLUDED_MODELS and not removed_df.empty and "model" in removed_df.columns:
            excluded_lower = [excluded.lower().strip() for excluded in self.config.EXCLUDED_MODELS]
            model_series = removed_df["model"].astype(str).str.lower().str.strip()
            # Check if any excluded model name is contained in the car's model name
            mask = ~model_series.apply(lambda m: any(excluded in m for excluded in excluded_lower))
            removed_df = removed_df[mask].copy()
        
        # Filter out cars below minimum year
        if self.config.MIN_YEAR is not None and not removed_df.empty and "year" in removed_df.columns:
            mask = removed_df["year"].isna() | (removed_df["year"] >= self.config.MIN_YEAR)
            removed_df = removed_df[mask].copy()
        
        if removed_df.empty:
            return
        timestamp = pd.Timestamp.now(tz="UTC")
        export_df = removed_df.copy()
        export_df.insert(0, "scrape_timestamp", timestamp)
        export_df = export_df.reset_index(drop=True)

        existing_df: Optional[pd.DataFrame]
        if self.config.REMOVED_CARS_CSV.exists():
            try:
                existing_df = pd.read_csv(self.config.REMOVED_CARS_CSV)
            except Exception as exc:
                print(f"Warning: unable to read existing removed cars log {self.config.REMOVED_CARS_CSV}: {exc}. Rewriting file.")
                existing_df = None
        else:
            existing_df = None

        desired_columns = ["scrape_timestamp"] + self.config.PRICE_DIFF_COLUMNS

        if existing_df is None or existing_df.empty:
            export_df.to_csv(self.config.REMOVED_CARS_CSV, mode="a", header=True, index=False, columns=desired_columns)
            return

        if list(existing_df.columns) != desired_columns:
            if "status" not in existing_df.columns:
                existing_df["status"] = "removed"
            for col in desired_columns:
                if col not in existing_df.columns:
                    existing_df[col] = pd.NA
            existing_df = existing_df[desired_columns]
            combined_df = pd.concat([existing_df, export_df[desired_columns]], ignore_index=True, sort=False)
            combined_df.to_csv(self.config.REMOVED_CARS_CSV, index=False)
        else:
            export_df.to_csv(self.config.REMOVED_CARS_CSV, mode="a", header=False, index=False, columns=desired_columns)

    def save_filtered_cars_csv(self, filtered_df: pd.DataFrame) -> None:
        """Save filtered/excluded cars to CSV (overwrites existing file)"""
        if filtered_df.empty:
            return
        timestamp = pd.Timestamp.now(tz="UTC")
        export_df = filtered_df.copy()
        export_df.insert(0, "scrape_timestamp", timestamp)
        export_df = export_df.reset_index(drop=True)
        
        # Overwrite the file with current filtered cars
        export_df.to_csv(self.config.FILTERED_CARS_CSV, index=False)

