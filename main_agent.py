from datetime import datetime
import json
import os
from email_agent import email_agent
from calendar_agent import calendar_agent
from scrapper_agent import scrapper_agent
from openai import OpenAI
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import asyncio

# Load env keys
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Main Agent Jarvis
async def main_agent(content, page):
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
        {
            "type": "function",
            "function": {
                "name": "scrapper_agent",
                "description": "Handles tasks related searching for information on the web, such as retrieving information about a person or getting data online. Call this whenever the user wants to search for something or get his school timetable, for example when a person asks 'what is my timetable like for this week?'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The user's request related to retrieving information online",
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
            "scrapper_agent": scrapper_agent
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
            elif function_to_call == scrapper_agent:
                function_response = await function_to_call(content=function_args.get('content'), messages=messages_scrapper, page=page)
            
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

async def main():
    async with async_playwright() as p:
        user_data_dir = "C:/Users/Joel/AppData/Local/Google/Chrome/User Data"
        browser = await p.chromium.launch_persistent_context(user_data_dir, channel="chrome", headless=False)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})

        try:
            while True:
                content = input("User: ")
                if content.lower() == "exit":
                    print("Exiting the program...")
                    break
                response = await main_agent(content, page)
                print(f"Jarvis: {response}")

        except KeyboardInterrupt:
            print("Program interrupted. Exiting...")

        finally:
            await browser.close()
            if os.path.exists("screenshot.jpg"):
                os.remove("screenshot.jpg")


if __name__ == "__main__":
    date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    messages = []
    messages_email = [{"role": "system", "content": "You are an email assistant helping out a main agent whose role is to assist his creator named Joel. You have the ability to analyze, summarize and send emails. Ignore emails with low importance and just briefly shift them into categories like 'ads and spam'. You must list down important emails and reccomendations that the user can take based off these emails only if they are really important. Use the supplied tools to assist the user. Give your response in plain text and exclude special HTML entities or encoded characters in your response or email. "}]
    messages_calendar = [{"role": "system", "content": f"You are an Calendar assistant helping out a main agent whose role is to assist his creator named Joel. Your main responsibility is to manage and organize events. Use the supplied tools to assist the user. Take note that the current date and time is {date_time}."}]
    messages_scrapper = [{"role": "system", "content": "You are a smart information gatherer assistant helping out a main agent whose role is to assist his creator named Joel. You have the ability to control Playwright to interact with the web such as navigating or clicking and also aiding to provide synopsis of information to your main agent on details once you have completed your navigation around the web. Use the supplied tools to assist the user. Each time you use a tool, a screenshot of the page with clickable objects drawn by a red box is shown to you as well as the selectors of the interactable elements. You can then 'click' through by choosing the appriopriate html selector to use. If the selector has a dollar sign in it, add a backslash before it to escape the dollar sign. When you reached you destination, always rely and prioritise on the screenshot to get information and give a synopsis of that information back and do not scrape it fully unless specified. If you are doing a google search, prioritise the first result in the screenshot that pops up unless specified and select the correct clickable html tag. Take note of the following website links for your information: School management website which contains information about the student such as his timetable can be found at https://in4sit.singaporetech.edu.sg/psc/CSSISSTD/EMPLOYEE/SA/c/NUI_FRAMEWORK.PT_LANDINGPAGE.GBL"}]
    system_message = {"role": "system", "content": """You are a helpful personal assistant named Jarvis and helping out your owner Joel with his needs. You resemble the personality and talking style of the Jarvis from Iron Man. You have a few helper agents that are more proficient in performing a specific task. Use the tools supplied to you if necessary and decide which agent to use for a specified task.
                        The list of agents includes the email_agent whose responsibilities include anything related to email management, calendar_agent whose responsibilities include anything related to calendar management."""}
    messages.append(system_message)
    asyncio.run(main())
