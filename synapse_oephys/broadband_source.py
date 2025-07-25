import asyncio
import logging
import zmq, json, numpy as np
from dataclasses import dataclass

from synapse.server.nodes import BaseNode
from synapse.api.node_pb2 import NodeType
from synapse.api.nodes.broadband_source_pb2 import BroadbandSourceConfig
from synapse.server.status import Status
from synapse.api.datatype_pb2 import BroadbandFrame
from synapse.api.tap_pb2 import TapConnection, TapType
from synapse_oephys.zmq_client import ZMQClient

NUM_SAMPLES = 928
NUM_CHANNELS = 16

@dataclass
class OpenEphysMessage:
    message_num: int
    channel_num: int
    sample_num: int
    timestamp: int
    sample_rate: int
    payload: np.ndarray
class BroadbandSource(BaseNode):
    def __init__(self, id):
        print(f"BroadbandSource __init__")
        super().__init__(id, NodeType.kBroadbandSource)
        self.__config: BroadbandSourceConfig = None
        self.zmq_context = None
        self.zmq_socket = None
        self.seq_number = 0
        self.iface_ip = None
        self.zmq_client = ZMQClient()
        self.last_channel_num = None
        self.samples = np.zeros((NUM_CHANNELS, NUM_SAMPLES), dtype=np.float32)

    def config(self):
        c = super().config()
        if self.__config:
            c.broadband_source.CopyFrom(self.__config)
        return c

    def configure(self, config: BroadbandSourceConfig) -> Status:
        self.__config = config
        return Status()

    async def run(self):
        if not self.zmq_context:
            self.zmq_context = zmq.Context()
            self.zmq_socket = self.zmq_context.socket(zmq.PUB)
            self.port = self.zmq_socket.bind_to_random_port(f"tcp://{self.iface_ip}")

        while self.running: # to resume in case of exception
            try:
                async for msg in self.zmq_client.receive_data():
                    res = self.parse_msg(msg)
                    if not res:
                        continue
                    # print(f"res: {res}")
                    expected_channel = 0 if self.last_channel_num is None else self.last_channel_num + 1
                    if res.channel_num != expected_channel:
                        raise ValueError(f"channel_num {res.channel_num} does not match expected {expected_channel}")
                    self.last_channel_num = expected_channel
                    self.samples[res.channel_num, :] = res.payload

                    # if we accumulated all samples, send the frames over tap
                    # print type of res.channel_num
                    if res.channel_num == NUM_CHANNELS - 1:
                        # iterate samples to construct payload indexed by channel_num
                        for i in range(NUM_SAMPLES):
                            # res.timestamp is exact same for all NUM_CHANNEL msgs
                            base_ts_ns = int(res.timestamp * 1e6) # milliseconds to nanoseconds

                            # ideally dt = 1e9 / res.sample_rate, but since msgs from open-ephys have ms resolution the next header loses upto 1ms due to truncation
                            # so we adjust. at sample_rate, NUM_SAMPLES take
                            required_time_ms = int(NUM_SAMPLES * 1e3 / res.sample_rate)
                            dt_ns = int(required_time_ms * 1e6 / NUM_SAMPLES)

                            frame = BroadbandFrame(
                                timestamp_ns=base_ts_ns + i * dt_ns,
                                sequence_number=self.seq_number,
                                frame_data=self.samples[:, i].astype(np.int32).tolist(),
                                sample_rate_hz=res.sample_rate,
                            )
                            # print(f"frame_data: {frame.frame_data}")
                            print(f"sending frame: {frame}")
                            self.zmq_socket.send(frame.SerializeToString())
                            self.seq_number += 1
                        self.samples = np.zeros((NUM_CHANNELS, NUM_SAMPLES), dtype=np.float32)
                        self.last_channel_num = None
            except Exception as e:
                # self.logger.warn(f"failed to read data: {e}")
                print(f"failed to read data: {e}")
                await asyncio.sleep(0.01)  # Sleep on error to prevent rapid retries

    def parse_msg(self, message: dict) -> OpenEphysMessage:
        if not message:
            self.logger.warn(f"no message received")
            return None

        if len(message) < 2:
            self.logger.warn(f"no frames for message: {message[0]}")
            return None

        # is len(message) == 2 possible?

        try:
            envelope, header_json, payload = message
            header = json.loads(header_json)
            # print(f'header: {header}, payload: {payload}')

            if header['type'] == 'event' or header['type'] == 'spike':
                print("event or spike type is not yet supported")
                return None
            if header['type'] != 'data':
                raise ValueError('message type not yet supported')

            message_num, content, timestamp = map(header.get, ('message_num', 'content', 'timestamp'))
            channel_num, num_samples, sample_num, sample_rate = map(content.get, ('channel_num', 'num_samples', 'sample_num', 'sample_rate'))
            if num_samples != NUM_SAMPLES:
                # for this prototype, we only work with NUM_SAMPLES samples per channel
                raise ValueError(f'num_samples {num_samples} does not match expected {NUM_SAMPLES}')

            return OpenEphysMessage(
                message_num=message_num,
                timestamp=timestamp,
                channel_num=channel_num,
                sample_num=sample_num,
                sample_rate=int(sample_rate),
                payload=np.frombuffer(payload, dtype=np.float32)
            )
        except Exception as e:
            print(f"failed to parse message: {e}")
            return None

    def stop(self):
        """Clean up ZMQ resources."""
        if self.zmq_socket:
            self.zmq_socket.close()
            self.zmq_socket = None

        if self.zmq_context:
            self.zmq_context.destroy()
            self.zmq_context = None

        return super().stop()

    def configure_iface_ip(self, iface_ip):
        print(f"configuring iface_ip: {iface_ip}")
        self.iface_ip = iface_ip

    def tap_connections(self):
        return [
            TapConnection(
                name="broadband_source_sim",
                endpoint=f"tcp://{self.iface_ip}:{self.port}",
                message_type="synapse.BroadbandFrame",
                tap_type=TapType.TAP_TYPE_PRODUCER,
            )
        ]
