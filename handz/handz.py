import hashlib
from datetime import timedelta
from typing import List, Dict
import json
import re
from requests_cache import CachedSession as MyCachedSession


class Handz:
    TOKEN = "62e8c1a08efe2d1fad068684"

    @staticmethod
    def parse_int(sin):
        m = re.search(r'^(\d+)[.,]?\d*?', str(sin))
        return int(m.groups()[-1]) if m and not callable(sin) else 'NaN'


    @staticmethod
    def get_prices(listings: List[Dict]):
        data = Handz.prepare_data(listings)

        url = "https://api.handz.co.il/v2.0/entities/vehicles/auth"
        headers = {'Content-Type': 'application/json'}
        # Make the POST request
        # response = requests.post("https://api.handz.co.il/v2.0/entities/vehicles/auth",
        #                          headers=headers, data=json.dumps(data))
        session = MyCachedSession('cache/handz_cache', backend='sqlite', expire_after=timedelta(hours=2))
        response = session.post(url, headers=headers, data=json.dumps(data), timeout=10)
        #
        # Parse the response as JSON and return it
        return response.json()

    @staticmethod
    def prepare_data(listings):
        # Sort the list of dictionaries based on the 'id' key
        listings.sort(key=lambda x: x['id'])
        # Concatenate the 'id' and 'price' values for each dictionary in t
        magic_string = "-vt@.%G^M-994tho.!$d"
        id_and_price = ''.join(f"{d['id']}-{Handz.parse_int(d['price'])}" for d in listings)
        # Compute the SHA512 hash of the concatenated string
        hash_result = hashlib.sha512(f'"{id_and_price}"{magic_string}'.encode()).hexdigest()
        # Prepare the request body
        data = {
            'entities': listings,
            'f': hash_result[5:15][::-1],
            's': hash_result[-5:],
            'n': hash_result[:5],
            't': Handz.TOKEN
        }
        return data


if __name__ == '__main__':
    handz = Handz()
    with open('handz_payloads.json', 'r') as f:
        payload_for_handz = json.load(f)
        result = handz.get_prices(payload_for_handz['entities'])
        print(result)
