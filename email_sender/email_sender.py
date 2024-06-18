import json
import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

from car_details import CarDetails
from criteria_model import html_criteria_mail

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class EmailSender:
    def __init__(self) -> None:
        pass

    def send(self, msg_content: str, subject: str = "Automated draft"):
        load_dotenv()
        # Define the subject and body of the email.
        body = msg_content
        # Define the sender's email address.
        sender: str = os.environ.get("SENDER_EMAIL")
        # List of recipients to whom the email will be sent.
        recipients: list = json.loads(os.environ.get("RECIPIENTS_EMAIL"))
        # Password for the sender's email account.
        password = os.environ.get("EMAIL_PASSWORD")

        # Create a MIMEText object with the body of the email.
        msg = MIMEText(body, 'html')
        # Set the subject of the email.
        msg['Subject'] = subject
        # Set the sender's email.
        msg['From'] = sender
        # Join the list of recipients into a single string separated by commas.
        msg['To'] = ', '.join(recipients)

        # Connect to Gmail's SMTP server using SSL.
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            # Login to the SMTP server using the sender's credentials.
            smtp_server.login(sender, password)
            # Send the email. The sendmail function requires the sender's email, the list of recipients, and the email message as a string.
            smtp_server.sendmail(sender, recipients, msg.as_string())
        # Print a message to console after successfully sending the email.
        print("Message sent!")


if __name__ == "__main__":
    gmail_sender = EmailSender()
    car_ad_db = {
        "manufacturer": "Toyota",
        "car_model": "Corolla",
        "city": "Tel Aviv"
    }

    # msg = gmail_sender.create_html_msg("Toyota", "פרטי", "Corolla", "2019", "50", "100000", "120000", "2021-09-01")
    car_details = CarDetails(id="123456", manuf_en="Toyota", manuf_he="טויוטה", car_model="Corolla", year="2019", price="100000", prices=[],
                             date_added_epoch="2323232", date_added="2021-09-01", feed_source="yad2")
    msg = html_criteria_mail(car_details)
    gmail_sender.send(msg, f'🎁 [New] - {car_ad_db["manufacturer"]} {car_ad_db["car_model"]} {car_ad_db["city"]}')
    # gmail_sender.send(msg, f'⬇️ [Update] - {car_ad_db["manufacturer"]} {car_ad_db["car_model"]} {car_ad_db["city"]}')
