from threading import Thread
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

from tray import _SimpleTray, tray

class _HttpHandler(BaseHTTPRequestHandler):
    """
    Extracts the response from the class attribute "_HttpHandler.dictionary".,
    according to the path requested. GET /a/b/c is evaluated as
    _HttpHandler.dictionary['a']['b']['c'].
    """
    def do_GET(self):
        if self.path.startswith('/'):
            self.path = self.path[1:]

        value = _HttpHandler.dictionary
        for part in self.path.split('/'):
            value = value[part]

        self.wfile.write(str(value))

def start_http_server(dictionary, port=80):
    """
    Starts an HTTP server in a new thread that returns the values from the
    given dictionary. GET /a/b/c is evaluated as dictionary['a']['b']['c'].

    Starts a tray icon if one hasn't been set yet so the user can close the
    application.
    """
    if _SimpleTray.instance is None:
        tray()

    server_address = ('', port)
    _HttpHandler.dictionary = dictionary
    def handle_requests():
        httpd = HTTPServer(server_address, _HttpHandler)
        while _SimpleTray.instance != None:
            httpd.handle_request()
    Thread(target=handle_requests).start()
