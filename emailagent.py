import os
import re
from datetime import datetime
import json
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

def get_emails(day):
    query = f'newer_than:{day}'
    service = authenticate_gmail()
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
    
    emails = []
    for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = {header['name']: header['value'] for header in msg['payload']['headers']}

            email_data = {
                'date': headers.get('Date', ''),
                'from': headers.get('From', ''),
                'subject': headers.get('Subject', ''),
                'body': clean_text(msg.get('snippet', '')),
            }
            emails.append(email_data)

    return json.dumps(emails)

def email_analysis_agent(content):
    user_message = {"role": "user", "content": content}
    messages.append(user_message)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_emails",
                "description": "Retrieves all emails that are sent me in a given time period. Call this whenever you need access to my emails that are sent to me, for example when a person asks 'I need an analysis of my emails'. The number of days of email must be specified by the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "day": {
                            "type": "string",
                            "description": "The number of days worth of email the user wishes to check in the format of '[number]d'",
                        },
                    },
                    "required": ["day"],
                },
            }
        }
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
            "get_emails": get_emails
        }
        for tool_call in tool_calls:
            print(f"Calling function: {tool_call.function.name} with params {tool_call.function.arguments}")
            function_to_call = available_functions[tool_call.function.name]
            function_args = json.loads(tool_call.function.arguments)
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
    system_message = {"role": "system", "content": "You are an email assistant that analyzes and summarizes emails. You can also categorise the emails based off their importance and state reccomendations or after actions that the user can take based off these emails only if they are really important. Use the supplied tools to assist the user. Give your response in plain text. "}
    messages.append(system_message)
    while True:
        content = input("")
        response = email_analysis_agent(content)
        print(response)