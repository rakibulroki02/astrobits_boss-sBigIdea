#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>

#define RELAY_ACTIVE_STATE   HIGH
#define RELAY_INACTIVE_STATE (RELAY_ACTIVE_STATE == HIGH ? LOW : HIGH)

// --- Network & Server Configuration ---
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// Ensure your ngrok URL has /api/update at the end!
// NOTE: If you restarted ngrok, this URL will change and you must update it here.
//
// IMPORTANT: this must be the *http://* forwarding URL, not https://.
// Start ngrok with both schemes enabled so it gives you a plain-HTTP URL too:
//   ngrok http 8000 --scheme http --scheme https
// Then copy the "http://..." line it prints (NOT the https:// one) into webhookUrl below.
// This avoids a TLS handshake incompatibility between the ESP32's TLS stack
// and ngrok's edge servers that causes "Error code: -1, connection refused"
// even with WiFiClientSecure + setInsecure().
const char* webhookUrl = "http://fried-resolved-vertebrae.ngrok-free.dev/api/update";

// --- Office Layout Configuration ---
#define NUM_ROOMS   3
#define NUM_DEVICES 5

const char* roomNames[NUM_ROOMS]   = {"Drawing Room", "Work Room 1", "Work Room 2"};
const char* deviceKeys[NUM_DEVICES] = {"fan_1", "fan_2", "light_1", "light_2", "light_3"};

// Only Room 0 (Drawing Room) has real relays wired in the Wokwi schematic.
const bool roomIsPhysical[NUM_ROOMS] = {true, false, false};
const int relayPins[NUM_DEVICES]     = {13, 12, 14, 27, 26};  // only used for room 0

// --- State Tracking (2D: [room][device]) ---
bool deviceState[NUM_ROOMS][NUM_DEVICES];
float deviceWattage[NUM_ROOMS][NUM_DEVICES];
char lastChangedStr[NUM_ROOMS][NUM_DEVICES][20];
unsigned long nextToggleTime[NUM_ROOMS][NUM_DEVICES];

unsigned long lastTelemetrySend = 0;
const unsigned long HEARTBEAT_INTERVAL = 15000;  // keep-alive if nothing toggles for a while

const long gmtOffset_sec = 6 * 3600;  // Dhaka timezone (UTC+6)
const int daylightOffset_sec = 0;

const unsigned long WIFI_CONNECT_TIMEOUT = 15000;
const unsigned long NTP_SYNC_TIMEOUT = 10000;

void recordLastChanged(int r, int d) {
  struct tm ti;
  if (getLocalTime(&ti)) {
    strftime(lastChangedStr[r][d], sizeof(lastChangedStr[r][d]), "%I:%M %p", &ti);
  } else {
    strncpy(lastChangedStr[r][d], "Time Error", sizeof(lastChangedStr[r][d]));
  }
}

