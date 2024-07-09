import models
from jinja2 import Environment, select_autoescape, FileSystemLoader
env = Environment(
    loader=FileSystemLoader(f"{models.ROOT_DIR}/templates"),
    autoescape=select_autoescape(['html', 'xml'])
)
from flask import url_for


def html_criteria_mail(car_details: models.AdDetails) -> str:
    with open(f"{models.ROOT_DIR}/templates/criteria_mail.html", "r") as f:
        criteria_mail = f.read()
        # print(criteria_mail)
    template = env.get_template("criteria_mail.html")

    # Transforming the list to a single human-readable string
    human_readable_str = ""
    for history in car_details.prices:
        date_str = history.date.strftime("%B %d, %Y")
        human_readable_str += f"On {date_str}, the price was {history.price} NIS.\n"

    if len(car_details.prices) > 0:
        initial_price = car_details.prices[0].price
    else:
        initial_price = "N/A"

    return template.render(id=car_details.id,
                           manufacturer=car_details.manuf_en,
                           hand=car_details.hand,
                           model=car_details.car_model,
                           year=car_details.year,
                           km=car_details.kilometers,
                           price=car_details.price,
                           gear_type=car_details.gear_type,
                           free_text=human_readable_str.strip(),
                           initial_price=initial_price,
                           date_created=car_details.date_added,
                           prices_handz=car_details.prices_handz,
                           test_date=car_details.test_date,
                           month_on_road=car_details.month_on_road,
                           url_for=url_for)

