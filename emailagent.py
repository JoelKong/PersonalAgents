import os
import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from openai import OpenAI
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def clean_text(text):
    """Remove URLs, images, and special characters from the text."""
    # Remove URLs
    text = re.sub(r'http\S+|www.\S+', '', text)
    
    # Remove HTML tags
    text = re.sub(r'<.*?>', '', text)
    
    # Remove non-ASCII characters and excessive spaces
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def is_today(email_date):
    """Check if the email date is today."""
    email_date = parsedate_to_datetime(email_date)
    now = datetime.now()
    return email_date.date() == now.date()

def authenticate_gmail():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def get_today_emails(service):
    query = 'newer_than:1d'
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
    
    emails = []
    for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = {header['name']: header['value'] for header in msg['payload']['headers']}

            if is_today(headers.get('Date', '')):
                email_data = {
                    'date': headers.get('Date', ''),
                    'from': headers.get('From', ''),
                    'subject': headers.get('Subject', ''),
                    'body': clean_text(msg.get('snippet', '')),
                }
                emails.append(email_data)

    return emails

def main():
    service = authenticate_gmail()
    emails = get_today_emails(service)
    print(emails)

    # for email in emails:
    #     print(email)
    
    # important_emails = []
    # for email in emails:
    #     result = analyze_email(email)
    #     if result['important']:
    #         important_emails.append({'summary': result['summary'], 'email': email})
    
    # print("Important Emails:")
    # for imp_email in important_emails:
    #     print(f"Summary: {imp_email['summary']}")
    #     print(f"Original: {imp_email['email']['body']}\n")

if __name__ == '__main__':
    main()

# def analyze_email_content(email_body):
#     """Use OpenAI to analyze sentiment and summarize the email."""
#     response = openai.ChatCompletion.create(
#         model="gpt-4-0613",
#         messages=[
#             {"role": "system", "content": "You are an email assistant that analyzes and summarizes emails."},
#             {"role": "user", "content": f"Analyze this email and tell me if it's important: {email_body}"}
#         ],
#         functions=[
#             {
#                 "name": "determine_importance_and_summarize",
#                 "description": "Determines if an email is important and summarizes it.",
#                 "parameters": {
#                     "type": "object",
#                     "properties": {
#                         "important": {"type": "boolean"},
#                         "summary": {"type": "string"},
#                     },
#                     "required": ["important", "summary"]
#                 }
#             }
#         ],
#         function_call="auto"
#     )
#     result = response['choices'][0]['message']['function_call']['arguments']
#     return json.loads(result)

# def fetch_and_analyze_emails():
#     """Main function to fetch and analyze today's emails."""
#     service = authenticate_gmail()
#     emails = get_today_emails(service)
    
#     important_emails = []
#     for email in emails:
#         result = analyze_email_content(email['body'])
#         if result['important']:
#             important_emails.append({'summary': result['summary'], 'email': email})
    
#     return important_emails
