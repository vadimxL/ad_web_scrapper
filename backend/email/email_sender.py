import smtplib
from email.mime.text import MIMEText
from typing import List

from dotenv import load_dotenv

from backend.car_details import CarDetails
from backend.criteria_model import html_criteria_mail
from backend.logger_setup import ads_updates_logger

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class EmailSender:
    def __init__(self, sender_email: str, sender_pw: str) -> None:
        self._sender_email = sender_email
        self._sender_pw = sender_pw
        pass

    def send(self, msg_content: str, recipient: List[str], subject: str = "Automated draft"):
        load_dotenv()
        # Define the subject and body of the email.
        body = msg_content
        # Define the sender's email address.

        sender: str = self._sender_email
        # Password for the sender's email account.
        password: str = self._sender_pw

        # Create a MIMEText object with the body of the email.
        msg = MIMEText(body, 'html')
        # Set the subject of the email.
        msg['Subject'] = subject
        # Set the sender's email.
        msg['From'] = sender
        # Join the list of recipients into a single string separated by commas.
        msg['To'] = ', '.join(recipient)

        # Connect to Gmail's SMTP server using SSL.
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            # Login to the SMTP server using the sender's credentials.
            smtp_server.login(sender, password)
            # Send the email. The sendmail function requires the sender's email, the list of recipients, and the email message as a string.
            smtp_server.sendmail(sender, recipient, msg.as_string())
        # Print a message to console after successfully sending the email.
        ads_updates_logger.info("Message sent!, check your inbox for the email.")


if __name__ == "__main__":
    gmail_sender = EmailSender()
    car_ad_db = {
        "manufacturer": "Toyota",
        "car_model": "Corolla",
        "city": "Tel Aviv"
    }

    full_info = {'images_urls': [
        "https://img.yad2.co.il/Pic/202407/14/1_3/o/y2_1pa_010241_20240714150746.jpeg",
        "https://img.yad2.co.il/Pic/202407/14/1_3/o/y2_1pa_010438_20240714150745.jpeg",
        "https://img.yad2.co.il/Pic/202407/14/1_3/o/y2_1pa_010226_20240714150745.jpeg",
        "https://img.yad2.co.il/Pic/202407/14/1_3/o/y2_1pa_010449_20240714150745.jpeg",
        "https://img.yad2.co.il/Pic/202407/14/1_3/o/y2_1pa_010414_20240714150745.jpeg"
      ]}

    # msg = mail_sender.create_html_msg("Toyota", "פרטי", "Corolla", "2019", "50", "100000", "120000", "2021-09-01")
    car_details = CarDetails(id="123456", manuf_en="Toyota", manuf_he="טויוטה", car_model="Corolla", year="2019", price="100000", prices=[],
                             date_added_epoch="2323232", date_added="2021-09-01", feed_source="private",
                             prices_handz="2024-06-17 123500| 2024-06-17 23500| 2024-06-15 118000| 2024-06-13 122000| 2024-06-11 None",
                             month_on_road="2024-06-17", test_date="2024-06-17", city="Tel Aviv", kilometers="120000", hand="2",
                             full_info=full_info)
    msg = html_criteria_mail(car_details)
    gmail_sender.send(msg, "vadimski30@gmail.com", f'🎁 [New] - {car_ad_db["manufacturer"]} {car_ad_db["car_model"]} {car_ad_db["city"]}')
    # mail_sender.send(msg, f'⬇️ [Update] - {car_ad_db["manufacturer"]} {car_ad_db["car_model"]} {car_ad_db["city"]}')
