import json
import logging
from threading import Thread, current_thread
import time
import zmq
import zmq.asyncio
import numpy as np

class ZMQClient:
    def __init__(self, app_name="zmq-client", ip="tcp://localhost", port=5556):
        self._timer = None

        self.context = zmq.asyncio.Context()
        self.heartbeat_socket = None
        self.data_socket = None
        self.poller = zmq.asyncio.Poller()
        self.ip = ip
        self.port = port
        self.message_num = 0
        self.socket_waits_reply = False

        self.app_name = app_name

        self.last_heartbeat_time = 0
        self.last_reply_time = time.time()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        self.init_socket()

    def init_socket(self):
        """Initialize the data socket"""
        if not self.data_socket:
            ip_string = f'{self.ip}:{self.port}'
            self.logger.info("Initializing data socket on " + ip_string)
            self.data_socket = self.context.socket(zmq.SUB)
            self.data_socket.connect(ip_string)
            self.data_socket.setsockopt(zmq.SUBSCRIBE, b'')
            self.poller.register(self.data_socket, zmq.POLLIN)

        if not self.heartbeat_socket:
            ip_string = f'{self.ip}:{self.port + 1}'
            self.logger.info("Initializing heartbeat socket on " + ip_string)
            self.heartbeat_socket = self.context.socket(zmq.REQ)
            self.heartbeat_socket.connect(ip_string)
            self.poller.register(self.heartbeat_socket, zmq.POLLIN)

    def send_heartbeat(self):
        """Sends heartbeat message to ZMQ Interface,
           to indicate that the app is alive
        """
        d = {'application': self.app_name,
             'uuid': self.app_name,
             'type': 'heartbeat'}
        j_msg = json.dumps(d)
        self.logger.debug("sending heartbeat")
        self.heartbeat_socket.send(j_msg.encode('utf-8'))
        self.last_heartbeat_time = time.time()
        self.socket_waits_reply = True

    async def receive_data(self):
        while True:
            if (time.time() - self.last_heartbeat_time) > 2.:
                if self.socket_waits_reply:
                    print("heartbeat haven't got reply, retrying...")
                    self.last_heartbeat_time += 1.
                    if (time.time() - self.last_reply_time) > 10.:
                        # reconnecting the socket as per
                        # the "lazy pirate" pattern (see the ZeroMQ guide)
                        print("connection lost, trying to reconnect")
                        self.poller.unregister(self.data_socket)
                        self.data_socket.close()
                        self.data_socket = None

                        self.init_socket()

                        self.socket_waits_reply = False
                        self.last_reply_time = time.time()
                else:
                    self.send_heartbeat()

            # check poller
            socks = dict(await self.poller.poll(timeout=1)) # in milliseconds

            if not socks:
                continue

            if self.data_socket in socks:

                try:
                    message = await self.data_socket.recv_multipart()
                except zmq.ZMQError as err:
                    print("got error: {0}".format(err))
                    break

                if message:

                    self.message_num += 1
                    yield message

                #     if len(message) < 2:
                #         print("no frames for message: ", message[0])
                #     try:
                #         header = json.loads(message[1].decode('utf-8'))
                #     except ValueError as e:
                #         print("ValueError: ", e)
                #         print(message[1])

                #     if header['message_num'] != self.message_num:
                #         print("Missed a message at number", self.message_num)

                #     self.message_num = header['message_num']

                #     if header['type'] == 'data':
                #         c = header['content']
                #         num_samples = c['num_samples']
                #         channel_num = c['channel_num']
                #         sample_rate = c['sample_rate']

                #         if channel_num == 1:
                #             try:
                #                 n_arr = np.frombuffer(message[2],
                #                                         dtype=np.float32)
                #                 n_arr = np.reshape(n_arr, num_samples)

                #                 if num_samples > 0:
                #                     print(f"Received {num_samples} samples")

                #             except IndexError as e:
                #                 print(e)
                #                 print(header)
                #                 print(message[1])
                #                 if len(message) > 2:
                #                     print(len(message[2]))
                #                 else:
                #                     print("only one frame???")

                #     elif header['type'] == 'event':
                #         print("event type is not yet supported")
                #         # if header['data_size'] > 0:
                #         #     event = Event(header['content'],
                #         #                             message[2])
                #         # else:
                #         #     event = Event(header['content'])

                #         # print(event)

                #     elif header['type'] == 'spike':
                #         print("spike type is not yet supported")
                #         # spike = Spike(header['spike'],
                #         #                             message[2])
                #         # print(spike)
                #     else:
                #         raise ValueError("message type unknown")
                # else:
                #     print("No data in message, breaking")

            elif self.heartbeat_socket in socks and self.socket_waits_reply:
                message = self.heartbeat_socket.recv()
                self.logger.debug(f'Heartbeat reply: {message}')
                if self.socket_waits_reply:
                    self.socket_waits_reply = False
                else:
                    print("Received reply before sending a message?")