// Builds the JSON snapshot of all 3 rooms x 5 devices and POSTs it.
void sendTelemetry() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Skipping send: WiFi not connected");
    return;
  }

  // Refresh wattage for every device based on current state
  for (int r = 0; r < NUM_ROOMS; r++) {
    for (int d = 0; d < NUM_DEVICES; d++) {
      if (deviceState[r][d]) {
        if (String(deviceKeys[d]).startsWith("fan")) {
          deviceWattage[r][d] = 60.0 + (random(0, 50) / 10.0);   // 60.0 to 65.0W
        } else {
          deviceWattage[r][d] = 14.0 + (random(0, 20) / 10.0);   // 14.0 to 16.0W
        }
      } else {
        deviceWattage[r][d] = 0.0;
      }
    }
  }

  // ArduinoJson v7 syntax
  JsonDocument doc;
  for (int r = 0; r < NUM_ROOMS; r++) {
    JsonObject roomObj = doc[roomNames[r]].to<JsonObject>();
    for (int d = 0; d < NUM_DEVICES; d++) {
      JsonObject devObj = roomObj[deviceKeys[d]].to<JsonObject>();
      devObj["status"] = deviceState[r][d] ? "on" : "off";
      devObj["wattage"] = deviceWattage[r][d];
      devObj["last_updated"] = lastChangedStr[r][d];
    }
  }

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  HTTPClient http;

  // Plain HTTP now (see webhookUrl comment above) -- no secure client needed,
  // which sidesteps the ESP32/ngrok TLS handshake incompatibility entirely.
  http.begin(webhookUrl);

  // Headers
  http.addHeader("Content-Type", "application/json");
  // Bypass the Ngrok free-tier browser warning interstitial
  http.addHeader("ngrok-skip-browser-warning", "true");

  http.setTimeout(10000);          // was 5000 -- more headroom for the multi-hop route
  http.setConnectTimeout(8000);    // explicit connect-phase timeout too

  int httpResponseCode = http.POST(jsonPayload);
  if (httpResponseCode > 0) {
    Serial.printf("HTTP Response code: %d\n", httpResponseCode);
  } else {
    Serial.printf("Error code: %d, Error: %s\n", httpResponseCode, http.errorToString(httpResponseCode).c_str());
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("=== 3-Room Office Telemetry Node ===");

  randomSeed(esp_random());

  for (int r = 0; r < NUM_ROOMS; r++) {
    for (int d = 0; d < NUM_DEVICES; d++) {
      deviceState[r][d] = false;
      nextToggleTime[r][d] = millis() + random(1000, 4000);

      if (roomIsPhysical[r]) {
        pinMode(relayPins[d], OUTPUT);
        digitalWrite(relayPins[d], RELAY_INACTIVE_STATE);
      }
    }
  }

  // Connecting directly to channel 6 speeds up Wokwi boot time
  WiFi.begin(ssid, password, 6);
  Serial.print("Connecting to WiFi");
  unsigned long wifiStart = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - wifiStart < WIFI_CONNECT_TIMEOUT) {
    delay(500);
    Serial.print(".");
  }
  bool wifiOK = (WiFi.status() == WL_CONNECTED);
  Serial.println(wifiOK ? "\nConnected!" : "\nWiFi timed out -- continuing, will keep retrying in the background");

  if (wifiOK) {
    Serial.print("Syncing real-time clock");
    configTime(gmtOffset_sec, daylightOffset_sec, "pool.ntp.org");
    struct tm ti;
    unsigned long ntpStart = millis();
    while (!getLocalTime(&ti) && millis() - ntpStart < NTP_SYNC_TIMEOUT) {
      delay(250);
      Serial.print(".");
    }
    Serial.println(getLocalTime(&ti) ? " Done." : " Timed out (will show 'Time Error' until it syncs).");
  }

  for (int r = 0; r < NUM_ROOMS; r++) {
    for (int d = 0; d < NUM_DEVICES; d++) {
      recordLastChanged(r, d);
    }
  }
  Serial.println();
}

void loop() {
  unsigned long currentMillis = millis();
  bool anyStateChanged = false;

  for (int r = 0; r < NUM_ROOMS; r++) {
    for (int d = 0; d < NUM_DEVICES; d++) {
      if (currentMillis >= nextToggleTime[r][d]) {
        deviceState[r][d] = !deviceState[r][d];

        if (roomIsPhysical[r]) {
          digitalWrite(relayPins[d], deviceState[r][d] ? RELAY_ACTIVE_STATE : RELAY_INACTIVE_STATE);
        }

        recordLastChanged(r, d);
        anyStateChanged = true;

        Serial.print("Toggled "); Serial.print(roomNames[r]);
        Serial.print(" / "); Serial.print(deviceKeys[d]);
        Serial.println(deviceState[r][d] ? " ON" : " OFF");

        // Set the next random toggle time between 10 to 20 seconds for the demo
        nextToggleTime[r][d] = currentMillis + random(10000, 20000);
      }
    }
  }

  if (anyStateChanged) {
    sendTelemetry();
    lastTelemetrySend = currentMillis;
  }

  if (currentMillis - lastTelemetrySend >= HEARTBEAT_INTERVAL) {
    lastTelemetrySend = currentMillis;
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi disconnected -- attempting reconnect...");
      WiFi.reconnect();
    } else {
      sendTelemetry();
    }
  }
}
