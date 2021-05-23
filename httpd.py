#!usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import argparse
import datetime
import calendar
import socket
import select
import re
import os


REQUEST_FL_REGEX = re.compile(b'^(GET|HEAD) (.*) (HTTP.*)')
CONTENT_TYPE = {
    '.html': 'text/html',
    '.css':  'text/css',
    '.js':   'application/javascript',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png':  'image/png',
    '.gif':  'image/gif',
    '.swf':  'application/x-shockwave-flash',
    '.txt':  'text/plain'
}

EOL1 = b'\r\n\r\n'


def set_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', '--workers', default=1, type=int, help='Set numbers of workers')
    parser.add_argument('-r', '--doc_root', default='./root_dir', help='Set DOCUMENT_ROOT')
    return parser.parse_args()


class AsyncHTTPServer:

    request_queue_size = 100

    def __init__(self, server_host, server_port, RequestHandlerClass):
        self.server_host = server_host
        self.server_port = server_port
        self.RequestHandlerClass = RequestHandlerClass
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.epoll = None
        self.connections = {}
        self.requests = {}
        self.responses = {}

    def server_bind(self):
        self.socket.bind((self.server_host, self.server_port))

    def server_activate(self):
        self.socket.listen(self.request_queue_size)
        self.socket.setblocking(False)
        self.epoll = select.epoll()
        self.epoll.register(self.socket.fileno(), select.EPOLLIN)

    def server_forever(self, poll_interval=1):
        try:
            while True:
                events = self.epoll.poll(poll_interval)
                for fileno, event in events:
                    if fileno == self.socket.fileno():
                        self.server_socket_read_event()
                    elif event & select.EPOLLIN:
                        self.client_socket_read_event(fileno)
                    elif event & select.EPOLLOUT:
                        self.client_socket_write_event(fileno)
                    elif event & select.EPOLLHUP:
                        self.client_socket_hang_up(fileno)
        finally:
            self.epoll.unregister(self.socket.fileno())
            self.epoll.close()
            self.socket.close()

    def server_socket_read_event(self):
        try:
            conn, address = self.socket.accept()
            conn.setblocking(False)
            self.epoll.register(conn.fileno(), select.EPOLLIN)
            self.connections[conn.fileno()] = conn
            self.requests[conn.fileno()] = b""
        except:
            return

    def client_socket_read_event(self, fileno):
        chunk_size = 1024
        self.requests[fileno] += self.connections[fileno].recv(chunk_size)
        if EOL1 in self.requests[fileno]:
            self.epoll.modify(fileno, select.EPOLLOUT)

    def client_socket_write_event(self, fileno):
        self.responses[fileno] = self.RequestHandlerClass.get_response(self.requests[fileno])
        self.connections[fileno].sendall(self.responses[fileno])
        bytes_written = len(self.responses[fileno])
        self.responses[fileno] = self.responses[fileno][bytes_written:]
        if len(self.responses[fileno]) == 0:
            self.epoll.modify(fileno, 0)
            self.connections[fileno].shutdown(socket.SHUT_RDWR)

    def client_socket_hang_up(self, fileno):
        self.epoll.unregister(fileno)
        self.connections[fileno].close()
        del self.connections[fileno]


class CodeResponse:

    @classmethod
    def response_403_404_405(cls, stat):
        if stat == 405:
            response = b'HTTP/1.1 405 Method Not Allowed\r\n'
            response += b'Allow: GET, HEAD\r\n'
        elif stat == 404:
            response = b'HTTP/1.1 404 Not Found\r\n'
        elif stat == 403:
            response = b'HTTP/1.1 403 Forbidden\r\n'
        else:
            response = b''
        date_time = cls.get_time_in_utc()
        response += date_time.encode() + b'\r\n'
        response += b'Server: plhome/1.0\r\n'
        response += b'Connection: close\r\n\r\n'

        return response

    @classmethod
    def response_200(cls, content, content_size, tp, method):
        response = b'HTTP/1.1 200 OK\r\n'
        date_time = cls.get_time_in_utc()
        response += date_time.encode() + b'\r\n'
        response += b'Server: plhome/1.0\r\n'
        response += b'Connection: keep-alive\r\n'
        content_type = 'Content-Type: {}'.format(tp)
        response += content_type.encode() + b'\r\n'
        content_length = 'Content-Length: {}'.format(content_size)
        response += content_length.encode() + b'\r\n\r\n'
        if method == b'GET':
            response += content
        return response

    @staticmethod
    def get_time_in_utc():
        current_date = datetime.datetime.now()
        day_name = calendar.day_abbr[current_date.weekday()]
        day = current_date.day
        month = calendar.month_abbr[current_date.month]
        year = current_date.year
        hour = current_date.hour
        minute = current_date.minute
        second = current_date.second
        utc_dt = "Date: {day_name}, {day} {month} {year} {hour}:{minute}:{second} GMT".format(
            day_name=day_name,
            day=day,
            month=month,
            year=year,
            hour=hour,
            minute=minute,
            second=second
        )
        return utc_dt


