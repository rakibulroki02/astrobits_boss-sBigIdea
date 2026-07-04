# import os
# import discord
# from discord.ext import commands, tasks
# import json
# import aiohttp
# import datetime
# from dotenv import load_dotenv

# # Load the environment variables from the .env file
# load_dotenv()

# # --- CONFIGURATION ---
# DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
# OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
# ALERT_CHANNEL_ID = 1522667361163804905 

# # Backend URL (Change this if your teammate hosts it online instead of running it locally)
# BACKEND_API_URL = "http://127.0.0.1:8000/api/state"

# LLM_MODEL = 'openrouter/free' 

# intents = discord.Intents.default()
# intents.message_content = True
# bot = commands.Bot(command_prefix='!', intents=intents)

# # --- DATA FETCHING ---
# async def fetch_office_data():
#     """Fetches the live state from the FastAPI backend."""
#     async with aiohttp.ClientSession() as session:
#         try:
#             async with session.get(BACKEND_API_URL) as response:
#                 if response.status == 200:
#                     return await response.json()
#                 else:
#                     print(f"⚠️ Backend returned status {response.status}")
#                     return None
#         except Exception as e:
#             print(f"❌ Failed to connect to backend: {e}")
#             return None

# # --- LLM INTEGRATION ---
# async def ask_llm(office_data: dict, user_question: str) -> str:
#     """Passes the live JSON and the user's question to OpenRouter."""
#     headers = {
#         "Authorization": f"Bearer {OPENROUTER_API_KEY}",
#         "Content-Type": "application/json"
#     }
    
#     payload = {
#         "model": LLM_MODEL,
#         "messages": [
#             {
#                 "role": "system", 
#                 "content": (
#                     "You are a helpful, casual office assistant bot living in Discord. "
#                     "Your boss is a tech enthusiast who hates robotic data dumps. "
#                     "Always reply in a friendly, conversational tone. Do not expose raw JSON. "
#                     "Keep answers concise (1-3 sentences maximum). Read the provided JSON data accurately."
#                 )
#             },
#             {
#                 "role": "user", 
#                 "content": f"Here is the live office data:\n{json.dumps(office_data)}\n\nThe boss is asking: {user_question}"
#             }
#         ]
#     }
    
#     async with aiohttp.ClientSession() as session:
#         async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload) as response:
#             if response.status == 200:
#                 data = await response.json()
#                 return data['choices'][0]['message']['content']
#             else:
#                 return f"⚠️ My brain is offline. OpenRouter returned status {response.status}."

# # --- BACKGROUND TASKS (THE BONUS FEATURE) ---
# @tasks.loop(minutes=1) 
# async def monitor_office_hours():
#     """Continuously checks the live API for devices left on after hours."""
#     current_hour = datetime.datetime.now().hour
    
#     # Change to `if True:` when recording your demo video to force the alert immediately!
#     if current_hour >= 17 or current_hour < 9:
#         office_data = await fetch_office_data()
        
#         if not office_data:
#             return # Backend might be offline, skip this check
            
#         rooms_with_devices_on = []
        
#         # Scan the live backend data
#         for room_name, devices in office_data.get("rooms", {}).items():
#             on_count = sum(1 for d in devices.values() if d.get("status") == "on")
#             if on_count > 0:
#                 rooms_with_devices_on.append(room_name)
        
#         if rooms_with_devices_on:
#             channel = bot.get_channel(ALERT_CHANNEL_ID)
#             if channel:
#                 prompt = (
#                     f"It is currently outside of office hours, but devices are still ON in: "
#                     f"{', '.join(rooms_with_devices_on)}. Generate a short, slightly panicked, "
#                     f"proactive alert message asking if someone forgot to leave."
#                 )
#                 alert_msg = await ask_llm(office_data, prompt)
#                 await channel.send(f"🚨 **AUTOMATED ALERT** 🚨\n{alert_msg}")

# @monitor_office_hours.before_loop
# async def before_monitor():
#     await bot.wait_until_ready()

# # --- BOT EVENTS & COMMANDS ---
# @bot.event
# async def on_ready():
#     print(f'⚡ {bot.user.name} is online and ready!')
#     if not monitor_office_hours.is_running():
#         monitor_office_hours.start()

