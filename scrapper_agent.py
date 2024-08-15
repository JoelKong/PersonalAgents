import os
import re
import base64
import json
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from openai import OpenAI
import time
from bs4 import BeautifulSoup

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Some websites have certain illegal characters in their html tags so we need to escape them
def escape_selector(selector: str) -> str:
    return re.sub(r'(\$)', r'\\\1', selector)

# Function to take a screenshot of the page and save it
async def take_screenshot(page):
    screenshot = await page.screenshot()
    image = Image.open(BytesIO(screenshot))
    image.save("screenshot.jpg")

# Function to encode the image for GPT Vision to read
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
# Function to highlight and return clickable elements in red boxes for gpt to see what it can click
async def highlight_clickables(page):
    interactable_elements = await page.evaluate('''() => {
        const elements = document.querySelectorAll('div[id="win0divPTNUI_LAND_REC_GROUPLET$1"], div[ptgpid="ADMN_S201801281809025135349589"], span[id="submitButton"], a, button, input, textarea[id="APjFqb"]');
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

# Function call to navigate to a webpage
async def navigate(link, page):
    await page.goto(link)
    time.sleep(5)
    interactable_elements = await highlight_clickables(page)
    await take_screenshot(page)
    return json.dumps(f"Navigated to {link} successfully! The interactable elements are {interactable_elements}")

# Function call for gpt to click on a selector
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
            time.sleep(5)
            interactable_elements = await highlight_clickables(page)
            await take_screenshot(page)
            return json.dumps(f"Clicked on element successfully! The interactable elements are {interactable_elements}")
        except Exception as e:
            continue
    return json.dumps("Failed to click on any of the elements.")

# Function call for gpt to type on keyboard
async def type_on_keyboard(selector, text, page):
    escaped_selector = escape_selector(selector)
    await page.fill(escaped_selector, text)
    await page.wait_for_load_state('networkidle')
    interactable_elements = await highlight_clickables(page)
    await take_screenshot(page)
    return json.dumps(f"Typed text into {selector} successfully! The interactable elements are {interactable_elements}.")

# Function call for gpt to simulate hitting enter to submit forms or go to next page
async def enter(page):
    await page.keyboard.press('Enter')
    await page.wait_for_load_state('load')
    time.sleep(5)
    interactable_elements = await highlight_clickables(page)
    await take_screenshot(page)
    return json.dumps(f"Pressed Enter successfully! The interactable elements are {interactable_elements}")

# Function call to go back to the previous page
async def go_back(page):
    await page.go_back()
    await page.wait_for_load_state('load')
    time.sleep(5)
    interactable_elements = await highlight_clickables(page)
    await take_screenshot(page)
    return json.dumps(f"Navigated back to the previous page successfully! The interactable elements are {interactable_elements}.")

# Function call for gpt to 'scroll' up or down by 100vh to see a new instance of the page to get more information
async def scroll(page, direction):
    if direction == "up":
        await page.evaluate('''() => {
            window.scrollBy(0, -window.innerHeight);
        }''')
    else:
        await page.evaluate('''() => {
            window.scrollBy(0, window.innerHeight);
        }''')
    await page.wait_for_load_state('load')
    time.sleep(5)
    interactable_elements = await highlight_clickables(page)
    await take_screenshot(page)
    return json.dumps(f"Scrolled {direction} by 100vh successfully!  The interactable elements are {interactable_elements}.")


# Function call for gpt to scrape the full contents of the page (for now only when user specified as it can be quite expensive as i will be inserting the whole body tag into the prompt)
async def scrape_page(page):
    body_content = await page.evaluate('''() => {
        return document.body.innerHTML;
    }''')

    soup = BeautifulSoup(body_content, 'html.parser')
    content = soup.get_text()
    clean_content = re.sub(r'<[^>]*>', '', content)

    return clean_content

# Scrapper agent responsible for navigating the web and retrieving information
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
                            "description": "The html selector that you wish to select to click. The selector must be in the format of tag[attribute='']",
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
                "description": "Navigate to a website on the web. Call this whenever you need to go to a certain website to investigate it, for example when the user requests to search for something on the web you can go to google.com. The website link must be provided and can be interpretted by you if possible. Default to google.com. The selector must be in the format of tag[attribute='']",
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
                "description": "Type on the keyboard in a specific html selector. Call this whenever you need to type something, for example when you want to fill up an input field. The text information to be filled up must be provided unless it can be interpretted by you. The html selector to type on must also be selected by you given the information on the interactable elements. The selector must be in the format of tag[attribute='']",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text you would like to type.",
                        },
                        "selector": {
                            "type": "string",
                            "description": "The html selector that you wish to select to type in. The selector must be in the format of tag[attribute='']",
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
                "name": "go_back",
                "description": "Return back to the previous page of the website. Call this whenever you want to go back to the previous page of where you navigated to.",
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
                "name": "scroll",
                "description": "Scroll up or down to the next instance of the page where your window cant display at the moment. Call this whenever you require more information and want to explore more on the page to extract out more information or when the user asks you to do so.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "description": "The direction you would like to scroll. Either 'up' or 'down'",
                        },
                    },
                    "required": ["direction"],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "scrape_page",
                "description": "Scrape the whole body content of the page. Call this only when the user specifies that he wants the full page information.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            }
        }
    ]

    # Loop until gpt decides that it is satisfied with the screenshot hence stop using the tools provided
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
                "go_back": go_back,
                "scroll": scroll,
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
                elif function_to_call == go_back:
                    function_response = await function_to_call(page=page)
                elif function_to_call == scroll:
                    function_response = await function_to_call(page=page, direction=function_args.get('direction'))
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