class RequestHandlerClass:

    def __init__(self, document_root):
        self.document_root = document_root

    def get_response(self, request):

        if not request.strip():
            return CodeResponse.response_403_404_405(405)

        (head, body) = re.split(EOL1, request, 1)
        headers = head.split(b"\r\n")

        request_headers = self.parse_headers(headers)

        if request_headers is None:
            response = CodeResponse.response_403_404_405(405)
        else:
            response = self.method_response(request_headers)
        return response

    def get_path(self, headers):
        path = headers[b'path']
        abs_path = os.path.abspath(path)
        components = abs_path.split(b'/')
        if abs_path[-1] != path[-1]:
            file_name = components[-1].decode()
            file_name += path.decode()[-1]
            components[-1] = file_name.encode()
        for el in range(len(components)):
            try:
                components[el] = bytes.fromhex(components[el].decode().replace('%', ''))
            except ValueError:
                pass
            if b'?' in components[el]:
                components[el] = components[el].partition(b'?')[0]
            components[el] = components[el].replace(b'%20', b' ')

        return os.path.join(os.path.abspath(self.document_root).encode(), *components)

    def method_response(self, headers):

        method = headers[b'method']

        abs_path = self.get_path(headers).decode()
        abs_root_path = os.path.abspath(self.document_root)

        if abs_root_path not in abs_path:
            response = CodeResponse.response_403_404_405(403)
        elif os.path.isdir(abs_path):
            response = self.try_to_find_index(abs_path, method)
        else:
            if os.path.exists(abs_path):
                response = self.return_file(abs_path, method)
            else:
                response = CodeResponse.response_403_404_405(404)

        return response

    def try_to_find_index(self, checking_path, method):
        index = 'index.html'
        if index in os.listdir(checking_path):
            index_path = os.path.join(checking_path, index)
            content_length = os.path.getsize(index_path)
            with open(index_path, 'rb') as fb:
                content = fb.read()
                response = CodeResponse.response_200(content, content_length, CONTENT_TYPE['.html'], method)
        else:
            response = CodeResponse.response_403_404_405(404)

        return response

    def return_file(self, checking_path, method):
        filename, ext = os.path.splitext(checking_path)
        tp = CONTENT_TYPE.get(ext)
        content_size = os.path.getsize(checking_path)
        content = ""
        if method == b'GET':
            with open(checking_path, 'rb') as fb:
                content = fb.read()
        return CodeResponse.response_200(content, content_size, tp, method)

    def parse_headers(self, headers):
        request_headers = {}

        first_line = headers.pop(0)
        res = REQUEST_FL_REGEX.match(first_line.strip())
        if res:
            request_headers[b'method'] = res.group(1)
            request_headers[b'path'] = res.group(2)
            request_headers[b'http'] = res.group(3)
        else:
            return None

        for key, val in enumerate(headers):
            (name, value) = re.split(b'\s*:\s*', val, 1)
            request_headers[name] = value

        return request_headers


def worker():
    http = AsyncHTTPServer(
        server_host='localhost',
        server_port=80,
        RequestHandlerClass=RequestHandlerClass(document_root)
    )
    http.server_bind()
    http.server_activate()
    http.server_forever()


if __name__ == '__main__':
    sys_args = set_args()
    workers = sys_args.workers
    document_root = sys_args.doc_root

    for _ in range(workers):
        th = threading.Thread(target=worker)
        th.start()

