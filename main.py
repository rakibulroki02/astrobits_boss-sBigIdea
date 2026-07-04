from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import random
import time
import datetime

app = FastAPI()

# --- CONNECTION MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- IN-MEMORY STATE ---
office_state = {}
rooms = ["Drawing Room", "Work Room 1", "Work Room 2"]

for room in rooms:
    office_state[room] = {
        "fan_1": {"status": "off", "wattage": 60, "last_updated": "Startup"},
        "fan_2": {"status": "off", "wattage": 60, "last_updated": "Startup"},
        "light_1": {"status": "off", "wattage": 15, "last_updated": "Startup"},
        "light_2": {"status": "off", "wattage": 15, "last_updated": "Startup"},
        "light_3": {"status": "off", "wattage": 15, "last_updated": "Startup"},
    }

# Tracks the exact time a room had ALL its devices turned on
room_all_on_tracker = {"Drawing Room": None, "Work Room 1": None, "Work Room 2": None}

# --- BACKGROUND SIMULATOR (Final Version with All Alerts) ---
async def simulate_device_activity():
    print("🚀 Background simulator is STARTING UP...", flush=True)
    simulated_time = datetime.datetime.strptime("08:00 AM", "%I:%M %p")
    
    while True:
        try:
            await asyncio.sleep(5) 
            
            # Advance time by 15 minutes every 2 seconds
            simulated_time += datetime.timedelta(minutes=5)
            current_time_str = simulated_time.strftime("%I:%M %p")
            
            # 1. Randomly toggle a device
            random_room = random.choice(rooms)
            random_device = random.choice(list(office_state[random_room].keys()))
            
            current_status = office_state[random_room][random_device]["status"]
            
            # If it's night time (after 6 PM), bias heavily towards turning things OFF
            if simulated_time.hour >= 18 or simulated_time.hour < 8:
                new_status = "off" if random.random() < 0.8 else "on"
            else:
                new_status = "on" if current_status == "off" else "off"
            
            base_w = 60 if "fan" in random_device else 15
            
            if new_status == "on":
                live_wattage = round(base_w + random.uniform(-1.5, 1.5), 1)
            else:
                live_wattage = 0

            # Update the state dictionary
            office_state[random_room][random_device]["status"] = new_status
            office_state[random_room][random_device]["wattage"] = live_wattage
            office_state[random_room][random_device]["last_updated"] = current_time_str
            
            # Print update to terminal
            print(f"[{current_time_str}] DYNAMIC UPDATE: {random_room} {random_device} is now {new_status} ({live_wattage}W)", flush=True)
            
            # 2. Check for Alerts (Out of Office Hours & 2-Hour Rule)
            active_alerts = []
            is_after_hours = simulated_time.hour < 9 or simulated_time.hour >= 17
            total_power = 0
            room_power = {"Drawing Room": 0, "Work Room 1": 0, "Work Room 2": 0}
            
            for room, devices in office_state.items():
                room_total = 0
                all_devices_on = True # Assume true until we find an "off" device
                
                for device_name, device_info in devices.items():
                    room_total += device_info["wattage"]
                    
                    if device_info["status"] == "on":
                        # Alert 1: After Hours Check
                        if is_after_hours:
                            alert_msg = f"[{current_time_str}] ALERT: {device_name.replace('_', ' ').title()} left ON in {room} after hours!"
                            active_alerts.append(alert_msg)
                            print(f"🚨 {alert_msg}", flush=True)
                    else:
                        all_devices_on = False
                
                # Alert 2: The 2-Hour Continuous Check
                if all_devices_on:
                    # If this is the first time we noticed they are all on, start the timer
                    if room_all_on_tracker[room] is None:
                        room_all_on_tracker[room] = simulated_time
                    else:
                        # Check if it has been strictly more than 2 hours
                        time_difference = simulated_time - room_all_on_tracker[room]
                        if time_difference.total_seconds() > 7200: # 7200 seconds = 2 hours
                            alert_msg = f"[{current_time_str}] ⚠️ WARNING: ALL devices in {room} have been ON for over 2 hours!"
                            active_alerts.append(alert_msg)
                            print(f"🚨 {alert_msg}", flush=True)
                else:
                    # If even one device is off, reset the timer
                    room_all_on_tracker[room] = None
                
                room_power[room] = round(room_total, 1)
                total_power += room_total
            
            # 3. Build the Payload for the Web Dashboard
            live_payload = {
                "simulated_time": current_time_str,
                "total_power_w": round(total_power, 1),
                "room_power_w": room_power,
                "alerts": active_alerts,
                "rooms": office_state
            }
            
            # Broadcast to UI
            await manager.broadcast(live_payload)

        # If anything breaks, print the exact error!
        except Exception as e:
            print(f"❌ ERROR IN SIMULATOR: {e}", flush=True)
            await asyncio.sleep(2) 

@app.on_event("startup")
async def startup_event():
    print("⚡ FastAPI is starting up. Launching simulator...", flush=True)
    asyncio.create_task(simulate_device_activity())

# --- REST API ENDPOINT (For the Discord Bot) ---
@app.get("/api/state")
async def get_state():
    total_power = 0
    room_power = {"Drawing Room": 0, "Work Room 1": 0, "Work Room 2": 0}
    
    # Calculate live power consumption before sending the JSON
    for room, devices in office_state.items():
        room_total = 0
        for device_name, device_info in devices.items():
            room_total += device_info["wattage"]
        
        room_power[room] = round(room_total, 1)
        total_power += room_total
                
    return {
        "total_power_w": round(total_power, 1),
        "room_power_w": room_power,
        "rooms": office_state
    }

# --- WEBSOCKET ENDPOINT (For the Web Dashboard) ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(websocket)