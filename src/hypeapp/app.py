import toga
from toga.style import Pack
from toga.style.pack import COLUMN
import threading
import json
import ssl
import websocket
import time
import traceback

class HypeApp(toga.App):
    def startup(self):
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
        self.ws = None
        self.token = ""

    # SAFE UI UPDATER (Prevents crashes on Android)
    def update_ui(self, text):
        self.loop.call_soon_threadsafe(lambda: setattr(self.status_label, 'text', text))

    def start_status(self, widget):
        self.token = self.token_input.value.strip()
        if not self.token:
            self.update_ui("Error: Token required")
            return
            
        self.is_running = True
        self.update_ui("Connecting...")
        
        threading.Thread(target=self.run_ws, daemon=True).start()

    def stop_status(self, widget):
        self.is_running = False
        if self.ws:
            self.ws.close()
        self.update_ui("Status: Offline")

    def run_ws(self):
        try:
            url = "wss://gateway.discord.gg/?v=10&encoding=json"
            self.ws = websocket.WebSocketApp(
                url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        except Exception as e:
            self.update_ui(f"WS Error: {e}")

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if data.get("op") == 10:
                interval = data["d"]["heartbeat_interval"] / 1000
                identify = {
                    "op": 2,
                    "d": {
                        "token": self.token,
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
                ws.send(json.dumps(identify))
                self.update_ui("Status: ACTIVE (VR)")

                def hb():
                    while self.is_running:
                        time.sleep(interval)
                        try: ws.send(json.dumps({"op": 1, "d": None}))
                        except: break
                threading.Thread(target=hb, daemon=True).start()
        except Exception as e:
            self.update_ui(f"Msg Error: {e}")

    def on_error(self, ws, error):
        self.update_ui(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        if self.is_running:
            self.update_ui("Disconnected")

def main():
    return HypeApp("Hype App", "com.hype.app")
