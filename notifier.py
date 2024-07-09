from datetime import datetime, timedelta

import models
from email_sender.email_sender import EmailSender
from criteria_model import html_criteria_mail
from loguru import logger


class Notifier:
    def __init__(self, mail_sender: EmailSender):
        self.sender = mail_sender

    def notify_new_ad(self, ad: models.AdDetails):
        try:
            diff: timedelta = datetime.now() - ad.date_added
            minutes = diff.total_seconds() / 60
            logger.info(f'{ad.id} {ad.manufacturer_he} {ad.car_model} {ad.city}, Total difference in '
                        f'minutes: {minutes}, difference: {diff}')
            if minutes > 60:
                logger.info(f"New ad is older than 60 minutes, skipping email notification")
                return
            message = html_criteria_mail(ad)
            self.sender.send(message, f'🎁 [New] - {ad.manufacturer_he} {ad.car_model} {ad.city}')
        except Exception as e:
            logger.error(f"Error sending email: {e}")

    def notify_archived(self, ads):
        for ad in ads:
            message = html_criteria_mail(ad)
            self.sender.send(message, f'💸 [Sold] - {ad.manufacturer_he} {ad.car_model} {ad.city}')

    def notify_update_ad(self, ad: models.AdDetails):
        try:
            message = html_criteria_mail(ad)
            last_price = ad.prices[-1].price
            previous_price = ad.prices[-2].price
            if last_price < previous_price:
                subject = f'⬇️ [Update] - {ad.manufacturer_he} {ad.car_model} {ad.city}'
            else:
                subject = f'⬆️ [Update] - {ad.manufacturer_he} {ad.car_model} {ad.city}'

            self.sender.send(message, subject)
        except Exception as e:
            logger.error(f"Error sending email: {e}")
