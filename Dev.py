import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
import requests
import datetime
import wikipedia

# 1. Load API Key
load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def make_json_safe(data):
    """Recursively cleans ALL data so JSON never crashes again."""
    if isinstance(data, bytes):
        return data.decode('utf-8', errors='ignore') 
    elif isinstance(data, dict):
        return {k: make_json_safe(v) for k, v in data.items()} 
    elif isinstance(data, list):
        return [make_json_safe(item) for item in data] 
    elif isinstance(data, (str, int, float, bool, type(None))):
        return data 
    else:
        # If it is a weird Google SDK object, force it to be a string!
        return str(data)

def get_weather(location: str) -> str:
    """Returns the REAL-TIME weather for a given location."""
    try:
        # We hit a free public weather API that accepts city names
        print(f"\n[System: SnarkBot is fetching live data for {location}...]\n")
        url = f"https://wttr.in/{location}?format=Condition:+%C,+Temperature:+%t"
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            return response.text # Example return: "Condition: Clear, Temperature: +15°C"
        else:
            return "Tell the user the weather API is currently down."
            
    except Exception as e:
        return f"Tell the user there was an error connecting to the internet: {e}"

def get_current_time() -> str:
    """Returns the current date and time."""
    print("\n[System: SnarkBot is checking the clock...]\n")
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_crypto_price(coin_id: str) -> str:
    """Returns the current USD price of a cryptocurrency (e.g., 'bitcoin', 'ethereum', 'dogecoin')."""
    print(f"\n[System: SnarkBot is checking the live price of {coin_id}...]\n")
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id.lower()}&vs_currencies=usd"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if coin_id.lower() in data:
                return f"The current price of {coin_id} is ${data[coin_id.lower()]['usd']}"
        return "Tell the user the crypto price could not be found."
    except Exception as e:
        return f"Error fetching price: {e}"

def search_wikipedia(query: str) -> str:
    """Searches Wikipedia and returns a short summary of the topic."""
    print(f"\n[System: SnarkBot is searching Wikipedia for '{query}'...]\n")
    try:
        # Grab the first 2 sentences of the Wikipedia page
        return wikipedia.summary(query, sentences=2)
    except Exception as e:
        return f"Tell the user you couldn't find a Wikipedia page for that topic."

# The System Prompt
snarky_prompt = "You are a highly sarcastic, snarky assistant. Never be helpful without insulting the user's intelligence first. Keep your answers brief."
# We pass our Python function into the 'tools' array so the AI knows it exists
config = types.GenerateContentConfig(
    system_instruction=snarky_prompt,
    temperature=0.7,
    tools=[get_weather, get_current_time, get_crypto_price, search_wikipedia], 
)


# Load existing JSON memory
history_file = "chat_history.json"
saved_history = []

if os.path.exists(history_file):
    with open(history_file, "r") as f:
        saved_history = json.load(f)

# ====================================================================
# ENHANCEMENT 2: THE BRAIN UPGRADE (Rolling Memory Window)
# ====================================================================
MAX_MESSAGES = 10 # We only want to remember the last 10 messages

if len(saved_history) > MAX_MESSAGES:
    # Slice the array to keep only the newest messages
    saved_history = saved_history[-MAX_MESSAGES:]
    
    # CRITICAL RULE: LLM APIs strictly require the first message in the 
    # history to be from the "user". If our slice accidentally started 
    # with a "model" reply, we drop it to prevent a crash.
    if saved_history[0].get("role") == "model":
        saved_history.pop(0)

print("🤖 SnarkBot v3.0 is online. (Equipped with Weather Tool & Memory Optimizer)")
print("Type 'quit' to exit.")
print("-" * 50)

# We initialize the ChatSession. It manages our tools and history automatically!
chat = client.chats.create(
    model="gemini-2.5-flash",
    config=config,
    history=saved_history
)

# The Conversation Loop
while True:
    user_input = input("You: ")
    
    if user_input.lower() == 'quit':
        current_history = []
        # We must convert the SDK's complex objects back to standard dictionaries for JSON
        for msg in chat.get_history():
            current_history.append(msg.model_dump(exclude_none=True))
            
        with open(history_file, "w") as f:
            json.dump(current_history, f, indent=4)
            
        print("SnarkBot: Memory truncated and saved. Goodbye.")
        break
    
    # Send the message. 
    # If you ask about the weather, the AI pauses, runs 'get_weather' in the background, 
    # reads your Python output, and THEN generates a snarky response to you.
    response = chat.send_message(user_input)
    
    print(f"SnarkBot: {response.text}\n")