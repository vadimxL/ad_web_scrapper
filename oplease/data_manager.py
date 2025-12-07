#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Optional

import pandas as pd

from oplease.config import Config
from oplease.data_parser import DataParser


class DataManager:
    """Handles data operations, price changes, and data transformations"""
    
    def __init__(self, config: Config, data_parser: DataParser):
        self.config = config
        self.data_parser = data_parser

    def load_previous_data(self, path: Path) -> Optional[pd.DataFrame]:
        """Load previous car data from Excel file"""
        if not path.exists():
            return None
        try:
            df = pd.read_excel(path, sheet_name="cars")
        except Exception as exc:  # corrupted or missing sheet; skip diff this run
            print(f"Warning: unable to read previous data from {path}: {exc}")
            return None
        for col in ("year", "km", "price"):
            if col in df.columns:
                df[col] = self.data_parser.to_nullable_int(df[col])
        return df

    def build_merge_key(self, df: pd.DataFrame) -> pd.Series:
        """Build a merge key from key columns for matching cars"""
        key_series = pd.Series(["" for _ in range(len(df))], index=df.index, dtype="object")
        for col in self.config.KEY_COLUMNS:
            if col in df.columns:
                raw = df[col]
            else:
                raw = pd.Series([pd.NA for _ in range(len(df))], index=df.index)
            if col in ("year", "km"):
                values = self.data_parser.to_nullable_int(raw).fillna(-1)
            else:
                values = raw.fillna("")
            key_series = key_series + "|" + values.astype(str)
        return key_series.str.lstrip("|")

    def compute_price_changes(self, current_df: pd.DataFrame, prev_df: Optional[pd.DataFrame]) -> pd.DataFrame:
        """Compute price changes between current and previous data"""
        if prev_df is None or prev_df.empty:
            return pd.DataFrame(columns=self.config.PRICE_DIFF_COLUMNS)
        current_with_key = current_df.copy()
        current_with_key["__merge_key"] = self.build_merge_key(current_with_key)

        prev_subset = prev_df[self.config.KEY_COLUMNS + ["price"]].copy()
        prev_subset = prev_subset.dropna(subset=["price"])
        prev_subset["__merge_key"] = self.build_merge_key(prev_subset)
        prev_subset = prev_subset.drop_duplicates("__merge_key", keep="last")
        prev_subset["price"] = self.data_parser.to_nullable_int(prev_subset["price"])

        merged = current_with_key.merge(
            prev_subset[["__merge_key", "price"]].rename(columns={"price": "price_previous"}),
            on="__merge_key",
            how="left",
        )
        merged["price"] = self.data_parser.to_nullable_int(merged["price"])
        merged["price_previous"] = self.data_parser.to_nullable_int(merged["price_previous"])

        mask = merged["price"].notna() & merged["price_previous"].notna()
        changed = merged.loc[mask & (merged["price"] != merged["price_previous"])].copy()
        changed["price_change"] = self.data_parser.to_nullable_int(changed["price"] - changed["price_previous"])
        changed["status"] = "price_changed"
        changed = changed.drop(columns=["__merge_key"], errors="ignore")

        removed = prev_subset.loc[~prev_subset["__merge_key"].isin(current_with_key["__merge_key"])].copy()
        if not removed.empty:
            removed["price_previous"] = self.data_parser.to_nullable_int(removed["price"])
            removed["price"] = pd.Series([pd.NA] * len(removed), dtype="Int64")
            removed["price_change"] = pd.Series([pd.NA] * len(removed), dtype="Int64")
            removed["status"] = "removed"
            removed = removed.drop(columns=["__merge_key"], errors="ignore")
        else:
            removed = pd.DataFrame(columns=self.config.PRICE_DIFF_COLUMNS)

        result = pd.concat([changed, removed], ignore_index=True, sort=False)
        if result.empty:
            return pd.DataFrame(columns=self.config.PRICE_DIFF_COLUMNS)
        return result.reindex(columns=self.config.PRICE_DIFF_COLUMNS)

