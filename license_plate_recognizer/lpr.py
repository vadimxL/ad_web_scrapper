from os import listdir
from os.path import isfile, join
import pytesseract
import easyocr
import cv2
import imutils
from ultralytics import YOLO
import numpy as np
# load models
coco_model = YOLO('yolov8n.pt')
license_plate_detector = YOLO('license_plate_detector.pt')

def read_license_plate(license_plate_crop):
    """
    Read the license plate text from the given cropped image.

    Args:
        license_plate_crop (PIL.Image.Image): Cropped image containing the license plate.

    Returns:
        tuple: Tuple containing the formatted license plate text and its confidence score.
    """
    # Initialize EasyOCR reader
    reader = easyocr.Reader(['en'])  # You can specify the language for recognition

    # Perform OCR
    detections = reader.readtext(license_plate_crop, allowlist='0123456789')

    for detection in detections:
        bbox, text, score = detection

        text = text.upper().replace(' ', '')

        if len(text) >= 7:
            return text, score

    return None, None

def recognize_license_plate(image_path):
    # Load image
    image = cv2.imread(image_path)
    results = []

    if image is None:
        return results

    vehicles = [2, 7]
    # detect vehicles
    detections = coco_model(image)[0]
    detections_ = []
    for detection in detections.boxes.data.tolist():
        x1, y1, x2, y2, score, class_id = detection
        if int(class_id) in vehicles:
            detections_.append([x1, y1, x2, y2, score])

    if not detections_:
        return results

    # crop vehicle
    # crop license plate
    i = 0
    if detections_:  # if there are detections
        x1, y1, x2, y2, score = detections_[0]
        print(f"Processing vehicle {i}, score: {score}")
        vehicle_crop = image[int(y1):int(y2), int(x1): int(x2), :]
        cv2.imwrite(image_path + f'_vehicle_crop_{i}.jpg', vehicle_crop)
        i += 1
        license_plates = license_plate_detector(vehicle_crop)[0]
        for license_plate in license_plates.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = license_plate

            # crop license plate
            license_plate_crop = vehicle_crop[int(y1):int(y2), int(x1): int(x2), :]
            # process license plate
            license_plate_crop_gray = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2GRAY)
            cv2.imwrite(image_path + f'_license_plate_crop_{i}.jpg', license_plate_crop_gray)
            # Apply Gaussian blur and adaptive thresholding for better text recognition
            blur = cv2.GaussianBlur(license_plate_crop_gray, (5, 5), 0)
            # thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            _, thresh = cv2.threshold(license_plate_crop_gray, 100, 255, cv2.THRESH_BINARY_INV)
            # read license plate number
            license_plate_text, license_plate_text_score = read_license_plate(thresh)
            if license_plate_text is not None:
                result = {'license_plate': {'bbox': [x1, y1, x2, y2],
                                            'text': license_plate_text,
                                            'bbox_score': score,
                                            'text_score': license_plate_text_score}}
                results.append(result)

        return results


def main():
    mypath = "3c3hu41q"
    only_files = [f for f in listdir(mypath) if isfile(join(mypath, f)) and f.endswith('.jpeg')]
    for image_path in only_files:
        results = recognize_license_plate(f"{mypath}/{image_path}")
        if results:
            print(f"Recognized License Plate Text {results[0]['license_plate']['text']} for {image_path}")


if __name__ == '__main__':
    main()
