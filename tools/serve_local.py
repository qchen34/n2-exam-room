#!/usr/bin/env python3
"""Serve the practice app on loopback, including byte ranges for MP3 seeking."""

import argparse
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re


class PracticeHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.range_length = None
        path = Path(self.translate_path(self.path))
        requested = self.headers.get("Range")
        if not requested or path.suffix.lower() != ".mp3" or not path.is_file():
            return super().send_head()

        audio = path.open("rb")
        size = audio.seek(0, 2)
        bounds = re.fullmatch(r"bytes=(\d*)-(\d*)", requested)
        if bounds and any(bounds.groups()):
            first, last = bounds.groups()
            start = int(first) if first else max(0, size - int(last))
            end = min(int(last), size - 1) if first and last else size - 1
            if 0 <= start <= end:
                self.range_length = end - start + 1
                self.send_response(HTTPStatus.PARTIAL_CONTENT)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.send_header("Content-Length", str(self.range_length))
                self.end_headers()
                audio.seek(start)
                return audio

        audio.close()
        self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
        self.send_header("Content-Range", f"bytes */{size}")
        self.send_header("Content-Length", "0")
        self.end_headers()
        return None

    def copyfile(self, source, outputfile):
        if self.range_length is None:
            super().copyfile(source, outputfile)
            return
        remaining = self.range_length
        while remaining:
            block = source.read(min(remaining, 65536))
            if not block:
                break
            outputfile.write(block)
            remaining -= len(block)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    handler = partial(PracticeHandler, directory=str(root))
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"http://127.0.0.1:{server.server_port}/?audio=local", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
