from machine import Pin, lightsleep
import picoweb
import utime
import camera
import gc

SSID = "Orange_Swiatlowod_FE30"         # Nazwa sieci WiFi
PASSWORD = "pFDdeauyRwHt56USRo"         # Hasło sieci WiFi

# Konfiguracja pinu PIR i LED
pir_sensor = Pin(13, Pin.IN)            # Czujnik PIR na pinie 13
led = Pin(2, Pin.OUT)                   # LED na pinie 2

# Funkcja łącząca z WiFi
def wifi_connect():
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to network...')
        wlan.connect(SSID, PASSWORD) 
    start = utime.time()
    while not wlan.isconnected():
        utime.sleep(1)
        if utime.time() - start > 5:
            print("Connect timeout!")
            break
    if wlan.isconnected():
        print('Network config:', wlan.ifconfig())

# Funkcja inicjalizująca kamerę
def camera_init():
    camera.deinit()
    camera.init(0, d0=4, d1=5, d2=18, d3=19, d4=36, d5=39, d6=34, d7=35,
                format=camera.JPEG, framesize=camera.FRAME_VGA, 
                xclk_freq=camera.XCLK_20MHz,
                href=23, vsync=25, reset=-1, pwdn=-1,
                sioc=27, siod=26, xclk=21, pclk=22, fb_location=camera.PSRAM)

    camera.framesize(camera.FRAME_VGA)
    camera.flip(1)
    camera.mirror(1)
    camera.saturation(0)
    camera.brightness(0)
    camera.contrast(0)
    camera.quality(10)
    camera.speffect(camera.EFFECT_NONE)
    camera.whitebalance(camera.WB_NONE)

# Treść odpowiedzi HTTP
index_web = """
HTTP/1.0 200 OK\r\n
<html>
  <head>
    <title>Video Streaming</title>
  </head>
  <body>
    <h1>Video Streaming Demonstration</h1>
    <img src="/video" margin-top:100px; style="transform:rotate(180deg)"; />
  </body>
</html>
"""

# Obsługa zapytań HTTP
def index(req, resp):
    yield from resp.awrite(index_web)

def send_frame():
    buf = camera.capture()
    yield (b'--frame\r\n'
           b'Content-Type: image/jpeg\r\n\r\n'
           + buf + b'\r\n')
    del buf
    gc.collect()

def video(req, resp):
    yield from picoweb.start_response(resp, content_type="multipart/x-mixed-replace; boundary=frame")
    while True:
        yield from resp.awrite(next(send_frame()))
        gc.collect()

ROUTES = [
    ("/", index),
    ("/video", video),
]

if __name__ == '__main__':
    import ulogging as logging
    logging.basicConfig(level=logging.INFO)
    
    while True:
        if pir_sensor.value() == 1:  # Sprawdzenie, czy czujnik PIR wykrył ruch
            print("Ruch wykryty! Uruchamianie serwera kamery...")
            led.value(1)  # Włącz LED

            camera_init()
            wifi_connect()

            # Tworzenie obiektu aplikacji z trasami
            app = picoweb.WebApp(__name__, ROUTES)
            app.run(debug=1, port=80, host="0.0.0.0")
            
            print("Serwer kamery uruchomiony.")
            
            # Po 2 minutach pracy sprawdź ponownie czujnik PIR przez 15 sekund
            utime.sleep(120)  # Serwer działa przez 2 minuty
            led.value(0)  # Wyłącz LED po zakończeniu działania serwera
            camera.deinit()  # Zatrzymaj kamerę po wyłączeniu serwera

            # Sprawdź przez 15 sekund, czy ruch nadal występuje
            for _ in range(15):
                if pir_sensor.value() == 1:
                    print("Ruch nadal wykrywany, kontynuowanie działania serwera.")
                    break
                utime.sleep(1)
            else:
                print("Brak ruchu. Przechodzenie do trybu light sleep.")
                lightsleep(10000)  # Przechodzenie do trybu light sleep na 10 sekund
        else:
            print("Brak ruchu, przechodzenie do trybu light sleep.")
            lightsleep(10000)  # Przechodzenie do trybu light sleep na 10 sekund
