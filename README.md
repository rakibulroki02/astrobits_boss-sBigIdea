<div align="center">
  <h1>🚀 Astrobits: Boss's Big Idea (Office Live Monitor)</h1>

  <p>
    <a href="https://github.com/rakibulroki02/astrobits_boss-sBigIdea/issues">
      <img src="https://img.shields.io/github/issues/rakibulroki02/astrobits_boss-sBigIdea" alt="Issues">
    </a>
    <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
    <img src="https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi" alt="FastAPI">
    <img src="https://img.shields.io/badge/Three.js-black?style=flat&logo=three.js&logoColor=white" alt="Three.js">
  </p>

  <p>
    <strong>A real-time IoT monitoring system featuring a 3D WebGL dashboard, a conversational Discord bot, and ESP32 hardware simulation to track office power consumption.</strong><br>
    <em>Built for the Techathon Nationals Rover Summit</em>
  </p>
</div>

<hr>

<h2>📋 Table of Contents</h2>
<ul>
  <li><a href="#about">About the Project</a></li>
  <li><a href="#architecture">System Architecture</a></li>
  <li><a href="#features">Features</a></li>
  <li><a href="#tech-stack">Tech Stack</a></li>
  <li><a href="#installation">Installation & Setup</a></li>
  <li><a href="#usage">Usage & Commands</a></li>
</ul>

<h2 id="about">🌌 About the Project</h2>
<p>
  Our boss had a big idea: <em>"What if I could see every light and fan in the office on a live dashboard? And check how much power we're burning? And ask a bot about it right from Discord?"</em>
</p>
<p>
  <b>Astrobits</b> is the realization of that idea. It is a unified IoT ecosystem that monitors 15 devices across 3 office rooms. It features a simulated ESP32 hardware node that posts telemetry data to a centralized Python backend. This "Single Source of Truth" instantly broadcasts live updates to a dual 2D/3D web dashboard via WebSockets and serves data to an AI-powered Discord Watchdog bot via REST API.
</p>

<h2 id="architecture">📐 System Architecture</h2>
<pre><code>
[ Hardware Node (Wokwi) ] --(HTTP POST JSON)--> [ Ngrok Tunnel ]
                                                       |
                                                       v
[ Discord LLM Bot ] <------(REST API GET)------ [ FastAPI Backend ]
        |                                              |
        v                                              v
[ Discord Server ]                       (WebSockets) / (Live Broadcast)
                                                       |
                                                       v
                                            [ Web Dashboard (HTML/JS) ]
                                            ├─ 2D Live Blueprint View
                                            └─ 3D First-Person POV (Three.js)
</code></pre>

<h2 id="features">✨ Features</h2>
<ul>
  <li><strong>Hardware Simulation (Wokwi):</strong> ESP32 C++ simulation handling 3 rooms, using non-blocking timers and randomized realistic wattage calculation (e.g., fans drawing ~60W).</li>
  <li><strong>Unified FastAPI Backend:</strong> A single source of truth that catches hardware webhooks and instantly pushes data to the UI using asynchronous WebSockets.</li>
  <li><strong>Interactive WebGL Dashboard:</strong> A real-time web interface featuring a 2D floor plan that dynamically updates device states, alongside a fully playable 3D First-Person POV powered by Three.js.</li>
  <li><strong>Conversational Discord Bot:</strong> An AI-powered Discord bot (using OpenRouter LLM) that reads the live telemetry and answers questions in a friendly, humanized tone.</li>
  <li><strong>Proactive Watchdog Alerts:</strong> The system detects if devices are left running outside of office hours (9 AM - 5 PM) and automatically pushes panic alerts to both the web UI and Discord.</li>
</ul>

<h2 id="tech-stack">🛠️ Tech Stack</h2>
<ul>
  <li><b>Frontend:</b> HTML5, Tailwind CSS, Vanilla JS, Three.js (WebGL), WebSockets</li>
  <li><b>Backend:</b> Python, FastAPI, Uvicorn</li>
  <li><b>Discord Bot:</b> Python, <code>discord.py</code>, <code>aiohttp</code>, OpenRouter API</li>
  <li><b>Hardware/IoT:</b> C++, ESP32 (Wokwi Simulator), ArduinoJson</li>
</ul>

<h2 id="installation">💻 Installation & Setup</h2>
<p>To run this project locally and recreate the full pipeline, follow these 5 steps in order. You will need 4 terminal windows open.</p>

<h3>1. Prerequisites & Dependencies</h3>
<p>Ensure you have Python 3 installed. Install the required Python packages:</p>
<pre><code>pip install fastapi uvicorn websockets discord.py aiohttp python-dotenv</code></pre>

<h3>2. Environment Variables</h3>
<p>Create a file named <code>.env</code> in the root directory and add your API keys (refer to <code>.env.example</code> if provided):</p>
<pre><code>DISCORD_TOKEN=your_discord_bot_token_here
OPENROUTER_API_KEY=your_openrouter_api_key_here</code></pre>

<h3>3. Start the Backend & Tunnel</h3>
<p><b>Terminal 1:</b> Start the FastAPI server.</p>
<pre><code>uvicorn main:app --reload</code></pre>

<p><b>Terminal 2:</b> Because Wokwi runs in the cloud, you must expose your local port 8000 using <a href="https://ngrok.com/">ngrok</a>.</p>
<pre><code>ngrok http 8000</code></pre>
<p><i>⚠️ Important: Copy the <code>http://...</code> forwarding URL provided by ngrok. Open the <code>sketch.ino</code> file in Wokwi and update the <code>webhookUrl</code> variable with this exact link.</i></p>

<h3>4. Start the Frontend & Bot</h3>
<p><b>Terminal 3:</b> Start a local HTTP server to host the web dashboard (this prevents CORS issues with the 3D textures).</p>
<pre><code>python -m http.server 3000</code></pre>

<p><b>Terminal 4:</b> Boot up the Discord Watchdog bot.</p>
<pre><code>python bot.py</code></pre>

<h3>5. Launch the Hardware</h3>
<p>Go to your Wokwi project and click the <b>Play</b> button on the ESP32 simulator. It will connect to virtual WiFi and begin sending POST requests to your backend.</p>

<h2 id="usage">🚀 Usage & Commands</h2>

<h3>Web Dashboard</h3>
<ul>
  <li>Navigate to <code>http://localhost:3000</code> in your browser.</li>
  <li>Watch the 2D layout update dynamically as Wokwi toggles virtual relays.</li>
  <li>Click <b>"🤖 Launch 3D Bot POV"</b> to enter the Three.js environment. Use <code>W A S D</code> to walk through the office and view the physical lights and fans reacting to the live data.</li>
</ul>

<h3>Discord Bot</h3>
<p>In your Discord server, type the following commands:</p>
<ul>
  <li><code>!status</code> - The bot will provide a natural language summary of which devices are currently running.</li>
  <li><code>!usage</code> - The bot will fetch the total live wattage consumption.</li>
  <li><code>!room &lt;name&gt;</code> - (e.g., <code>!room work1</code>) The bot will give a detailed breakdown of a specific room.</li>
</ul>
<p><i>Note: If the simulated time falls outside of office hours (9 AM - 5 PM), the bot will autonomously post a warning message to the designated channel.</i></p>
