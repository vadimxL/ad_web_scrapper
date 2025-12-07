#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import List, Optional


class Config:
    """Configuration constants"""
    URL = ("https://www.opl.co.il/%D7%9E%D7%9B%D7%99%D7%A8%D7%AA_%D7%A8%D7%9B%D7%91/"
           "%D7%9E%D7%A6%D7%90_%D7%A8%D7%9B%D7%91"
           "?manufacturer=&year%5B0%5D=&year%5B1%5D=&price%5B0%5D=&price%5B1%5D=&gear=")

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    COLUMNS = ["manufacturer", "model", "year", "km", "transmission", "color", "price", "license_plate",
               "gov_manufacturer", "gov_tokef_dt", "gov_last_test_dt", "gov_baalut", "zmig_kidmi", "zmig_ahori"]
    
    OUT_PATH = Path("opl_cars.xlsx")
    OUT_CSV_PATH = Path("opl_cars.csv")
    PRICE_CHANGES_SHEET = "price_changes"
    PRICE_CHANGES_CSV = Path("opl_price_changes.csv")
    REMOVED_CARS_CSV = Path("opl_removed_cars.csv")
    FILTERED_CARS_CSV = Path("opl_filtered_cars.csv")
    
    KEY_COLUMNS = ["manufacturer", "model", "year", "km", "transmission", "color"]
    PRICE_DIFF_COLUMNS = KEY_COLUMNS + ["price_previous", "price", "price_change", "status"]
    
    EXCLUDED_MANUFACTURERS: List[str] = ["סיטרואן", "שברולט", "פיג'ו", "MG", "רנו", "AIWAYS", "ניסאן"]  # Add manufacturer names to exclude (case-insensitive)
    EXCLUDED_MODELS: List[str] = ["פיקנטו", "i10", "2 1.5 DYNAMIC", "i20"]  # Add model names to exclude (case-insensitive, partial matching supported)
    MIN_YEAR: Optional[int] = 2022  # Minimum year to include (cars with year < MIN_YEAR will be filtered out). Set to None to disable.

