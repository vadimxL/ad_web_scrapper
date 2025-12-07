#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional

import pandas as pd
from bs4 import BeautifulSoup

from oplease.config import Config
from oplease.car_parser import CarParser
from oplease.data_manager import DataManager
from oplease.data_parser import DataParser
from oplease.file_writer import FileWriter
from oplease.web_scraper import WebScraper


class CarScraper:
    """Main orchestrator class for scraping and processing car data"""
    
    def __init__(self):
        self.config = Config()
        self.data_parser = DataParser()
        self.web_scraper = WebScraper(self.config)
        self.car_parser = CarParser(self.config, self.web_scraper, self.data_parser)
        self.data_manager = DataManager(self.config, self.data_parser)
        self.file_writer = FileWriter(self.config, self.data_parser)

    def run(self) -> None:
        """Main execution method"""
        prev_df: Optional[pd.DataFrame] = self.data_manager.load_previous_data(self.config.OUT_PATH)
        soup: BeautifulSoup = self.web_scraper.fetch_html(self.config.URL)
        rows, filtered_rows = self.car_parser.parse_list_table(soup)
        
        if not rows and not filtered_rows:
            raise SystemExit("No results parsed. The page layout may have changed.")
        
        current_df: pd.DataFrame = pd.DataFrame(rows, columns=self.config.COLUMNS) if rows else pd.DataFrame(columns=self.config.COLUMNS)
        for col in ("year", "km", "price"):
            if col in current_df.columns:
                current_df[col] = self.data_parser.to_nullable_int(current_df[col])

        # Save filtered cars
        if filtered_rows:
            filtered_df: pd.DataFrame = pd.DataFrame(filtered_rows, columns=self.config.COLUMNS)
            for col in ("year", "km", "price"):
                if col in filtered_df.columns:
                    filtered_df[col] = self.data_parser.to_nullable_int(filtered_df[col])
            self.file_writer.save_filtered_cars_csv(filtered_df)

        price_changes_df: pd.DataFrame = self.data_manager.compute_price_changes(current_df, prev_df)
        self.file_writer.write_excel(current_df, price_changes_df)
        self.file_writer.write_csv(current_df)
        self.file_writer.save_price_changes_csv(price_changes_df)
        self.file_writer.save_removed_cars_csv(price_changes_df)

        print(f"Wrote {len(current_df)} rows to {self.config.OUT_PATH.resolve()} and {self.config.OUT_CSV_PATH.resolve()}")
        if filtered_rows:
            print(f"Filtered {len(filtered_rows)} excluded car(s); saved to {self.config.FILTERED_CARS_CSV}.")
        if price_changes_df.empty:
            print("No price changes compared to previous scrape.")
        else:
            price_changed_count = len(price_changes_df[price_changes_df["status"] == "price_changed"])
            removed_count = len(price_changes_df[price_changes_df["status"] == "removed"])
            if price_changed_count > 0:
                print(f"Found {price_changed_count} price change(s); see sheet '{self.config.PRICE_CHANGES_SHEET}'.")
            if removed_count > 0:
                print(f"Found {removed_count} removed car(s); saved to {self.config.REMOVED_CARS_CSV}.")

