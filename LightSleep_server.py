import esp
import webrepl
from machine import Pin, lightsleep
import picoweb
import utime
import camera
import gc

SSID = "Orange_Swiatlowod_FE30"  # Nazwa sieci WiFi
PASSWORD = "pFDdeauyRwHt56USRo"  # Hasło sieci WiFi

# Konfiguracja pinu PIR i LED
pir_sensor = Pin(13, Pin.IN)  # Czujnik PIR na pinie 13
led = Pin(2, Pin.OUT)  # LED na pinie 2

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
    camera.deinit()  # Deinitialize camera if previously initialized
    try:
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
        print("Camera initialized successfully.")
    except Exception as e:
        print("Error initializing camera:", e)

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
    try:
        buf = camera.capture()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n'
               + buf + b'\r\n')
        del buf
        gc.collect()
    except Exception as e:
        print("Error capturing frame:", e)

def video(req, resp):
    yield from picoweb.start_response(resp, content_type="multipart/x-mixed-replace; boundary=frame")
    while True:
        try:
            yield from resp.awrite(next(send_frame()))
            gc.collect()
        except Exception as e:
            print("Error during video streaming:", e)
            break  # Exit the loop if there's an error

ROUTES = [
    ("/", index),
    ("/video", video),
]

if __name__ == '__main__':
    import ulogging as logging
    logging.basicConfig(level=logging.INFO)
    
    # Utworzenie obiektu aplikacji Picoweb
    app = picoweb.WebApp(__name__, ROUTES)

    while True:
        print("Entering light sleep mode...")
        lightsleep(10000)  # Tryb uśpienia na 10 sekund

        if pir_sensor.value() == 1:  # Sprawdzanie wykrycia ruchu
            print("Motion detected! Starting camera server...")
            led.value(1)  # Włączenie diody LED
            
            # Inicjalizacja kamery i połączenia WiFi
            camera_init()
            if not camera:
                print("Camera failed to initialize. Skipping server start.")
                continue  # Skip server start if camera is not initialized
            wifi_connect()

            try:
                # Uruchomienie serwera
                app.run(debug=1, port=80, host="192.168.1.23")
                print("Camera server started.")
                
                # Utrzymanie serwera przez minutę
                utime.sleep(60)  # Serwer działa przez 1 minutę
            except Exception as e:
                print("Error in running server:", e)
            
            led.value(0)  # Wyłączenie diody LED
            
            # Sprawdzanie wykrycia ruchu przez 15 sekund po zakończeniu serwera
            motion_still_detected = False
            for _ in range(15):
                if pir_sensor.value() == 1:
                    print("Motion still detected, continuing server operation.")
                    motion_still_detected = True
                    break
                utime.sleep(1)

            if not motion_still_detected:
                print("No motion detected. Shutting down camera.")
                camera.deinit()  # Wyłączenie kamery
                led.value(0)     # Wyłączenie diody LED
        else:
            print("No motion detected. Continuing light sleep.")
            lightsleep(10000)  # Tryb uśpienia na 10 sekund
