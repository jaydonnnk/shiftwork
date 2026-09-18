import base64
import json
import os
import runpy
import socket
import sys
import threading
from http.server import HTTPServer
from pathlib import Path


sys.stderr.reconfigure(newline="\n")
fixture = json.loads(Path("fixture.json").read_bytes())["fault"]
learner = runpy.run_path("learner_service.py")


class FixtureHandler(learner["Handler"]):
    def do_POST(self):
        if fixture == "kill_mid_batch" and self.server.completed == 1:
            os._exit(23)
        if fixture == "connection_refused":
            self.server.server_close()
        if fixture in ("timeout", "truncated_body", "non_utf8_body"):
            self.rfile.read(int(self.headers["Content-Length"]))
            body = b'{"action":' if fixture == "truncated_body" else b'\xff\xfe{"action":"answer"}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body) + (50 if fixture == "truncated_body" else 0)))
            self.end_headers()
            self.wfile.flush()
            if fixture == "timeout":
                threading.Event().wait()
            self.wfile.write(body)
            self.wfile.flush()
            self.close_connection = True
        elif fixture == "env_probe":
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            print("request-bytes " + base64.b64encode(raw).decode("ascii"), file=sys.stderr, flush=True)
            body = json.dumps(learner["answer"](json.loads(raw), self.server.snapshot), separators=(",", ":")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_POST()
        self.server.completed += 1


print("trusted fixture ready", file=sys.stderr, flush=True)
if fixture == "env_probe":
    print("child-env " + json.dumps(dict(os.environ), sort_keys=True), file=sys.stderr, flush=True)
if fixture == "port_dead":
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        print(json.dumps({"port": reserved.getsockname()[1]}), flush=True)
        threading.Event().wait()
else:
    with HTTPServer(("127.0.0.1", 0), FixtureHandler) as server:
        server.snapshot = json.loads(Path("shop.json").read_bytes())
        server.completed = 0
        print(json.dumps({"port": server.server_port}), flush=True)
        while True:
            server.handle_request()
            if fixture == "connection_refused":
                threading.Event().wait()
