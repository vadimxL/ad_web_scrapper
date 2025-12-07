#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List, Dict, Any, Tuple

from bs4 import BeautifulSoup

from oplease.config import Config
from oplease.data_parser import DataParser
from oplease.web_scraper import WebScraper


class CarParser:
    """Parses HTML to extract car data"""
    
    def __init__(self, config: Config, web_scraper: WebScraper, data_parser: DataParser):
        self.config = config
        self.web_scraper = web_scraper
        self.data_parser = data_parser

    def parse_list_table(self, soup: BeautifulSoup) -> Tuple[Optional[List[Dict[str, Any]]], List[Dict[str, Any]]]:
        """Parse list-based table structure using ul/li with aria-label attributes
        Returns: (rows, filtered_rows) where filtered_rows are excluded manufacturers
        """
        rows: List[Dict[str, Any]] = []
        filtered_rows: List[Dict[str, Any]] = []
        license_plates: List[str] = []

        # Find all li elements with role="row" that contain car data
        car_lis = soup.find_all("li", {"role": "row"})

        # First pass: collect all data except government data
        for li in car_lis:
            # Skip header rows or li elements without proper structure
            if not li.get("id") or not li.get("id").startswith("deal"):
                continue

            # Create a mapping of aria-label to text content
            aria_data: Dict[str, str] = {}

            # Find all divs with aria-label within this li
            aria_divs = li.find_all("div", {"aria-label": True})
            for div in aria_divs:
                aria_label = div.get("aria-label", "").strip()
                text_content = self.data_parser.clean_text(div.get_text(" ", strip=True))
                if aria_label and text_content:
                    aria_data[aria_label] = text_content

            # Also look for data attributes in buttons/links
            data_elements = li.find_all(attrs={"data-car": True})
            data_licence = None
            data_price = None

            if data_elements:
                element = data_elements[0]
                data_licence = element.get("data-licence", "").strip()
                data_price = element.get("data-price", "").strip()

            def pick_by_aria(hebrew_key: str) -> str:
                return aria_data.get(hebrew_key, "")

            # Special handling for manufacturer - it's in an <a> tag with aria-label="יצרן"
            manufacturer = ""
            manufacturer_links = li.find_all("a", {"aria-label": "יצרן"})
            if manufacturer_links:
                manufacturer = self.data_parser.clean_text(manufacturer_links[0].get_text(" ", strip=True))

            model: str = pick_by_aria("דגם")
            year: Optional[int] = self.data_parser.parse_int(pick_by_aria("שנה"))
            km: Optional[int] = self.data_parser.parse_int(pick_by_aria("ק״מ"))
            transmission: Optional[str] = pick_by_aria("הילוכים") or pick_by_aria("גיר") or None
            color: Optional[str] = pick_by_aria("צבע") or None

            # Try to get price from aria-label first, then from data-price
            price_text = pick_by_aria("מחיר מכירה") or pick_by_aria("מחיר") or data_price or ""
            price: Optional[int] = self.data_parser.parse_price(price_text)

            # Get license plate from data-licence
            license_plate = data_licence if data_licence else None

            # Track excluded manufacturers and models (case-insensitive comparison)
            # For models, partial matching is supported (e.g., "Corolla" matches "Toyota Corolla")
            is_excluded = False
            if self.config.EXCLUDED_MANUFACTURERS and manufacturer:
                manufacturer_lower = manufacturer.lower().strip()
                if any(excluded.lower().strip() == manufacturer_lower for excluded in self.config.EXCLUDED_MANUFACTURERS):
                    is_excluded = True
            
            if not is_excluded and self.config.EXCLUDED_MODELS and model:
                model_lower = model.lower().strip()
                if any(excluded.lower().strip() in model_lower for excluded in self.config.EXCLUDED_MODELS):
                    is_excluded = True
            
            # Filter out cars below minimum year
            if not is_excluded and self.config.MIN_YEAR is not None and year is not None:
                if year < self.config.MIN_YEAR:
                    is_excluded = True

            if manufacturer and model and year:
                car_data = {
                    "manufacturer": manufacturer,
                    "model": model,
                    "year": year,
                    "km": km,
                    "transmission": transmission,
                    "color": color,
                    "price": price,
                    "license_plate": license_plate,
                    # Placeholders for government data
                    "gov_manufacturer": "",
                    "gov_tokef_dt": "",
                    "gov_last_test_dt": "",
                    "gov_baalut": "",
                    "zmig_kidmi": "",
                    "zmig_ahori": "",
                }
                
                if is_excluded:
                    filtered_rows.append(car_data)
                else:
                    rows.append(car_data)
                
                # Collect license plates for batch processing (for both filtered and non-filtered cars)
                if license_plate:
                    license_plates.append(license_plate)

        if not rows and not filtered_rows:
            return None, []

        # Batch fetch government data for all license plates (both filtered and non-filtered cars)
        if license_plates:
            print(f"Fetching government data for {len(license_plates)} vehicles...")
            gov_data_dict = self.web_scraper.fetch_gov_vehicle_data_batch(license_plates)

            # Update rows with government data
            for row in rows:
                license_plate = row.get("license_plate")
                if license_plate and license_plate in gov_data_dict:
                    gov_data = gov_data_dict[license_plate]
                    # Update row with all government data keys dynamically
                    row.update(gov_data)
            
            # Update filtered_rows with government data
            for row in filtered_rows:
                license_plate = row.get("license_plate")
                if license_plate and license_plate in gov_data_dict:
                    gov_data = gov_data_dict[license_plate]
                    # Update row with all government data keys dynamically
                    row.update(gov_data)

        return rows, filtered_rows

