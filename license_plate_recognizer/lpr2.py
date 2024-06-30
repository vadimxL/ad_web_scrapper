import time

import requests
from pprint import pprint
from os import listdir
from os.path import isfile, join

def main():
    regions = ["il"]  # Change to your country
    onlyfiles = [f for f in listdir() if isfile(f) and f.endswith('.jpeg')]
    for file in onlyfiles:
        with open(file, 'rb') as fp:
            response = requests.post(
                'https://api.platerecognizer.com/v1/plate-reader/',
                data=dict(regions=regions),  # Optional
                files=dict(upload=fp),
                headers={'Authorization': 'Token caa094c4c1dd2e7ee616326ce83ead929e97042b'})

        # For files field, if needed, use imencode method of cv2 library to encode an image and producing a compressed representation that can be easier stored, transmitted, or processed.
        # import cv2
        # success, image_jpg = cv2.imencode('.jpg', fp)
        # files=dict(upload=image_jpg.tostring())

            pprint(response.json())
            time.sleep(1)


if __name__ == '__main__':
    main()