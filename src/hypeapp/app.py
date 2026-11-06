import toga
from toga.style import Pack
from toga.style.pack import COLUMN
import asyncio
import json
import ssl
import websockets

class HypeApp(toga.App):
    def startup(self):
        # UI Layout
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20))
        
        title_label = toga.Label(
            "Hype App: VR Status", 
            style=Pack(font_size=24, padding_bottom=20, text_align="center")
        )
        
        self.token_input = toga.PasswordInput(
            placeholder="Paste Discord Token here", 
            style=Pack(padding_bottom=15)
        )
        
        self.start_btn = toga.Button(
            "Start VR Status", 
            on_press=self.start_status, 
            style=Pack(padding_bottom=10)
        )
        
        self.stop_btn = toga.Button(
            "Stop Status", 
            on_press=self.stop_status, 
            style=Pack(padding_bottom=15)
        )
        
        self.status_label = toga.Label(
            "Status: Offline", 
            style=Pack(font_size=16, text_align="center")
        )

        main_box.add(title_label)
        main_box.add(self.token_input)
        main_box.add(self.start_btn)
        main_box.add(self.stop_btn)
        main_box.add(self.status_label)

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

        self.is_running = False
        self.ws_task = None

    def update_ui(self, text):
        # Safely update UI from async task
        self.loop.call_soon_threadsafe(lambda: setattr(self.status_label, 'text', text))

    def start_status(self, widget):
        token = self.token_input.value.strip()
        if not token:
            self.update_ui("Error: Token required")
            return
            
        self.is_running = True
        self.update_ui("Connecting...")
        
        # Start the async websocket task
        self.ws_task = self.loop.create_task(self.run_ws(token))

    def stop_status(self, widget):
        self.is_running = False
        if self.ws_task:
            self.ws_task.cancel()
        self.update_ui("Status: Offline")

    async def run_ws(self, token):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        url = "wss://gateway.discord.gg/?v=10&encoding=json"
        
        try:
            async with websockets.connect(url, ssl=ssl_context) as ws:
                # Wait for Hello (op 10)
                hello = json.loads(await ws.recv())
                interval = hello["d"]["heartbeat_interval"] / 1000
                
                # Send Identify (op 2)
                identify = {
                    "op": 2,
                    "d": {
                        "token": token,
                        "properties": {
                            "$os": "android", 
                            "$browser": "Discord VR", 
                            "$device": "Meta Quest 3"
                        },
                        "presence": {
                            "status": "online", 
                            "afk": False, 
                            "activities": []
                        }
                    }
                }
                await ws.send(json.dumps(identify))
                self.update_ui("Status: ACTIVE (VR)")

                # Heartbeat Loop
                while self.is_running:
                    await asyncio.sleep(interval)
                    try:
                        await ws.send(json.dumps({"op": 1, "d": None}))
                    except:
                        break
                        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.update_ui(f"Error: {str(e)[:20]}")
            self.is_running = False

def main():
    return HypeApp("Hype App", "com.hype.app")
