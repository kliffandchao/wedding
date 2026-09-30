"""Dev server for the prototype.

Python's stock http.server sends Last-Modified and no Cache-Control, so browsers
heuristically cache HTML, SVG and JS. During this build that served stale copies
twice (an old logo SVG, and an old map tile provider) and both looked like real
bugs. This subclass disables caching outright.
"""
import functools
import http.server
import socketserver
import sys
from pathlib import Path

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4321
ROOT = Path(__file__).resolve().parent


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_response(self, *args, **kwargs):
        # drop Last-Modified so conditional requests can't 304
        super().send_response(*args, **kwargs)

    def send_header(self, keyword, value):
        if keyword.lower() == "last-modified":
            return
        super().send_header(keyword, value)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def lan_ips():
    """Every non-loopback IPv4 this machine answers on, for phone testing."""
    import socket
    out = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in out:
                out.append(ip)
    except OSError:
        pass
    return out


if __name__ == "__main__":
    handler = functools.partial(NoCacheHandler, directory=str(ROOT))
    # 0.0.0.0, not 127.0.0.1 — otherwise phones on the same Wi-Fi can't reach it.
    # This exposes the prototype to everyone on the local network; fine for
    # placeholder content, don't leave it running on public Wi-Fi.
    with Server(("0.0.0.0", PORT), handler) as httpd:
        print(f"prototype (no-cache) on http://localhost:{PORT}/")
        for ip in lan_ips():
            print(f"  on this network:  http://{ip}:{PORT}/")
        httpd.serve_forever()
