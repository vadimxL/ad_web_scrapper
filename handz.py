import hashlib
import json
import logging
import sys
import requests

from handz_payloads import payload_for_handz
logging.getLogger(__name__).addHandler(logging.StreamHandler(stream=sys.stdout))
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='example.log',
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8')

def parse_int(sin):
    import re
    m = re.search(r'^(\d+)[.,]?\d*?', str(sin))
    return int(m.groups()[-1]) if m and not callable(sin) else 'NaN'


def get_pricing_from_handz(listings, token):
    # Sort the list of dictionaries based on the 'id' key
    listings.sort(key=lambda x: x['id'])
    # Concatenate the 'id' and 'price' values for each dictionary in t
    magic_string = "-vt@.%G^M-994tho.!$d"
    id_and_price = ''.join(f"{d['id']}-{parse_int(d['price'])}" for d in listings)
    # Compute the SHA512 hash of the concatenated string
    hash_result = hashlib.sha512(f'"{id_and_price}"{magic_string}'.encode()).hexdigest()

    # Prepare the request body
    data = {
        'entities': listings,
        'f': hash_result[5:15][::-1],
        's': hash_result[-5:],
        'n': hash_result[:5],
        't': token
    }

    logger.info(f"Requesting pricing from Handz with data: f={data['f'], data['s'], data['n'], data['t']}")
    handz_payload = json.dumps(data, indent=4)
    with open('handz_payload.json', 'w') as f:
        f.write(handz_payload)
    # Make the POST request
    response = requests.post("https://api.handz.co.il/v2.0/entities/vehicles/auth",
                             headers={'Content-Type': 'application/json'}, data=json.dumps(data))
    #
    # Parse the response as JSON and return it
    return response.json()


if __name__ == '__main__':
    result = get_pricing_from_handz(payload_for_handz['entities'], payload_for_handz['t'])
    print(result)
