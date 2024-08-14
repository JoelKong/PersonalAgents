import os
import re
import base64
import json
from playwright.async_api import async_playwright
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from openai import OpenAI
import time

# Load environment variables for OpenAI API
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def escape_selector(selector: str) -> str:
    # Escape the dollar sign and any other special characters as needed
    return re.sub(r'(\$)', r'\\\1', selector)

# Function to take a screenshot and save it
async def take_screenshot(page):
    screenshot = await page.screenshot()
    image = Image.open(BytesIO(screenshot))
    image.save("screenshot.jpg")

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
# Function to highlight clickable elements
async def highlight_clickables(page):
    interactable_elements = await page.evaluate('''() => {
        const elements = document.querySelectorAll('div[id^="win0divPTNUI_LAND_REC_GROUPLET"], li[id^="win1divPTGP_STEPS_L1_row"], a, button, input, textarea');
        const visibleElements = [];

        elements.forEach(element => {
            const rect = element.getBoundingClientRect();
            const inViewport = (
                rect.top >= 0 &&
                rect.left >= 0 &&
                rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                rect.right <= (window.innerWidth || document.documentElement.clientWidth)
            );

            if (inViewport) {
                element.style.border = '2px solid red';
                visibleElements.push(element.outerHTML);
            }
        });

        return visibleElements;
    }''')

    return interactable_elements

# # Function to highlight clickable elements
# async def highlight_clickables(page):
#     patterns = [
#         'win0divPTNUI_LAND_REC_GROUPLET',  # Explicitly include this prefix
#         'DERIVED_CLASS_S_SSR_DISP_TITLE',
#         'DERIVED_CLASS_S_SSR_REFRESH_CAL',
#         '^win\\d+divPTGP_STEP_DVW_PTGP_STEP_BTN_GB'  # Regex pattern for other IDs
#     ]

#     interactable_elements = await page.evaluate('''(patterns) => {
#         function matchesPattern(id, pattern) {
#             // Check if the pattern is a regex or a specific string
#             if (pattern.startsWith('^')) {
#                 // Regex pattern
#                 const regex = new RegExp(pattern);
#                 return regex.test(id);
#             } else {
#                 // Specific string
#                 return id.startsWith(pattern);
#             }
#         }

#         const elements = document.querySelectorAll('a, button, input, textarea');
#         const visibleElements = [];

#         elements.forEach(element => {
#             const id = element.id;
#             const rect = element.getBoundingClientRect();
#             const inViewport = (
#                 rect.top >= 0 &&
#                 rect.left >= 0 &&
#                 rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
#                 rect.right <= (window.innerWidth || document.documentElement.clientWidth)
#             );

#             if (inViewport && (id === '' || patterns.some(pattern => matchesPattern(id, pattern)))) {
#                 element.style.border = '2px solid red';
#                 visibleElements.push(element.outerHTML);
#             }
#         });

#         return visibleElements;
#     }''', patterns)

#     return interactable_elements

async def navigate(link, page):
    await page.goto(link)
    time.sleep(5)
    interactable_elements = await highlight_clickables(page)
    await take_screenshot(page)
    return json.dumps(f"Navigated to {link} successfully! The interactable elements are {interactable_elements}")


async def click(selector, page):
    escaped_selector = escape_selector(selector)
    locators = page.locator(escaped_selector)
    count = await locators.count()

    for i in range(count):
        element = locators.nth(i)
        try:
            await element.wait_for(state='visible')
            await element.click()
            await page.wait_for_load_state('load')

            # Check if the page navigation or action was successful
            time.sleep(5)
            interactable_elements = await highlight_clickables(page)
            await take_screenshot(page)
            return json.dumps(f"Clicked on element successfully! The interactable elements are {interactable_elements}")
        except Exception as e:
            continue

    return json.dumps("Failed to click on any of the elements.")

async def type_on_keyboard(selector, text, page):
    escaped_selector = escape_selector(selector)
    await page.fill(escaped_selector, text)
    await page.wait_for_load_state('networkidle')
    interactable_elements = await highlight_clickables(page)
    await take_screenshot(page)
    return json.dumps(f"Typed text into {selector} successfully! The interactable elements are {interactable_elements}.")

async def enter(page):
    await page.keyboard.press('Enter')
    await page.wait_for_load_state('load')
    time.sleep(5)
    interactable_elements = await highlight_clickables(page)
    await take_screenshot(page)
    return json.dumps(f"Pressed Enter successfully! The interactable elements are {interactable_elements}")

