import json
import unittest


class MyTestCase(unittest.TestCase):
    def test_parse(self):
        car_items = []
        file_name = 'test'
        with open(file_name + '.json') as f:
            items = json.load(f)
            for item in items:
                pass
                # car_details = extract_car_details(item)
                # car_items.append(car_details)

        with open(f'{test}.json', 'w') as f:
            json.dump(car_items, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    unittest.main()
