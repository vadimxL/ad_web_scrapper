import hashlib
import json
import requests

from handz_payloads import payload_for_handz


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
    # Make the POST request
    r = {'error': 'Failed to get pricing from Handz'}
    try:
        response = requests.post("https://api.handz.co.il/v2.0/entities/vehicles/auth",
                                 headers={'Content-Type': 'application/json'}, data=json.dumps(data))
        r = response.json()
    except Exception as e:
        print(e)
    finally:
        return r


if __name__ == '__main__':
    result = get_pricing_from_handz(payload_for_handz['entities'], payload_for_handz['t'])
    print(result)
