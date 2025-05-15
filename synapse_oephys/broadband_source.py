import asyncio
import logging
import zmq, json, numpy as np
from synapse.server.nodes import BaseNode
from synapse.api.node_pb2 import NodeType
from synapse.api.nodes.broadband_source_pb2 import BroadbandSourceConfig
from synapse.server.status import Status, StatusCode
from synapse.utils.ndtp_types import ElectricalBroadbandData
from synapse_oephys.zmq_client import ZMQClient

class BroadbandSource(BaseNode):
    def __init__(self, id):
        super().__init__(id, NodeType.kBroadbandSource)
        self.zmq_client = ZMQClient()

    def config(self):
        c = super().config()
        if self.__config:
            c.broadband_source.CopyFrom(self.__config)
        return c

    def configure(self, config: BroadbandSourceConfig) -> Status:
        self.__config = config
        return Status()

    async def run(self):
        while self.running: # to resume in case of exception
            try:
                async for msg in self.zmq_client.receive_data():
                    res = self.parse_msg(msg)
                    if res:
                        await self.emit_data(res)
            except Exception as e:
                self.logger.warn(f"failed to read data: {e}")
                await asyncio.sleep(1)  # Sleep on error to prevent rapid retries

    def parse_msg(self, message):
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
            if header['type'] == 'data':
                c = header['content']
                num_samples = c['num_samples']
                channel_num = c['channel_num']
                n_arr = np.reshape(np.frombuffer(payload, dtype=np.float32), num_samples)
                data = [[channel_num, n_arr]] # data is a list of [channel_id, np.array(samples, dtype=int32)] tuples
                return ElectricalBroadbandData(
                    sample_rate=c['sample_rate'],
                    t0=header['timestamp'] * 1e3, # ms to microseconds
                    samples=data,
                    bit_width=(header['data_size'] * 8) / c['num_samples'],
                    is_signed=True, # check this
                )
            elif header['type'] == 'event' or header['type'] == 'spike':
                print("event or spike type is not yet supported")
            else:
                raise ValueError("message type unknown")
        except Exception as e:
            self.logger.exception(f"failed to parse message: {e}")
            return None

