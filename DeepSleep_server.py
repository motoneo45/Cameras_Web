from time import sleep, time
from machine import Pin, deepsleep
import esp32


# Definicje pinu dla LED i PIR
led = Pin(2, Pin.OUT)  # LED jako wskaźnik działania serwera
pir_sensor = Pin(13, Pin.IN)  # PIR sensor na pinie 13

# Czas działania serwera w sekundach oraz czas sprawdzania ruchu
server_runtime = 120  # Czas działania serwera - 2 minuty
motion_check_time = 20  # Czas sprawdzania ruchu - 20 sekund

from time import sleep, time
from machine import Pin, deepsleep
import esp32

# Definicje pinu dla LED i PIR
led = Pin(2, Pin.OUT)  # LED jako wskaźnik działania serwera
pir_sensor = Pin(13, Pin.IN)  # PIR sensor na pinie 13

# Czas działania serwera w sekundach oraz czas sprawdzania ruchu
server_runtime = 120  # Czas działania serwera - 2 minuty
motion_check_time = 20  # Czas sprawdzania ruchu - 20 sekund

def start_camera_server():
    import picoweb
    import utime
    import camera
    import gc

    SSID = "Orange_Swiatlowod_FE30"
    PASSWORD = "pFDdeauyRwHt56USRo"

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
                    print("Connection timeout!")
                    break
        if wlan.isconnected():
            print('Network config:', wlan.ifconfig())

    def camera_init():
        # Disable and reinitialize camera
        camera.deinit()
        camera.init(0, d0=4, d1=5, d2=18, d3=19, d4=36, d5=39, d6=34, d7=35,
                    format=camera.JPEG, framesize=camera.FRAME_VGA, 
                    xclk_freq=camera.XCLK_20MHz,
                    href=23, vsync=25, reset=-1, pwdn=-1,
                    sioc=27, siod=26, xclk=21, pclk=22, fb_location=camera.PSRAM)

        camera.framesize(camera.FRAME_VGA) # Set the camera resolution
        camera.flip(1)
        camera.mirror(1)
        camera.saturation(0)
        camera.brightness(0)
        camera.contrast(0)
        camera.quality(10)
        camera.speffect(camera.EFFECT_NONE)
        camera.whitebalance(camera.WB_NONE)

    # HTTP Response Content
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

    # HTTP Response
    def index(req, resp):
        yield from resp.awrite(index_web)

    # Send camera frames
    def send_frame():
        buf = camera.capture()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n'
               + buf + b'\r\n')
        del buf
        gc.collect()
        
    # Video transmission
    def video(req, resp):
        yield from picoweb.start_response(resp, content_type="multipart/x-mixed-replace; boundary=frame")
        while True:
            yield from resp.awrite(next(send_frame()))
            gc.collect()

    ROUTES = [
        ("/", index),
        ("/video", video),
    ]

    import ulogging as logging
    logging.basicConfig(level=logging.INFO)
    camera_init()
    wifi_connect()

    # Create a Picoweb app instance
    app = picoweb.WebApp(__name__, ROUTES)
    app.run(debug=1, port=80, host="0.0.0.0")
    print("Camera server started.")

# Funkcja inicjalizująca tryb głębokiego uśpienia
def enter_deep_sleep():
    print("Przechodzę w tryb uśpienia, oczekiwanie na ruch...")
    led.value(0)  # Wyłącz LED
    esp32.wake_on_ext0(pin=pir_sensor, level=esp32.WAKEUP_ANY_HIGH)
    deepsleep()

# Pętla główna
while True:
    # Pierwsze wejście do deep sleep, wybudzenie tylko przez ruch
    enter_deep_sleep()

    # Po wybudzeniu przez PIR - serwer kamery i sygnalizacja LED
    print("Ruch wykryty! Uruchamianie serwera...")
    led.value(1)  # Włącz LED
    start_camera_server()  # Uruchom serwer kamery

    # Utrzymywanie serwera przez server_runtime
    start_time = time()
    while time() - start_time < server_runtime:
        sleep(1)  # Czeka 1 sekundę

    # Sprawdzanie obecności ruchu przez motion_check_time
    print("Sprawdzanie ruchu...")
    for _ in range(15):
        if pir_sensor.value() == 1:  # Ruch wykryty, resetowanie czasu
            print("Ruch wykryty, przedłużenie działania serwera")
            start_time = time()  # Resetujemy czas działania serwera
        else:
            print("Brak ruchu, serwer zostanie zamknięty.")
        sleep(1)  # Czeka 1 sekundę na kolejne sprawdzenie

    # Zamknięcie serwera i powrót do deep sleep
    print("Serwer wyłączony, powrót do uśpienia.")

