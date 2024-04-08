from datetime import datetime


def convert_to_human_readable_date(date: str):
    date_obj = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")
    # Format the date as day-month year hour:minute
    return date_obj.strftime("%d/%m/%Y %H:%M")


def human_readable_date(items: list):
    # Example of items:
    # prices = [
    #     {
    #         "price": 119500,
    #         "date": "2023-12-06T08:35:46.531Z"
    #     },
    #     # ... (other prices)
    # ]
    for item in items:
        date_str = item['date']
        item['date'] = convert_to_human_readable_date(date_str)

    # Sort the list by date
    # sorted_data = sorted(items, key=lambda x: x['date'], reverse=True)
    sorted_data = items

    # Extract date (without hour) and price into a list of tuples
    data = [(datetime.strptime(entry['date'], '%d/%m/%Y %H:%M').strftime('%d/%m/%Y'), entry['price']) for
            entry in sorted_data]

    return [f"{date}, {price}" for date, price in data]