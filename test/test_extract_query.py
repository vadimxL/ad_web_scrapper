import unittest
from urllib import parse

import models
from main import extract_query_params
from scraper import BASE_API_URL


class MyTestCase(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, False)  # add assertion here

    def test_extract_query(self):
        url_to_scrape = f"{BASE_API_URL}?manufacturer=48&model=3866,2829,3484&year=2019--1&km=-1-80000"
        params = extract_query_params(url_to_scrape)
        self.assertEqual(params, {"manufacturer": "48", "model": "3866,2829,3484", "year": "2019--1", "km": "-1-80000"})

    def split_and_filter(self, data, field, separator):
        # Split the field on the specified separator
        parts = data[field].split(separator)

        # Filter and convert parts to integers, ignoring non-integer values
        filtered_parts = []
        for part in parts:
            try:
                # Convert the part to an integer
                num = int(part)
                filtered_parts.append(num)
            except ValueError:
                # Ignore parts that cannot be converted to an integer
                continue

        # Return the filtered list of integers
        return filtered_parts

    def get_range(self, data: str) -> models.Range:
        # Split the data on the separator
        parts = data.split('-')
        parts = [int(part) for part in parts if part.isdigit()]
        parts = [part * -1 if part == 1 else part for part in parts]
        range = models.Range(min=parts[0], max=parts[1])
        return range

    def test_create_criteria_from_query(self):
        url_to_scrape = f"{BASE_API_URL}?manufacturer=48&model=3866,2829,3484&year=2019--1&km=-1-80000"
        params = extract_query_params(url_to_scrape)
        criteria = models.CarCriteria(manufacturer=params['manufacturer'],
                                      models=params['model'].split(','),
                                      year=self.get_range(params['year']),
                                      km=self.get_range(params['km']))
        print(criteria)

    def test_url_split(self):
        url = f"{BASE_API_URL}?manufacturer=48&model=3866,2829,3484&year=2019--1&km=-1-80000"

        print(parse.urlsplit(url).query)


if __name__ == '__main__':
    unittest.main()
