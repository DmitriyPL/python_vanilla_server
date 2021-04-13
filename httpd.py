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


def set_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', '--workers', default=1, type=int, help='Set numbers of workers')
    parser.add_argument('-r', '--doc_root', default='./root_dir', help='Set DOCUMENT_ROOT')
    return parser.parse_args()


class MyHTTPServer:

    request_queue_size = 100

    def __init__(self, server_host, server_port, document_root):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.server_host = server_host
        self.server_port = server_port
        self.epoll = None
        self.connections = {}
        self.requests = {}
        self.responses = {}
        self.document_root = document_root

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
                    elif event == select.EPOLLIN:
                        self.client_socket_read_event(fileno)
                    elif event == select.EPOLLOUT:
                        self.client_socket_write_event(fileno)
                    elif event == select.EPOLLHUP:
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
        self.connections[fileno].settimeout(0.5)
        while True:
            try:
                chunk = self.connections[fileno].recv(chunk_size)
                if not chunk:
                    break
            except:
                break
            self.requests[fileno] += chunk
        self.epoll.modify(fileno, select.EPOLLOUT)
        # print(self.requests[fileno])

    def client_socket_write_event(self, fileno):
        self.responses[fileno] = self.get_response(fileno)
        bytes_written = self.connections[fileno].send(self.responses[fileno])
        self.responses[fileno] = self.responses[fileno][bytes_written:]
        if len(self.responses[fileno]) == 0:
            self.epoll.modify(fileno, 0)
            try:
                self.connections[fileno].shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.connections[fileno].close()

    def client_socket_hang_up(self, fileno):
        self.epoll.unregister(fileno)
        self.connections[fileno].close()
        del self.connections[fileno]

    def get_response(self, fileno):

        if not self.requests[fileno].strip():
            return self.return_response_405()

        (head, body) = re.split(b"\r\n\r\n", self.requests[fileno], 1)
        headers = head.split(b"\r\n")

        request_headers = self.parse_headers(headers)

        if request_headers is None:
            response = self.return_response_405()
        else:
            response = self.method_response(request_headers)

        return response

    def get_path(self, headers):
        components = headers[b'pass'].split(b'/')
        for el in range(len(components)):
            try:
                components[el] = bytes.fromhex(components[el].decode().replace('%', ''))
            except ValueError:
                pass
            if b'?' in components[el]:
                components[el] = components[el].partition(b'?')[0]
            components[el] = components[el].replace(b'%20', b' ')

        return os.path.join(self.document_root.encode(), *components)

    def method_response(self, headers):

        method = headers[b'method']

        path = self.get_path(headers)
        abs_root_path = os.path.abspath(self.document_root)
        abs_path = os.path.abspath(path).decode()

        if abs_root_path not in abs_path:
            response = self.return_response_403()
        elif os.path.isdir(path):
            response = self.try_to_find_index(path, method)
        else:
            if os.path.exists(path):
                response = self.return_file(path, method)
            else:
                response = self.return_response_404()

        return response

    def try_to_find_index(self, checking_path, method):
        index = b'index.html'
        if index in os.listdir(checking_path):
            with open(os.path.join(checking_path, index), 'rb') as fb:
                content = fb.read()
                response = self.return_response_200(content, CONTENT_TYPE['.html'], method)
        else:
            response = self.return_response_404()

        return response

    def return_file(self, checking_path, method):
        filename, ext = os.path.splitext(checking_path)
        tp = CONTENT_TYPE.get(ext.decode())
        with open(checking_path, 'rb') as fb:
            content = fb.read()
        return self.return_response_200(content, tp, method)

    def parse_headers(self, headers):
        request_headers = {}

        first_line = headers.pop(0)
        res = REQUEST_FL_REGEX.match(first_line.strip())
        if res:
            request_headers[b'method'] = res.group(1)
            request_headers[b'pass'] = res.group(2)
            request_headers[b'http'] = res.group(3)
        else:
            return None

        for key, val in enumerate(headers):
            (name, value) = re.split(b'\s*:\s*', val, 1)
            request_headers[name] = value

        return request_headers

    def return_response_405(self):
        response = b'HTTP/1.1 405 Method Not Allowed\r\n'
        response += b'Allow: GET, HEAD\r\n'
        date_time = self.get_time_in_utc()
        response += date_time.encode() + b'\r\n'
        response += b'Server: plhome/1.0\r\n'
        response += b'Connection: close\r\n\r\n'
        return response

    def return_response_404(self):
        response = b'HTTP/1.1 404 Not Found\r\n'
        date_time = self.get_time_in_utc()
        response += date_time.encode() + b'\r\n'
        response += b'Server: plhome/1.0\r\n'
        response += b'Connection: close\r\n\r\n'
        return response

    def return_response_403(self):
        response = b'HTTP/1.1 403 Forbidden\r\n'
        date_time = self.get_time_in_utc()
        response += date_time.encode() + b'\r\n'
        response += b'Server: plhome/1.0\r\n'
        response += b'Connection: close\r\n\r\n'
        return response

    def return_response_200(self, content, tp, method):
        response = b'HTTP/1.1 200 OK\r\n'
        date_time = self.get_time_in_utc()
        response += date_time.encode() + b'\r\n'
        response += b'Server: plhome/1.0\r\n'
        response += b'Connection: keep-alive\r\n'
        content_type = 'Content-Type: {}'.format(tp)
        response += content_type.encode() + b'\r\n'
        content_length = 'Content-Length: {}'.format(len(content))
        response += content_length.encode() + b'\r\n\r\n'
        if method == b'GET':
            response += content
        return response

    def get_time_in_utc(self):
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


def worker():
    http = MyHTTPServer(
        server_host='localhost',
        server_port=80,
        document_root=document_root
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

