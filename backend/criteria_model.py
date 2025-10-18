from flask import url_for
from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.car_details import ROOT_DIR, CarDetails

env = Environment(
    loader=FileSystemLoader(f"{ROOT_DIR}/templates"),
    autoescape=select_autoescape(['html', 'xml'])
)


def html_criteria_mail(car_details: CarDetails):
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



    images_links = []
    try:
        if 'images_urls' in car_details.full_info:
            img: str
            for img in car_details.full_info['images_urls']:
                images_links.append(img + "?c=8")
            # images_links: list = car_details.full_info['images_urls']
    except Exception as e:
        print(f"Error getting images: {e}")
        print(f"Full info: {car_details}")

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
                           images_url=images_links,
                           url_for=url_for)


def html_task_created(task):
    """
    Render an HTML email summarizing the newly created alert (task).
    """
    template = env.get_template("task_created.html")
    params = task.params or {}
    model = params.get("model") or "Any"
    sub_model = params.get("subModel") or "Any"
    year = params.get("year", "N/A")
    km = params.get("km", "N/A")
    manufacturers = task.manufacturers or []
    return template.render(
        title=task.title,
        email=task.mail,
        manufacturers=manufacturers,
        model=model,
        sub_model=sub_model,
        year=year,
        km=km,
        created_at=task.created_at.strftime("%Y-%m-%d %H:%M"),
        active=task.active,
    )
