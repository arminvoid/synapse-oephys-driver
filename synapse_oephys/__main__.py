import asyncio
from coolname import generate_slug
from synapse.api.node_pb2 import NodeType
from synapse.server.entrypoint import main, ENTRY_DEFAULTS
from synapse.server.nodes import SERVER_NODE_OBJECT_MAP
from synapse_oephys.broadband_source import BroadbandSource
from synapse_oephys.zmq_client import ZMQClient

defaults = ENTRY_DEFAULTS.copy()
defaults["device_serial"] = "oephys-connector"
defaults["server_name"] = "oephys-connector-" + generate_slug(2)

nodes = SERVER_NODE_OBJECT_MAP.copy()
nodes[NodeType.kBroadbandSource] = BroadbandSource

def run():
    main(nodes, peripherals=[], defaults=defaults)

async def test_zmq_client():
    zmq_client = ZMQClient()
    async for msg in zmq_client.receive_data():
        print("received:", msg)

if __name__ == "__main__":
    run()
    # asyncio.run(test_zmq_client())
