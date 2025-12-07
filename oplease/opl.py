#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main entry point for OPL car scraper"""
import requests_cache
from oplease import CarScraper

# Configure requests-cache with 1 hour expiration
requests_cache.install_cache('opl_cache', expire_after=3600)


def main() -> None:
    scraper = CarScraper()
    scraper.run()


if __name__ == "__main__":
    main()
