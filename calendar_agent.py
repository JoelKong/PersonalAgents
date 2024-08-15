import os
import json
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pytz

# Scopes for google calendar API
SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar'
]

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Google calendar Authentication
def authenticate_calendar():
    creds = None
    if os.path.exists('calendartoken.json'):
        creds = Credentials.from_authorized_user_file('calendartoken.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('calendartoken.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

# Function calling to get calendar events within a specified duration
def get_events(duration=None):
    service = authenticate_calendar()
    
    now = datetime.now()
    
    if not duration:
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        time_min = start_of_week.isoformat() + 'Z'
        time_max = end_of_week.isoformat() + 'Z'
    else:
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=int(duration))).isoformat() + 'Z'

    events_result = service.events().list(
        calendarId='primary', timeMin=time_min, timeMax=time_max,
        singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    events_list = []
    for event in events:
        event_data = {
            'start': event['start'].get('dateTime', event['start'].get('date')),
            'end': event['end'].get('dateTime', event['end'].get('date')),
            'summary': event.get('summary', 'No Title'),
        }
        events_list.append(event_data)

    return json.dumps(events_list)

# Function calling to create an event in calandar
def create_event(title, start_time, end_time, description=None, location=None):
    service = authenticate_calendar()

    timezone = 'Asia/Singapore'

    tz = pytz.timezone(timezone)
    start_time = tz.localize(datetime.fromisoformat(start_time))
    end_time = tz.localize(datetime.fromisoformat(end_time))
    
    event = {
        'summary': title,
        'location': location,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'UTC',
        }
    }

    try:
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return json.dumps(f"Event created: {created_event.get('htmlLink')}")
    except Exception as e:
        return json.dumps(f"An error occurred: {e}")

# Calendar agent responsible for managing Google Calendar
def calendar_agent(content, messages):
    user_message = {"role": "user", "content": content}
    messages.append(user_message)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_events",
                "description": "Retrieves events from Google Calendar within a specified time period. Call this whenever you need information of events in the Google Calendar, for example when a user asks 'can you tell me whats going on tommorrow?' If the user does not specify a duration, use the current week.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "duration": {"type": "string", "description": "The duration in days for which to retrieve events. Must be in numeric"},
                    },
                    "required": ['duration'],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_event",
                "description": f"Schedules a new event in Google Calendar. Call this whenever you need to schedule an event in the Google Calendar, for example when a user asks 'can you help me reserve a time slot in my calendar tommorrow for this event?' You can interpret the functions required from the user if given. If not, ask the user for it. ",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "The title of the event."},
                        "start_time": {"type": "string", "description": "The start time of the event in 'YYYY-MM-DDTHH:MM:SS' format."},
                        "end_time": {"type": "string", "description": "The end time of the event in 'YYYY-MM-DDTHH:MM:SS' format."},
                        "description": {"type": "string", "description": "The description of the event."},
                        "location": {"type": "string", "description": "The location of the event."},
                    },
                    "required": ["title", "start_time", "end_time", "description", "location"],
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
            "get_events": get_events,
            "create_event": create_event
        }
        for tool_call in tool_calls:
            print(f"Calendar agent is calling function: {tool_call.function.name} with params {tool_call.function.arguments}")
            function_to_call = available_functions[tool_call.function.name]
            function_args = json.loads(tool_call.function.arguments)

            if function_to_call == get_events:
                function_response = function_to_call(duration=function_args.get('duration'))
            elif function_to_call == create_event:
                function_response = function_to_call(title=function_args.get('title'), start_time=function_args.get('start_time'), end_time=function_args.get('end_time'), description=function_args.get('description'), location=function_args.get('location'))

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
