# Personal Agents
A team of AI agents that work together to assist the user to achieve his needs. (Email management, Schedule/Calendar management, Web exploration/scraping)

## Demo
Insert utube link here

## Application Code
### Technology Stack
Back-End: Python   
Tools used: GPT Vision, GPT Function Calling, GPT speech to text whisper model, Gmail and Google Calendar API, Playwright for web manipulation, BeautifulSoup for scraping

## System Workflow and Function Calling
When our user first requests something, the main agent "Jarvis" who plays the role as a personal assistant will decide whether it is a request that it can fulfill such as "Hey jarvis, what do you think of me?". If the user wants something that cant be fulfilled with Jarvis alone, Jarvis will call its sub agents for help, namely the email agent who is responsible for email management, calendar agent who is responsible for calendar management and the scrapper agent who is responsible for performing web related activities.  

The sub agents itself also have functions they can call and these functions help them become who they are. By using their functions, they are able to perform their roles accurately and assist the user. This would then be reflected back to Jarvis on the outcome of the task and finally back to the user.

![workflow](/assets/workflow.PNG)

## Concept of AI Agents and separation of duties
The current GPT model can hallucinate easily when overwhelmed with different tasks and not return with the best results. AI agents are specialised in certain areas of work such as a chatbot to manage your finances or a bot who takes down notes in a meeting. Some agents are even personally trained to better improve the model to fit their agent role. Hence, by allowing agents to specialise into a certain role, they are able to have functions related to their roles to carry out and therefore deliver the best result.

## Current Agents and Functions
### Main Agent Jarvis
Able to call its sub agents to perform tasks that it is not specialised to do. Think of Jarvis as an all in one to help you get through your day.

![jarvis](/assets/jarvis.PNG)

### Email Agent
The role of the email agent is to facilitate email management. It integrates hand in hand with the gmail api and currently has 2 functions. The first function is the ability to get the user's emails depending on the number of the days worth of email the user wishes to check. The second function is the ability to send or reply to emails. Even though a lot of information is needed for an email to be sent manually, the email agent can interpret it from the prompt that you gave if it is not specified or reprompt the user back again for more information. 

![emailagent](/assets/emailagent.PNG)

### Calendar Agent
The role of the calendar agent is to facilitate schedule management. It integrates hand in hand with the google calendar api and currently has 2 functions. The first function is the ability to fetch events from the user's google calendar within a specified time period that the user specifies or the agent interprets. The second function is the ability to create an event in the calendar. Similary, the agent could reprompt the user for more details to add in the event or interpret it by itself based off the conversation history.

![calendaragent](/assets/calendaragent.PNG)

### Scraper Agent
The role of the scraper agent is to interact and explore around the web, scraping and gathering information for the user. It is one of the more complicated agents to come up with as we know that AI models cant see or interact with web pages. However, web automation technologies like Playwright and GPT Vision makes this possible. Everytime the agent "interacts" with the screen with its functions by filtering for common clickable tags like buttons or anchors on the current viewport, the system draws a red border over them and takes a screenshot to convert it to base64. The base64 image is then passed to gpt vision along with the string of elements that are highlighted in the boxes to aid as description. This allows the model to understand where it is currently at and what it can act on next. 

It integrates with Playwright for web navigation and BeautifulSoup for more organised scraping. Its functions are similar to the way we humans navigate the web. It includes clicking, navigating, typing on the keyboard, hitting the enter key to submit a form, going back to the previous page, scrolling up or down and scraping the page.

You might ask: why go through so much trouble when you can just web scrape normally? Well, normal web scraping is targeted towards a certain website or area and cant go beyond that without doing more work. With this agent, it is able to make use of its intelligence along with some human touch to explore webpages whereever it deems to suit the user's everchanging needs. With a personalised trained model targeted in improving that "human touch", this would have a lot of potential.

![scrapperagent](/assets/scrapperagent.PNG)

## Speech to text
By integrating the openai whisper API, you can speak into the mic if you are lazy to type and it will transcribe it for you and return to the jarvis agent.

## Reflection, Limitations and Potential
It may be quite costly as the agents are prompting each other back and forth before returning a finalised answer to the user and slower than a regular prompt due to the numerous API calls made. Especially for the scraper agent, even though only necessary elements in the DOM are being pasted for the model to understand, it can still take up a lot of tokens. Moreover, since it is not personally trained, it might sometimes hallucinate along the way by selecting a wrong html tag to interact with.

Working on this project made me realise the power and untapped potential of AI Agents as they have the power to do so much things and automate our daily life. Beyond webpages, even advanced automation systems like RPA can be integrated with AI expand the different possibilities of what we can create. Hence, I am looking forward to creating more of such projects and start to think of what else i can automate in other people's lives.

## How to run locally
clone the repository
pip install requirements.txt
Create a google cloud project with google calendar and gmail, set scopes and import credentials.json
Change the user_data_dir variable in main_agent.py to match your google chrome directory
run main agent.py (remember to close your browser before running)

