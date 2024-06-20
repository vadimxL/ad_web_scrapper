import jinja2

from car_details import CarDetails

criteria_mail = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Title</title>
</head>
<body>
<table align="center" border="0" cellpadding="0" cellspacing="0" width="100%"
       style="border-collapse:collapse;max-width:600px!important">
    <tbody>
    <tr>
        <td valign="top"
            style="background:transparent none no-repeat center/cover;border-top:0;border-bottom:0;padding-top:0;padding-bottom:0">
            <table border="0" cellpadding="0" cellspacing="0" width="100%"
                   style="min-width:100%;border-collapse:collapse">
                <tbody>
                <tr>
                    <td valign="top" style="padding-top:9px">
                        <table style="max-width:100%;min-width:100%;border-collapse:collapse">
                            <tbody>
                            <tr>
                                <td valign="top"
                                    style="padding:0 18px 9px;word-break:break-word;color:#808080;font-family:Helvetica,serif;font-size:16px;line-height:150%">
                                    <h3 style="display:block;margin:0;padding:0;color:#444444;font-family:Helvetica,serif;font-size:22px;font-style:normal;font-weight:bold;line-height:150%;letter-spacing:normal">
                                        <span style="font-family:arial,helvetica neue,helvetica,sans-serif">{{manufacturer}}</span>
                                    </h3>
                                    <ul>
                                        <li>
                                            <span style="font-family:arial,helvetica neue,helvetica,sans-serif">id: {{id}}</span>
                                        </li>
                                        <li><span
                                                style="font-family:arial,helvetica neue,helvetica,sans-serif">date created: {{date_created}}</span>
                                        </li>
                                        <li><span
                                                style="font-family:arial,helvetica neue,helvetica,sans-serif">hand: {{hand}}</span>
                                        </li>
                                        <li><span
                                                style="font-family:arial,helvetica neue,helvetica,sans-serif">year: {{year}}</span>
                                        </li>
                                        <li><span
                                                style="font-family:arial,helvetica neue,helvetica,sans-serif">gear: {{gear_type}}</span>
                                        </li>
                                        <li><span
                                                style="font-family:arial,helvetica neue,helvetica,sans-serif">model: {{model}}</span>
                                        </li>
                                        <li><span
                                                style="font-family:arial,helvetica neue,helvetica,sans-serif">mileage: {{km}} [km]</span>
                                        </li>
                                        <ul>
                                            {% for item in free_text.split('\n') %}
                                            <li><span
                                                    style="font-family:arial,helvetica neue,helvetica,sans-serif">{{item}}</span>
                                            </li>
                                            {% endfor %}
                                        </ul>
                                    </ul>
                                    <div>
                                        <span style="font-family:arial,helvetica neue,helvetica,sans-serif">
                                           <span style="font-family:arial,helvetica neue,helvetica,sans-serif">
                                               <strong>price: {{price}}&nbsp;</strong>
                                               <span style="font-size:14px">initial price: {{initial_price}}</span>
                                           </span>
                                       </span>
                                    </div>
                                </td>
                            </tr>
                            </tbody>
                        </table>
                    </td>
                </tr>
                </tbody>
            </table>
            <table border="0" cellpadding="0" cellspacing="0" width="100%"
                   style="min-width:100%;border-collapse:collapse">
                <tbody>
                <tr>
                    <td style="padding: 0 18px 18px;" valign="top"
                        align="center">
                        <table border="0" cellpadding="0" cellspacing="0"
                               style="border-collapse:separate!important;border-radius:3px;background-color:#00add8">
                            <tbody>
                            <tr>
                                <td align="center" valign="middle"
                                    style="font-family:Helvetica,serif;font-size:18px;padding:18px">
                                    <a title="צפיה בפרטים המלאים"
                                       href="https://www.yad2.co.il/vehicles/item/{{id}}"
                                       style="font-weight:bold;letter-spacing:-0.5px;line-height:100%;text-align:center;text-decoration:none;color:#ffffff;display:block"
                                       target="_blank"
                                       >צפיה בפרטים המלאים</a>
                                </td>
                            </tr>
                            </tbody>
                        </table>
                    </td>
                </tr>
                </tbody>
            </table>
        </td>
    </tr>
    </tbody>
</table>
</body>
</html>"""


def html_criteria_mail(car_details: CarDetails):
    environment = jinja2.Environment()
    template = environment.from_string(criteria_mail)

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
                           date_created=car_details.date_added)