# @bot.command()
# async def status(ctx):
#     """Handles the !status command."""
#     async with ctx.typing():
#         office_data = await fetch_office_data()
#         if not office_data:
#             await ctx.send("❌ I can't reach the backend server right now!")
#             return
            
#         reply = await ask_llm(office_data, "Give me a quick summary of what devices are ON in every room right now.")
#     await ctx.send(reply)

# @bot.command()
# async def usage(ctx):
#     """Handles the !usage command."""
#     async with ctx.typing():
#         office_data = await fetch_office_data()
#         if not office_data:
#             await ctx.send("❌ I can't reach the backend server right now!")
#             return
            
#         reply = await ask_llm(office_data, "How much total power are we drawing right now across the whole office?")
#     await ctx.send(reply)

# @bot.command()
# async def room(ctx, *, room_name: str):
#     """Handles the !room <name> command."""
#     async with ctx.typing():
#         office_data = await fetch_office_data()
#         if not office_data:
#             await ctx.send("❌ I can't reach the backend server right now!")
#             return
            
#         reply = await ask_llm(office_data, f"What is the exact status of the lights and fans in {room_name}? Include the wattage.")
#     await ctx.send(reply)

# # Boot up the bot
# if __name__ == "__main__":
#     if DISCORD_TOKEN is None or OPENROUTER_API_KEY is None:
#         print("❌ Error: Missing API keys. Make sure your .env file is set up correctly.")
#     else:
#         bot.run(DISCORD_TOKEN)

import os
import re
import discord
from discord.ext import commands, tasks
import json
import aiohttp
import datetime
from dotenv import load_dotenv

# Load the environment variables from the .env file
load_dotenv()

# --- CONFIGURATION ---
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
ALERT_CHANNEL_ID = 1522941877396045954

# Backend URL -- correct as-is if the bot and the FastAPI server run on the
# same laptop. If you ever run the bot on a *different* machine than the
# server, change this to that machine's LAN IP, e.g. "http://192.168.1.42:8000/api/state".
BACKEND_API_URL = "http://127.0.0.1:8000/api/state"

# OpenRouter's official Free Models Router -- confirmed valid, no change needed.
LLM_MODEL = 'openrouter/free'

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# One shared session for the bot's whole runtime instead of opening a fresh
# TCP/TLS connection on every single command invocation and every 1-minute
# monitor tick.
session: aiohttp.ClientSession | None = None


# --- ROOM NAME MATCHING ---
def normalize_room_name(user_input: str, valid_rooms: list[str]) -> str | None:
    """
    Matches loose user input ('work1', 'Work Room 1', 'drawing') to an actual
    room key reported by the backend, instead of handing an unvalidated
    string straight to the LLM and hoping it guesses the right room.
    """
    cleaned_input = re.sub(r'[^a-z0-9]', '', user_input.lower())

    for room in valid_rooms:
        cleaned_room = re.sub(r'[^a-z0-9]', '', room.lower())

        if cleaned_input == cleaned_room:
            return room

        # Split into letters vs trailing digits so "work1" matches
        # "workroom1" even though "work" and "1" aren't adjacent in the
        # room's own name.
        input_letters = re.sub(r'[0-9]', '', cleaned_input)
        input_digits = re.sub(r'[^0-9]', '', cleaned_input)
        room_letters = re.sub(r'[0-9]', '', cleaned_room)
        room_digits = re.sub(r'[^0-9]', '', cleaned_room)

        letters_match = bool(input_letters) and room_letters.startswith(input_letters)
        digits_match = (input_digits == room_digits) if input_digits else True

        if letters_match and digits_match:
            return room

    return None


# --- DATA FETCHING ---
async def fetch_office_data():
    """Fetches the live state from the FastAPI backend."""
    try:
        async with session.get(BACKEND_API_URL, timeout=REQUEST_TIMEOUT) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"⚠️ Backend returned status {response.status}")
                return None
    except Exception as e:
        print(f"❌ Failed to connect to backend: {e}")
        return None


