"""
ground station control code:

this opens a server of some kind that the drones communicate with.
supports:
    receiving notifs about drone pos
    reciving info about blockers
    querying corridors
    managing corridors
"""

import http.server
import socketserver

PORT = 80

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print("serving at port", PORT)
    httpd.serve_forever()
