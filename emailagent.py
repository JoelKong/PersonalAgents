import os
import re
import json
from openai import OpenAI
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Load env keys
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Remove URLs, images, and special characters from the text.
def clean_text(text):
    text = re.sub(r'http\S+|www.\S+', '', text)
    
    text = re.sub(r'<.*?>', '', text)
    
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

# Gmail Authentication
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

# Function calling to get emails based off a time period the user specifies
def get_emails(day):
    service = authenticate_gmail()
    query = f'newer_than:{day}d'
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
    
    emails = []
    for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = {header['name']: header['value'] for header in msg['payload']['headers']}

            email_data = {
                'message_id': msg['id'],
                'thread_id': msg['threadId'],
                'date': headers.get('Date', ''),
                'from': headers.get('From', ''),
                'subject': headers.get('Subject', ''),
                'body': clean_text(msg.get('snippet', '')),
            }
            emails.append(email_data)

    return json.dumps(emails)

# Function calling to send or reply to an email based off what the user wnats
def send_email(receiver, subject, body, message_id = None, thread_id = None):
    service = authenticate_gmail()
    message = MIMEText(body)
    message['to'] = receiver
    message['subject'] = subject

    if (thread_id and message_id):
        message['in-reply-to'] = message_id
        message['references'] = message_id
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        raw_message = {
            'raw': raw_message,
            'threadId': thread_id
        }
    else:
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        raw_message = {'raw': raw_message}

    try:
        message = service.users().messages().send(userId='me', body=raw_message).execute()
        return json.dumps("Message successfully sent!")
    except Exception as e:
        print(f"An error occurred: {e}")

# Email agent responsible for managing my emails
def email_agent(content):
    user_message = {"role": "user", "content": content}
    messages.append(user_message)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_emails",
                "description": "Retrieves all emails that are sent me in a given time period. Call this whenever you need access to my emails that are sent to me, for example when a person asks 'I need an analysis of my emails'. The number of days of email to check must be specified by the user unless you are able to interpret it from the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "day": {
                            "type": "string",
                            "description": "The number of days worth of email the user wishes to check in numerical format.",
                        },
                    },
                    "required": ["day"],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_email",
                "description": "Sends an email to the specified receiver. Call this whenever you need to send an email, for example when a person asks 'Can you help me to email john about the meeting?'. The receiver must be specifically mentioned by the user and you can interpret the subject and body by yourself unless you require more information. If the user wants to reply to an email thread, use the message id and thread id that is provided to you for that particular email.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "receiver": {"type": "string", "description": "The email address of the receiver."},
                        "subject": {"type": "string", "description": "The subject of the email."},
                        "body": {"type": "string", "description": "The body of the email."},
                        "message_id": {"type": "string", "description": "The message id of the email"},
                        "thread_id": {"type": "string", "description": "The thread id of the email chain."},
                    },
                    "required": ["receiver", "subject", "body", "message_id", "thread_id"],
                },
            }
        },
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    result = response.choices[0].message
    tool_calls = result.tool_calls

    if tool_calls:
        messages.append(result)
        available_functions = {
            "get_emails": get_emails,
            "send_email": send_email
        }
        for tool_call in tool_calls:
            print(f"Email agent is calling function: {tool_call.function.name} with params {tool_call.function.arguments}")
            function_to_call = available_functions[tool_call.function.name]
            function_args = json.loads(tool_call.function.arguments)

            if function_to_call == send_email:
                function_response = function_to_call(receiver=function_args.get('receiver'), subject=function_args.get('subject'), body=function_args.get('body'), message_id=function_args.get('message_id'), thread_id=function_args.get('thread_id'))
            elif function_to_call == get_emails:
                function_response = function_to_call(day=function_args.get('day'))

            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": tool_call.function.name,
                "content": function_response
            })


        second_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )

        second_result = second_response.choices[0].message

        return second_result.content
    
    return result.content

if __name__ == "__main__":
    messages = []
    system_message = {"role": "system", "content": "You are an email assistant helping out a main agent whose role is to assist his creator named Joel. You have the ability to analyze, summarize and send emails. You must categorise the emails based off their importance and state reccomendations that the user can take based off these emails only if they are really important. Use the supplied tools to assist the user. Give your response in plain text and exclude special HTML entities or encoded characters in your response or email. "}
    messages.append(system_message)
    while True:
        content = input("")
        response = email_agent(content)
        print(response)