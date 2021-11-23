import argparse
import mimetypes
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import unquote

REQUEST_SIZE_LIMIT = 1024 * 1024

STATUSES_READABLE = {
    200: "OK",
    403: "FORBIDDEN",
    404: "NOT FOUND",
    405: "METHOD NOT ALLOWED",
    413: "PAYLOAD TOO LARGE",
}

mimetypes.init()


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
    data_size: int = 0
    path: str | None = None
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
            header_type, _ = mimetypes.guess_type(self.path)
            if header_type is None:
                header_type = 'text/plain'

            headers.append(
                f'Content-Type: {header_type}',
            )
            headers.append(f'Content-Length: {self.data_size}')

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

        root_abspath = os.path.abspath(self.content_root)
        abspath = os.path.abspath(path)
        if os.path.commonprefix([abspath, root_abspath]) != root_abspath:
            return Response(status=403)

        try:
            if request.method == 'HEAD':
                data = b''
                data_size = os.path.getsize(path)
            else:
                with open(path, 'rb') as f:
                    data = f.read()
                    data_size = len(data)
        except (FileNotFoundError, NotADirectoryError):
            return Response(status=404)

        return Response(
            status=200,
            data=data,
            data_size=data_size,
            path=path,
            method=request.method,
        )

    @staticmethod
    def _write_response(connection: socket.socket, response: Response) -> None:
        with connection.makefile('wb') as write_fd:
            write_fd.write(response.to_raw())

    def _handle_connection(self, connection: socket.socket):
        with connection:
            with connection.makefile('r', newline='\r\n') as read_fd:
                raw_request = []
                request_size = 0
                while request_line := read_fd.readline(REQUEST_SIZE_LIMIT + 1):
                    request_size += len(request_line)

                    if request_size > REQUEST_SIZE_LIMIT:
                        break

                    if request_line == '\r\n':
                        # possible only if it is two consecutive CRLF's
                        break

                    striped_line = request_line.rstrip('\r\n')
                    if striped_line:
                        raw_request.append(request_line.strip())

            if request_size > REQUEST_SIZE_LIMIT:
                self._write_response(connection, Response(status=413))

            if not raw_request:
                # probably not http
                return

            request = Request.from_raw(raw_request)
            response = self._handle_request(request)

            self._write_response(connection, response)

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
