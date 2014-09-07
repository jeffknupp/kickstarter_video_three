"""An HTTP proxy that supports IPv6 as well as the HTTP CONNECT method, among
other things."""

# Standard libary imports
import socket
import threading
import select

__version__ = '0.1.0 Draft 1'
BUFFER_LENGTH = 8192
VERSION = 'Python Proxy/{}'.format(__version__)
HTTP_VERSION = 'HTTP/1.1'


class Proxy(object):
    """Handles connections between the HTTP client and HTTP server."""
    def __init__(self, connection):
        self.client = connection
        self.client_buffer = ''
        self.target = None
        method, path, protocol = self.get_base_header()
        if method == 'CONNECT':
            self.method_connect(path)
        else:
            self.method_others(method, path, protocol)

    def get_base_header(self):
        """Return a tuple of (method, path, protocol) from the recieved
        message."""
        while '\n' not in self.client_buffer:
            self.client_buffer += self.client.recv(BUFFER_LENGTH)
        (data, _, self.client_buffer) = self.client_buffer.partition('\n')
        return data.split()

    def method_connect(self, path):
        """Handle HTTP CONNECT messages."""
        self._connect_to_target(path)
        self.client.send('{http_version} 200 Connection established\n'
                         'Proxy-agent: {version}\n\n'.format(
                             http_version=HTTP_VERSION,
                             version=VERSION))
        self.client_buffer = ''
        self._read_write()

    def method_others(self, method, path, protocol):
        """Handle all non-HTTP CONNECT messages."""
        path = path[len('http://'):]
        host, _, path = path.partition('/')
        path = '/{}'.format(path)
        self._connect_to_target(host)
        self.target.send('{method} {path} {protocol}\n{client_buffer}'.format(
            method=method,
            path=path,
            protocol=protocol,
            client_buffer=self.client_buffer))
        self.client_buffer = ''
        self._read_write()

    def _connect_to_target(self, host):
        """Create a connection to the HTTP server specified by *host*."""
        port = 80
        if ':' in host:
            host, _, port = host.partition(':')
        (socket_family, _, _, _, address) = socket.getaddrinfo(host, port)[0]
        self.target = socket.socket(socket_family)
        self.target.connect(address)

    def _read_write(self):
        """Read data from client connection and forward to server
        connection."""
        sockets = [self.client, self.target]
        try:
            while 1:
                (receive, _, error) = select.select(sockets, [], sockets, 10)
                if error:
                    break
                elif receive:
                    for source in receive:
                        data = source.recv(BUFFER_LENGTH)
                        if not data:
                            return
                        if source is self.client:
                            destination = self.target
                        else:
                            destination = self.client
                        destination.sendall(data)
        finally:
            self.client.close()
            self.target.close()


def start_server():
    """Start the HTTP proxy server."""
    host = 'localhost'
    port = 8080
    listener = socket.socket(socket.AF_INET)
    listener.bind((host, port))
    print 'Serving on {0}:{1}.'.format(host, port)
    listener.listen(0)
    while 1:
        connection, address = listener.accept()
        print 'Got connection from {}'.format(address)
        threading.Thread(
            target=Proxy, args=(connection, )).run()

if __name__ == '__main__':
    start_server()
