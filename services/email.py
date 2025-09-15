import os
import base64
from email.mime.text import MIMEText
from typing import List, Dict, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.compose']

class GmailClient:
    def __init__(self):
        self.creds = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate the user and create the Gmail API client."""
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

    def send_email(self, recipient, subject, body):
        """Send an email to the specified recipient."""
        service = build('gmail', 'v1', credentials=self.creds)
        message = MIMEText(body)
        message['to'] = recipient
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        message = {'raw': raw_message}
        return service.users().messages().send(userId='me', body=message).execute()

    def get_draft(self, recipient, subject, body):
        """Return draft content without sending."""
        draft_content = f"To: {recipient}\nSubject: {subject}\n\n{body}"
        return draft_content

    def check_for_replies(self, thread_id: str) -> List[Dict[str, Any]]:
        """Check for new replies in a given thread."""
        service = build('gmail', 'v1', credentials=self.creds)
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        return thread['messages']

if __name__ == "__main__":
    gmail_client = GmailClient()
    # Example usage
    # gmail_client.send_email('recipient@example.com', 'Test Subject', 'Test Body')
    # print(gmail_client.get_draft('recipient@example.com', 'Test Subject', 'Test Body'))