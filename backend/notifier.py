from logging import Logger

from backend.car_details import CarDetails
from backend.criteria_model import html_criteria_mail
from backend.email.email_sender import EmailSender


class Notifier:
    def __init__(self, email_sender: EmailSender, recipients: list[str], logger: Logger):
        self._email = email_sender
        self._log = logger
        self._recipients = recipients

    def new_car_ad(self, ad: CarDetails):
        try:
            msg = html_criteria_mail(ad)
            subject = f'🎁 {ad.manufacturer_he} {ad.car_model} {ad.city}'
            self._email.send(msg, self._recipients, subject)
        except Exception as e:
            self._log.error(f"Error sending new ad email: {e}")

    def updated_car_ad(self, new_ad: CarDetails):
        try:
            msg = html_criteria_mail(new_ad)
            last_price = new_ad.prices[-1].price
            prev_price = new_ad.prices[-2].price if len(new_ad.prices) > 1 else last_price
            arrow = '⬇️' if last_price < prev_price else '⬆️'
            subject = f'{arrow} {new_ad.manufacturer_he} {new_ad.car_model} {new_ad.city}'
            self._email.send(msg, self._recipients, subject)
        except Exception as e:
            self._log.error(f"Error sending updated ad email: {e}")

    def removed_car_ad(self, ad: CarDetails):
        try:
            msg = html_criteria_mail(ad)
            subject = f'💸 {ad.manufacturer_he} {ad.car_model} {ad.city}'
            self._email.send(msg, self._recipients, subject)
        except Exception as e:
            self._log.error(f"Error sending removed ad email: {e}")
