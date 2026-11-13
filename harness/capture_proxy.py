"""Local capture proxy / Proxy local de captura.

Saves the body of every /chat/completions request to ./captures and answers with fixed text,
so the agent executes nothing. Other paths are forwarded to Ollama. Listens on 127.0.0.1 only.
Guarda el cuerpo de cada /chat/completions en ./captures y responde con texto fijo (no se
ejecuta nada). El resto se reenvía a Ollama. Solo escucha en 127.0.0.1.

Usage: python3 capture_proxy.py 18434, then point the agent's base URL to http://127.0.0.1:18434/v1
The captures contain the agent's full prompt (instructions, memory): do not publish them.
"""
import json, sys, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

OUT = Path(__file__).resolve().parent / 'captures'
UP = 'http://127.0.0.1:11434'
N = [0]
OUT.mkdir(exist_ok=True)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _forward(self, body=None):
        req = urllib.request.Request(UP + self.path, data=body, method=self.command,
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read(); code = r.status
        except urllib.error.HTTPError as e:
            data = e.read(); code = e.code
        self.send_response(code); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        self._forward()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        if not self.path.endswith('/chat/completions'):
            return self._forward(body)
        N[0] += 1
        (OUT / f'req-{int(time.time())}-{N[0]}.json').write_bytes(body)
        d = json.loads(body)
        print('captured', N[0], 'tools=', len(d.get('tools') or []), 'stream=', d.get('stream'), flush=True)
        txt = 'captura'
        if d.get('stream'):
            self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.end_headers()
            base = {'id': 'cap', 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': d.get('model')}
            for ch in ({'delta': {'role': 'assistant', 'content': txt}, 'index': 0, 'finish_reason': None},
                       {'delta': {}, 'index': 0, 'finish_reason': 'stop'}):
                self.wfile.write(('data: ' + json.dumps({**base, 'choices': [ch]}) + '\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')
        else:
            out = json.dumps({'id': 'cap', 'object': 'chat.completion', 'created': int(time.time()), 'model': d.get('model'),
                              'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': txt}, 'finish_reason': 'stop'}],
                              'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(out))); self.end_headers(); self.wfile.write(out)


ThreadingHTTPServer(('127.0.0.1', int(sys.argv[1]) if len(sys.argv) > 1 else 18434), H).serve_forever()
