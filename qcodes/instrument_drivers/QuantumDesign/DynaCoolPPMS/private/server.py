import socket
import select
from msvcrt import kbhit, getch  # type: ignore
import logging

from qcodes.instrument_drivers.QuantumDesign.\
    DynaCoolPPMS.private.commandhandler import CommandHandler

command_handler = CommandHandler()

log = logging.getLogger(__name__)

RECEIVE_BUFFER_SIZE = 4096
PORT = 5000
ADDRESS = ''
LINE_TERM = '\r\n'

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((ADDRESS, PORT))
server_socket.listen(10)

# Dictionary to keep track of sockets and addresses.
# Keys are sockets and values are addresses.
# Add server socket to the dictionary first.
socket_dict = {server_socket: (ADDRESS, PORT)}

print('Server started on port {0}.'.format(PORT))
print('Press ESC to exit.')

keep_going = True
cmd_buffer: str = ''

while keep_going:
    # Get the list sockets which are ready to be read through select
    # 1 second timeout so that we can process keyboard events
    read_sockets = select.select(list(socket_dict.keys()), [], [], 1)[0]

    # Keyboard
    if kbhit():
        if ord(getch()) == 27:
            print('Server exiting')
            break

    for sock in read_sockets:
        # New connection
        if sock == server_socket:
            sock_fd, address = server_socket.accept()
            socket_dict[sock_fd] = address
            print('Client ({0}, {1}) connected.'.format(*address))
            log.info('Client ({0}, {1}) connected.'.format(*address))
            mssg = f'Connected to socket server.{LINE_TERM}'
            sock_fd.send(bytes(mssg, 'utf-8'))

        # Incoming message from existing connection
        else:
            data = sock.recv(RECEIVE_BUFFER_SIZE).decode('utf-8')
            log.debug(f'Received data: {data}')
            if data:
                data = data.replace('\n', '\r')
                data = data.replace('\r\r', '\r')
                cmd_buffer += data
        idx = cmd_buffer.find('\r')

        if idx >= 0:
            command = cmd_buffer[:idx].upper().strip(' ')
            cmd_buffer = cmd_buffer[idx+1:]
            if command == 'EXIT':
                # send an error code, since the driver expects that for all
                # commands
                sock.send(b'0')
                print('Server exiting.')
                keep_going = False
            elif command == 'CLOSE':
                # send an error code, since the driver expects that for all
                # commands
                sock.send(b'0')
                print('Client ({0}, {1}) disconnected.'.format(*socket_dict[sock]))
                log.info('Client ({0}, {1}) disconnected.'.format(*socket_dict[sock]))
                socket_dict.pop(sock, None)
                sock.close()
            else:
                response = command_handler(command)
                sock.send(bytes(f'{response}{LINE_TERM}', 'utf-8'))

server_socket.close()