async def scrape_page(page):
    body_content = await page.evaluate('''() => {
        return document.body.innerHTML;
    }''')

    return body_content

# Function to navigate to the timetable page
async def scrapper_agent(content, messages, page):
    user_message = {"role": "user", "content": content}
    messages.append(user_message)
    satisfied = False

    tools = [
        {
            "type": "function",
            "function": {
                "name": "click",
                "description": "Click on a clickable element on the web. Call this whenever you need to navigate around a website, for example when you need to click a button to access a certain page. The html selector that you wish to click must be provided. The interactable elements will be provided for you to decide which selector to use",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "The html selector that you wish to select to click.",
                        },
                    },
                    "required": ["selector"],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "navigate",
                "description": "Navigate to a website on the web. Call this whenever you need to go to a certain website to investigate it, for example when the user requests to search for something on the web you can go to google.com. The website link must be provided and can be interpretted by you if possible.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "link": {
                            "type": "string",
                            "description": "The link of the website you wish to visit.",
                        },
                    },
                    "required": ["link"],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "type_on_keyboard",
                "description": "Type on the keyboard in a specific html selector. Call this whenever you need to type something, for example when you want to fill up an input field. The text information to be filled up must be provided unless it can be interpretted by you. The html selector to type on must also be selected by you given the information on the interactable elements.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text you would like to type.",
                        },
                        "selector": {
                            "type": "string",
                            "description": "The html selector that you wish to select to type in.",
                        },
                    },
                    "required": ["text", "selector"],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "enter",
                "description": "Simulate pressing the Enter key on the current focus. Call this whenever you are done filling up information and ready to proceed to the next page. This action is used to submit forms or trigger actions that require pressing Enter.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "scrape_page",
                "description": "Call this only when the user specifies that he wants the full page information.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            }
        }
    ]

    while not satisfied:
        if os.path.exists("screenshot.jpg"):
            base64_image = encode_image("screenshot.jpg")
            messages.append({"role": "user", "content": [
                {"type": "text", "text": f"This is the current view of where you are in the website as well as its clickable elements surrounded by the red boxes."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpg;base64,{base64_image}"}}
            ]})

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
                "click": click,
                "navigate": navigate,
                "type_on_keyboard": type_on_keyboard,
                "enter": enter,
                "scrape_page": scrape_page
            }
            for tool_call in tool_calls:
                print(f"Smart scrapper agent is calling function: {tool_call.function.name} with params {tool_call.function.arguments}")
                function_to_call = available_functions[tool_call.function.name]
                function_args = json.loads(tool_call.function.arguments)

                if function_to_call == navigate:
                    function_response = await function_to_call(link=function_args.get('link'), page=page)
                elif function_to_call == click:
                    function_response = await function_to_call(selector=function_args.get('selector'), page=page)
                elif function_to_call == type_on_keyboard:
                    function_response = await function_to_call(selector=function_args.get('selector'), text=function_args.get('text'), page=page)
                elif function_to_call == enter:
                    function_response = await function_to_call(page=page)
                elif function_to_call == scrape_page:
                    function_response = await function_to_call(page=page)

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": function_response
                })
            continue
        else:
            satisfied = True

        second_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )

        second_result = second_response.choices[0].message

        return second_result.content
    
    return result.content

# if __name__ == "__main__":
#     messages = []
#     system_message = {"role": "system", "content": "You are a smart information gatherer assistant helping out a main agent whose role is to assist his creator named Joel. You have the ability to control Playwright to interact with the web such as navigating or clicking and also aiding to provide synopsis of information to your main agent on details once you have completed your navigation around the web. Use the supplied tools to assist the user. Each time you use a tool, a screenshot of the page with clickable objects drawn by a red box is shown to you as well as the selectors of the interactable elements. You can then 'click' through by choosing the appriopriate html selector to use. When you reached you destination, always rely and prioritise on the screenshot to get information and give a synopsis of that information back and do not scrape it fully unless specified. If you are doing a google search, prioritise the first result in the screenshot that pops up unless specified and select the correct clickable html tag. Take note of the following website links for your information: School management website which contains information about the student such as his timetable can be found at https://in4sit.singaporetech.edu.sg/"}
#     messages.append(system_message)
#     while True:
#         content = input("")
#         response = asyncio.run(scrapper_agent(content, messages))
#         print(response)
