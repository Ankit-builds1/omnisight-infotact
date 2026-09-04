from playwright.sync_api import sync_playwright
import http.server
import socketserver
import threading
from pathlib import Path

html_path = Path("screenshots/broken/broken-button-clip/assets/broken-button-clip.html")
serve_dir = html_path.parent
port = 8099

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(serve_dir), **kwargs)

httpd = socketserver.TCPServer(("localhost", port), Handler)
thread = threading.Thread(target=httpd.serve_forever, daemon=True)
thread.start()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(f"http://localhost:{port}/{html_path.name}")
    page.wait_for_timeout(1000)

    button = page.query_selector(".inventory_item:first-child .btn_inventory")
    if button is None:
        print("Button not found!")
    else:
        box = button.bounding_box()
        print(f"Button bounding box: {box}")
        print(f"left fraction   = {box['x']/1920:.3f}")
        print(f"right fraction  = {(box['x']+box['width'])/1920:.3f}")
        print(f"top fraction    = {box['y']/1080:.3f}")
        print(f"bottom fraction = {(box['y']+box['height'])/1080:.3f}")

    browser.close()

httpd.shutdown()