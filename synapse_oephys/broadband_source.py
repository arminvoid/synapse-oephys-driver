import asyncio
import zmq, json, numpy as np
from synapse.server.nodes import BaseNode
from synapse.api.node_pb2 import NodeType
from synapse.api.nodes.broadband_source_pb2 import BroadbandSourceConfig
from synapse.server.status import Status, StatusCode

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
                    self.logger.info("received: %d bytes", len(msg))
            except Exception as e:
                self.logger.warn(f"failed to read data: {e}")
                await asyncio.sleep(1)  # Sleep on error to prevent rapid retries

