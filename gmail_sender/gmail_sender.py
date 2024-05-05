import base64
from email.message import EmailMessage
import os
from google.auth.transport.requests import Request
import jinja2
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# load_dotenv()
#
# MY_ENV_VAR = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
#
# import google.auth
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class GmailSender:
    def __init__(self, credentials_path: str = "credentials.json"):
        self.creds = self._credentials(credentials_path)

    @staticmethod
    def _credentials(credentials_path: str):
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        return creds

    def send(self, msg_content: str, subject: str = "Automated draft"):
        """
        Create and send an email message
        Print the returned  message id
        Returns: Message object, including message id
        """
        try:
            service = build("gmail", "v1", credentials=self.creds)
            message = EmailMessage()

            message.set_content(msg_content)
            message.add_alternative(msg_content, subtype="html")

            message["To"] = "vadimski30@gmail.com"
            message["From"] = "malinvadim88@gmail.com"
            message["Subject"] = subject

            # encoded message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            create_message = {"raw": encoded_message}
            # pylint: disable=E1101
            send_message = (
                service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )
            print(f'Message Id: {send_message["id"]}')
        except HttpError as error:
            print(f"An error occurred: {error}")
            send_message = None
        return send_message


if __name__ == "__main__":
    gmail_sender = GmailSender()
    car_ad_db = {
        "manufacturer": "Toyota",
        "car_model": "Corolla",
        "city": "Tel Aviv"
    }

    msg = gmail_sender.create_html_msg("Toyota", "פרטי", "Corolla", "2019", "50", "100000", "120000", "2021-09-01")
    gmail_sender.send(msg, f'🎁 [New] - {car_ad_db["manufacturer"]} {car_ad_db["car_model"]} {car_ad_db["city"]}')
    # gmail_sender.send(msg, f'⬇️ [Update] - {car_ad_db["manufacturer"]} {car_ad_db["car_model"]} {car_ad_db["city"]}')
