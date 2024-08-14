from datetime import datetime
import json
import os
from email_agent import email_agent
from calendar_agent import calendar_agent
from openai import OpenAI
from dotenv import load_dotenv

# Load env keys
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def main_agent(content):
    user_message = {"role": "user", "content": content}
    messages.append(user_message)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "email_agent",
                "description": "Handles tasks related to emails, such as retrieving and sending emails. Call this whenever the user needs any form of email management, for example when a person asks 'Analyse my emails this week.'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The user's request related to emails.",
                        },
                    },
                    "required": ["content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "calendar_agent",
                "description": "Handles tasks related to the calendar, such as retrieving events and scheduling new ones. Call this whenever the user needs any form of calendar management, for example when a person asks 'Can you schedule an event for Thursday?'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The user's request related to calendar events.",
                        },
                    },
                    "required": ["content"],
                },
            },
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
            "email_agent": email_agent,
            "calendar_agent": calendar_agent,
        }

        for tool_call in tool_calls:
            print(f"Calling {tool_call.function.name} to help out with your request...")
            function_to_call = available_functions[tool_call.function.name]
            function_args = json.loads(tool_call.function.arguments)
            
            # Append the user message to the correct queue
            if function_to_call == email_agent:
                function_response = function_to_call(content=function_args.get('content'), messages=messages_email)
            elif function_to_call == calendar_agent:
                function_response = function_to_call(content=function_args.get('content'), messages=messages_calendar)
            
            # Append the function response to the global messages
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
    date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    messages = []
    messages_email = [{"role": "system", "content": "You are an email assistant helping out a main agent whose role is to assist his creator named Joel. You have the ability to analyze, summarize and send emails. Ignore emails with low importance and just briefly shift them into categories like 'ads and spam'. You must list down important emails and reccomendations that the user can take based off these emails only if they are really important. Use the supplied tools to assist the user. Give your response in plain text and exclude special HTML entities or encoded characters in your response or email. "}]
    messages_calendar = [{"role": "system", "content": f"You are an Calendar assistant helping out a main agent whose role is to assist his creator named Joel. Your main responsibility is to manage and organize events. Use the supplied tools to assist the user. Take note that the current date and time is {date_time}."}]
    system_message = {"role": "system", "content": """You are a helpful personal assistant named Jarvis and helping out your owner Joel with his needs. You resemble the personality and talking style of the Jarvis from Iron Man. You have a few helper agents that are more proficient in performing a specific task. Use the tools supplied to you if necessary and decide which agent to use for a specified task.
                        The list of agents includes the email_agent whose responsibilities include anything related to email management, calendar_agent whose responsibilities include anything related to calendar management."""}
    messages.append(system_message)
    while True:
        content = input("User: ")
        response = f"Jarvis: {main_agent(content)}"
        print(response)
