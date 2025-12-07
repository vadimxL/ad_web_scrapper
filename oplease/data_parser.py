#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from typing import Optional

import pandas as pd


class DataParser:
    """Utility functions for parsing text and numbers"""
    
    @staticmethod
    def clean_text(s: Optional[str]) -> str:
        return re.sub(r"\s+", " ", s or "").strip()

    @staticmethod
    def parse_int(s: Optional[str]) -> Optional[int]:
        if s is None:
            return None
        if isinstance(s, int):
            return s
        s = str(s).replace(",", "").replace("\u200f", "").strip()
        m = re.findall(r"\d+", s)
        return int(m[0]) if m else None

    @staticmethod
    def parse_price(s: Optional[str]) -> Optional[int]:
        if not s:
            return None
        s = s.replace(",", "")
        m = re.findall(r"\d+", s)
        return int("".join(m)) if m else None

    @staticmethod
    def to_nullable_int(series: pd.Series) -> pd.Series:
        return pd.to_numeric(series, errors="coerce").astype("Int64")

