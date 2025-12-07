#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import time
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup

from oplease.config import Config


class WebScraper:
    """Handles web scraping and API requests"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def fetch_html(self, url: str) -> BeautifulSoup:
        """Fetch HTML content from URL"""
        resp = requests.get(url, headers=self.config.HEADERS, timeout=30)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    def fetch_gov_vehicle_data_batch(self, license_plates: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch official vehicle data from Israeli government data.gov.il API in batches"""
        if not license_plates:
            return {}

        # Clean license plates
        license_plates_clean = [lp for lp in license_plates if lp]
        if not license_plates_clean:
            return {}

        # data.gov.il API endpoint for vehicle data
        url = "https://data.gov.il/api/3/action/datastore_search"

        result_dict: Dict[str, Dict[str, Any]] = {}
        batch_size = 215

        # Process in batches
        for i in range(0, len(license_plates_clean), batch_size):
            batch = license_plates_clean[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(license_plates_clean) + batch_size - 1) // batch_size

            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} license plates)...")

            # Create proper JSON filter for this batch
            params = {
                "resource_id": "053cea08-09bc-40ec-8f7a-156f0677aff3",
                "filters": json.dumps({"mispar_rechev": batch}, separators=(",", ":")),
                "limit": 32000
            }

            try:
                response = requests.get(url, params=params, headers=self.config.HEADERS, timeout=60)
                response.raise_for_status()

                data = response.json()

                if not data.get("success"):
                    print(f"Warning: Government API request was not successful for batch {batch_num}")
                    continue

                records = data.get("result", {}).get("records", [])

                # Add records from this batch to result dictionary
                # requests-cache automatically caches HTTP responses
                batch_results = 0
                for record in records:
                    license_plate = str(record.get("mispar_rechev", ""))
                    if license_plate:
                        result_dict[license_plate] = {
                            "gov_manufacturer": record.get("tozeret_nm", ""),
                            "gov_tokef_dt": record.get("tokef_dt", ""),
                            "gov_last_test_dt": record.get("mivchan_acharon_dt", ""),
                            "gov_baalut": record.get("baalut", ""),
                            "zmig_kidmi": record.get("zmig_kidmi", ""),
                            "zmig_ahori": record.get("zmig_ahori", ""),
                        }
                        batch_results += 1

                print(f"  Found {batch_results} records in batch {batch_num}")

                # Add delay between batches to be respectful to the API
                # Skip delay if response was from cache
                if i + batch_size < len(license_plates_clean) and not getattr(response, 'from_cache', False):
                    time.sleep(2)

            except requests.exceptions.RequestException as exc:
                print(f"Warning: Could not fetch government vehicle data for batch {batch_num}: {exc}")
                continue
            except Exception as exc:
                print(f"Warning: Unexpected error fetching government data for batch {batch_num}: {exc}")
                continue

        print(f"Successfully fetched government data for {len(result_dict)} out of {len(license_plates_clean)} vehicles total")
        return result_dict

