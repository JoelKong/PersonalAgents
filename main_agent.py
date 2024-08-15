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
import pyaudio
import wave
import keyboard

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Main Agent Jarvis responsible for handling my queries and communicates between its sub agents to deliver functions with proficiency
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
                            "description": "The request which needs to be fulfilled by the email agent.",
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
                            "description": "The request which needs to be fulfilled by the calendar agent.",
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
                "description": "Handles tasks related to searching for information on the web and retrieving information from screenshots, such as retrieving information about a person or getting data online or finding information in a screenshot. Call this whenever the user wants navigate to a website or to search for something or get his school timetable or get something from the page you navigated to, for example when a person asks 'what is my timetable like for this week?'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The request which needs to be fulfilled by the scrapper agent.",
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

            
            if function_to_call == email_agent:
                function_response = function_to_call(content=function_args.get('content'), messages=messages_email)
            elif function_to_call == calendar_agent:
                function_response = function_to_call(content=function_args.get('content'), messages=messages_calendar)
            elif function_to_call == scrapper_agent:
                function_response = await function_to_call(content=function_args.get('content'), messages=messages_scrapper, page=page)
            
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

# Record audio for speech to text
def record_audio(filename="prompt.wav"):
    chunk = 1024
    sample_format = pyaudio.paInt16
    channels = 1
    fs = 44100
    p = pyaudio.PyAudio()
    
    stream = p.open(format=sample_format,
                    channels=channels,
                    rate=fs,
                    frames_per_buffer=chunk,
                    input=True)

    frames = []

    while keyboard.is_pressed('space'):
        data = stream.read(chunk)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(sample_format))
        wf.setframerate(fs)
        wf.writeframes(b''.join(frames))

    return filename

# Transcribe the recorded audio file using OpenAI Whisper
def transcribe_audio(filename):
    with open(filename, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file, language="en")
    return transcript.text

def handle_input():
    while True:
        if keyboard.read_event().name == 't':
            content = input("User: ")
            return content
        elif keyboard.is_pressed('space'):
            audio_file = record_audio()
            content = transcribe_audio(audio_file)
            print(f"User: {content}")
            return content
        elif keyboard.is_pressed('q'):
            print("Exiting the program...")
            return "exit"

# Enable playwright for scrapping ability
async def main():
    if os.path.exists("screenshot.jpg"):
        os.remove("screenshot.jpg")
    async with async_playwright() as p:
        user_data_dir = "C:/Users/Joel/AppData/Local/Google/Chrome/User Data"
        browser = await p.chromium.launch_persistent_context(user_data_dir, channel="chrome", headless=False)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})
        print("Press 't' to type a message, Hold/Release 'spacebar' to record a message or stop recording respectively, or 'q' to quit:")

        try:
            while True:
                content = handle_input()
                if content == "exit":
                    await browser.close()
                    break

                response = await main_agent(content, page)
                print(f"Jarvis: {response}")

        except KeyboardInterrupt:
            print("Program interrupted. Exiting...")
            await browser.close()


if __name__ == "__main__":
    date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    messages = []
    messages_email = [{"role": "system", "content": "You are an email assistant helping out a main agent whose role is to assist his creator named Joel. You have the ability to analyze, summarize and send emails. Ignore emails with low importance and just briefly shift them into categories like 'ads and spam'. You must list down important emails and reccomendations that the user can take based off these emails only if they are really important. Use the supplied tools to assist the user."}]
    messages_calendar = [{"role": "system", "content": f"You are an Calendar assistant helping out a main agent whose role is to assist his creator named Joel. Your main responsibility is to manage and organize events. Use the supplied tools to assist the user. Take note that the current date and time is {date_time}."}]
    messages_scrapper = [{"role": "system", "content": "You are a smart information gatherer assistant helping out a main agent whose role is to assist his creator named Joel. You have the ability to control Playwright to interact with the web such as navigating, clicking, going back to the previous page, simulating key strokes, typing, scrolling. Your main goal is to aid to provide a synopsis of information to your main agent once you have found it on the web. Use the supplied tools to assist the user. Each time you use a tool, a screenshot of the page with currently clickable objects drawn by a red box is shown to you as well as the selectors of the interactable elements. You can then 'click' through by choosing the appriopriate html selector to use. When you reached you destination, always rely and prioritise on the screenshot to get information and give a synopsis of that information back and do not scrape it fully unless specified by the user. If you are doing a google search, prioritise the first result that pops up unless specified and select the correct clickable html tag. Take note that the website to see the timetable is at https://in4sit.singaporetech.edu.sg/psc/CSSISSTD/EMPLOYEE/SA/c/NUI_FRAMEWORK.PT_LANDINGPAGE.GBL followed by clicking Course Management and My Weekly Schedule."}]
    system_message = {"role": "system", "content": """You are a helpful personal assistant named Jarvis and helping out your owner Joel with his needs. You resemble the personality and talking style of the Jarvis from Iron Man. You have a few helper agents that are more proficient in performing a specific task. Use the tools supplied to you if necessary and decide which agent to use for a specified task.
                        The list of agents includes the email_agent whose responsibilities include anything related to email management, calendar_agent whose responsibilities include anything related to calendar management."""}
    messages.append(system_message)
    asyncio.run(main())