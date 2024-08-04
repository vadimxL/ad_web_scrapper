import requests
import json


def main():
    car_color = "כסף"  #input textbox
    car_model = "ELANTRA HEV"  # ELANTRA HYBRID, ELANTRA HEV
    year = "2022"  #input textbox
    month_year_on_the_road = "2022-3"  #input textbox
    submodel = 'EXECUTIVE'
    license_plate_partial = "XXX09002"  #input textbox
    full_license_plate = "61010701"
    url = "https://data.gov.il/api/3/action/datastore_search?resource_id=053cea08-09bc-40ec-8f7a-156f0677aff3&limit=99999999"
    filters = {
        'kinuy_mishari': car_model,
        # 'tzeva_rechev': car_color,
        'shnat_yitzur': year,
        'moed_aliya_lakvish': month_year_on_the_road,
        # 'ramat_gimur': submodel
    }
    params = {'filters': json.dumps(filters)}
    response = requests.get(url, params=params)
    data = response.json()

    # for record in data["result"]["records"]:
    #     print(f'car model: {record["kinuy_mishari"]}, year: {record["shnat_yitzur"]}, month_year_on_the_road: {record["moed_aliya_lakvish"]}, license_plate: {record["mispar_rechev"]}')

    matching_license_plates = []
    if data["result"]["records"]:
        for record in data["result"]["records"]:
            full_license_plate = str(record['mispar_rechev'])
            if len(license_plate_partial) == len(full_license_plate):
                is_match = True
                for i in range(len(license_plate_partial)):
                    if license_plate_partial[i] != "X" and license_plate_partial[i] != full_license_plate[i]:
                        is_match = False
                        break
                if is_match:
                    matching_license_plates.append(record["mispar_rechev"])
    print("optinal id: " + str(matching_license_plates))


if __name__ == '__main__':
    main()
