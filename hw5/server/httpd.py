import argparse
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import unquote

STATUSES_READABLE = {
    200: "OK",
    403: "FORBIDDEN",
    404: "NOT FOUND",
    405: "METHOD NOT ALLOWED",
}

CONTENT_TYPES_MAP = {
    'html': 'text/html',
    'css': 'text/css',
    'js': 'text/javascript',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'swf': 'application/x-shockwave-flash',
}


@dataclass
class Request:
    method: str
    location: str
    http_version: str

    @classmethod
    def from_raw(cls, raw_request: list[str]):
        method, path, http_version = raw_request[0].split()
        path = unquote(path)
        location = path.split('?')[0]

        return cls(
            method=method,
            location=location,
            http_version=http_version,
        )


@dataclass
class Response:
    status: int
    data: bytes | None = None
    content_type: str | None = None
    method: str | None = None

    def to_raw(self):
        current_time = time.strftime(
            '%a, %d %b %Y %I:%M:%S %Z',
            time.gmtime(),
        )

        headers = [
            f'HTTP/1.1 {self.status} {STATUSES_READABLE[self.status]}',
            f'Date: {current_time}',
            'Server: OTUServer',
        ]

        if self.data is not None:
            header_type = CONTENT_TYPES_MAP.get(
                self.content_type,
                'text/plain',
            )
            headers.append(
                f'Content-Type: {header_type}',
            )
            headers.append(f'Content-Length: {len(self.data)}')

        headers_raw = '\r\n'.join(headers)

        if self.data is None or self.method == 'HEAD':
            data_raw = bytes()
        else:
            data_raw = self.data

        return f'{headers_raw}\r\n\r\n'.encode('utf-8') + data_raw


class HTTPServer:
    def __init__(self, host, port, max_workers, content_root):
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self.content_root = content_root

    def _handle_request(self, request: Request) -> Response:
        if request.method not in ['GET', 'HEAD']:
            return Response(status=405)

        relative_path = request.location.strip('/')
        if request.location.endswith('/'):
            relative_path = os.path.join(
                relative_path,
                'index.html',
            )

        path = os.path.join(
            self.content_root,
            relative_path
        )

        if '..' in path.split('/'):
            return Response(status=403)

        try:
            with open(path, 'rb') as f:
                data = f.read()
        except (FileNotFoundError, NotADirectoryError):
            return Response(status=404)

        return Response(
            status=200,
            data=data,
            content_type=path.split('.')[-1].lower(),
            method=request.method,
        )

    def _handle_connection(self, connection: socket.socket):
        with connection:
            with connection.makefile('rw') as read_fd:
                raw_request = []
                while request_line := read_fd.readline().strip():
                    raw_request.append(request_line)

            if not raw_request:
                # probably not http
                return

            request = Request.from_raw(raw_request)
            response = self._handle_request(request)

            with connection.makefile('wb') as write_fd:
                write_fd.write(response.to_raw())

    def _serve_forever(self, server: socket.socket):
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while True:
                connection, addr = server.accept()
                executor.submit(self._handle_connection, connection)

    def serve(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen(self.max_workers)
            self._serve_forever(server)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', dest='root', action='store')
    parser.add_argument('-w', dest='workers_count', action='store', type=int)
    args = parser.parse_args()

    server = HTTPServer('0.0.0.0', 80, args.workers_count, args.root)
    server.serve()
