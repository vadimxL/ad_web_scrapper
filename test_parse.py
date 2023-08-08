import json
import unittest

from scraper import extract_car_details


class MyTestCase(unittest.TestCase):
    def test_parse(self):
        car_items = []
        file_name = 'parsed_yad2_2023-07-31_11-17-54'
        with open(file_name + '.json') as f:
            items = json.load(f)
            for item in items:
                car_details = extract_car_details(item)
                car_items.append(car_details)

        with open('short_parsed_yad2_2023-07-31_10-54-40.json', 'w') as f:
            json.dump(car_items, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    unittest.main()