# --- LLM INTEGRATION ---
async def ask_llm(office_data: dict, user_question: str) -> str:
    """Passes the live JSON and the user's question to OpenRouter."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful, casual office assistant bot living in Discord. "
                    "Your boss is a tech enthusiast who hates robotic data dumps. "
                    "Always reply in a friendly, conversational tone. Do not expose raw JSON. "
                    "Keep answers concise (1-3 sentences maximum). Read the provided JSON data accurately."
                )
            },
            {
                "role": "user",
                "content": f"Here is the live office data:\n{json.dumps(office_data)}\n\nThe boss is asking: {user_question}"
            }
        ]
    }

    try:
        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, timeout=REQUEST_TIMEOUT
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data['choices'][0]['message']['content']
            else:
                body = await response.text()
                print(f"⚠️ OpenRouter error {response.status}: {body}")
                return f"⚠️ My brain is offline. OpenRouter returned status {response.status}."
    except Exception as e:
        print(f"❌ Failed to reach OpenRouter: {e}")
        return "⚠️ I couldn't reach my brain (OpenRouter) just now -- try again in a moment."


async def answer_with_llm(ctx, question: str):
    """Shared fetch -> ask -> reply flow used by !status and !usage."""
    async with ctx.typing():
        office_data = await fetch_office_data()
        if not office_data:
            await ctx.send("❌ I can't reach the backend server right now!")
            return
        reply = await ask_llm(office_data, question)
    await ctx.send(reply)


# --- BACKGROUND TASKS (THE BONUS FEATURE) ---
@tasks.loop(minutes=1)
async def monitor_office_hours():
    """Continuously checks the live API for devices left on after hours."""
    current_hour = datetime.datetime.now().hour

    # Change to `if True:` when recording your demo video to force the alert immediately!
    if current_hour >= 17 or current_hour < 9:
        office_data = await fetch_office_data()

        if not office_data:
            return  # Backend might be offline, skip this check

        rooms_with_devices_on = []

        for room_name, devices in office_data.get("rooms", {}).items():
            on_count = sum(1 for d in devices.values() if d.get("status") == "on")
            if on_count > 0:
                rooms_with_devices_on.append(room_name)

        if rooms_with_devices_on:
            channel = bot.get_channel(ALERT_CHANNEL_ID)
            if channel:
                prompt = (
                    f"It is currently outside of office hours, but devices are still ON in: "
                    f"{', '.join(rooms_with_devices_on)}. Generate a short, slightly panicked, "
                    f"proactive alert message asking if someone forgot to leave."
                )
                alert_msg = await ask_llm(office_data, prompt)
                await channel.send(f"🚨 **AUTOMATED ALERT** 🚨\n{alert_msg}")


@monitor_office_hours.before_loop
async def before_monitor():
    await bot.wait_until_ready()


# --- BOT EVENTS & COMMANDS ---
@bot.event
async def on_ready():
    global session
    print(f'⚡ {bot.user.name} is online and ready!')

    # on_ready can fire more than once (e.g. after a gateway reconnect),
    # so guard against creating a duplicate session.
    if session is None or session.closed:
        session = aiohttp.ClientSession()

    if not monitor_office_hours.is_running():
        monitor_office_hours.start()


@bot.command()
async def status(ctx):
    """Handles the !status command."""
    await answer_with_llm(ctx, "Give me a quick summary of what devices are ON in every room right now.")


@bot.command()
async def usage(ctx):
    """Handles the !usage command."""
    await answer_with_llm(ctx, "How much total power are we drawing right now across the whole office?")


@bot.command()
async def room(ctx, *, room_name: str):
    """Handles the !room <name> command."""
    office_data = await fetch_office_data()
    if not office_data:
        await ctx.send("❌ I can't reach the backend server right now!")
        return

    valid_rooms = list(office_data.get("rooms", {}).keys())
    matched_room = normalize_room_name(room_name, valid_rooms)

    if not matched_room:
        await ctx.send(f"🤔 I don't recognize '{room_name}'. Try one of: {', '.join(valid_rooms)}")
        return

    async with ctx.typing():
        reply = await ask_llm(
            office_data,
            f"What is the exact status of the lights and fans in {matched_room}? Include the wattage."
        )
    await ctx.send(reply)


# Boot up the bot
if __name__ == "__main__":
    if DISCORD_TOKEN is None or OPENROUTER_API_KEY is None:
        print("❌ Error: Missing API keys. Make sure your .env file is set up correctly.")
    else:
        bot.run(DISCORD_TOKEN)