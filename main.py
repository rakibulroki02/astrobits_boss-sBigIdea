from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import ClientDisconnect
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
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # FIX: a single stale/half-closed browser tab (e.g. from a page
        # refresh) could previously stall this loop indefinitely, which in
        # turn could delay the server from reading the next incoming POST
        # from the ESP32 -- looking exactly like a dropped connection there.
        # Now we isolate failures per-connection and prune dead ones.
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(connection)

manager = ConnectionManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- IN-MEMORY STATE ---
# This holds the latest state reported by Wokwi
office_state = {
    "Drawing Room": {
        "fan_1": {"status": "off", "wattage": 0, "last_updated": "Startup"},
        "fan_2": {"status": "off", "wattage": 0, "last_updated": "Startup"},
        "light_1": {"status": "off", "wattage": 0, "last_updated": "Startup"},
        "light_2": {"status": "off", "wattage": 0, "last_updated": "Startup"},
        "light_3": {"status": "off", "wattage": 0, "last_updated": "Startup"},
    },
    "Work Room 1": {
        "fan_1": {"status": "off", "wattage": 0, "last_updated": "Startup"},
        "fan_2": {"status": "off", "wattage": 0, "last_updated": "Startup"},
        "light_1": {"status": "off", "wattage": 0, "last_updated": "Startup"},
        "light_2": {"status": "off", "wattage": 0, "last_updated": "Startup"},
        "light_3": {"status": "off", "wattage": 0, "last_updated": "Startup"},
    },
    "Work Room 2": {
        "fan_1": {"status": "off", "wattage": 0, "last_updated": "Startup"},
        "fan_2": {"status": "off", "wattage": 0, "last_updated": "Startup"},
        "light_1": {"status": "off", "wattage": 0, "last_updated": "Startup"},
        "light_2": {"status": "off", "wattage": 0, "last_updated": "Startup"},
        "light_3": {"status": "off", "wattage": 0, "last_updated": "Startup"},
    }
}

# --- WOKWI POST ENDPOINT (The Receiver) ---
@app.post("/api/update")
async def receive_wokwi_update(request: Request):
    global office_state

    # FIX: if the ESP32 / tunnel drops mid-request (flaky network across the
    # Wokwi Gateway -> ngrok chain), this used to raise an unhandled
    # ClientDisconnect and print a scary traceback. Now we just log it and
    # skip this one update -- the next telemetry send will catch things up.
    try:
        payload = await request.json()
    except ClientDisconnect:
        print("⚠️  Client disconnected before sending full body -- skipping this update.")
        return {"status": "error", "message": "client disconnected"}
    except Exception as e:
        print(f"⚠️  Failed to parse incoming payload: {e}")
        return {"status": "error", "message": "invalid payload"}

    # Update the internal state with Wokwi's data
    if "rooms" in payload:
        office_state = payload["rooms"]
    else:
        # If Wokwi just sends the rooms object directly
        office_state = payload

    # 1. Calculate live totals and alerts based on the real-world time
    current_time_str = datetime.datetime.now().strftime("%I:%M %p")
    current_hour = datetime.datetime.now().hour

    # You can change these hours to trigger alerts during the video demo
    is_after_hours = current_hour < 9 or current_hour >= 17

    total_power = 0
    room_power = {"Drawing Room": 0, "Work Room 1": 0, "Work Room 2": 0}
    active_alerts = []

    for room, devices in office_state.items():
        room_total = 0
        for device_name, device_info in devices.items():
            room_total += float(device_info.get("wattage", 0))

            # Check for Alerts
            if device_info.get("status") == "on" and is_after_hours:
                clean_name = device_name.replace('_', ' ').title()
                alert_msg = f"[{current_time_str}] ALERT: {clean_name} left ON in {room} outside office hours!"
                active_alerts.append(alert_msg)

        room_power[room] = round(room_total, 1)
        total_power += room_total

    # 2. Build the exact payload the HTML Dashboard expects
    live_payload = {
        "simulated_time": current_time_str,
        "total_power_w": round(total_power, 1),
        "room_power_w": room_power,
        "alerts": active_alerts,
        "rooms": office_state
    }

    # 3. Fire it to the Web Dashboard instantly via WebSockets
    await manager.broadcast(live_payload)

    return {"status": "success", "message": "Data received and broadcasted to Dashboard!"}

# --- REST API ENDPOINT (For the Discord Bot) ---
@app.get("/api/state")
async def get_state():
    # The Discord Bot will hit this endpoint to get the latest state Wokwi sent us
    total_power = 0
    room_power = {"Drawing Room": 0, "Work Room 1": 0, "Work Room 2": 0}

    for room, devices in office_state.items():
        room_total = 0
        for device_name, device_info in devices.items():
            room_total += float(device_info.get("wattage", 0))

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