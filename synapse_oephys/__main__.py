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
    bs = BroadbandSource(69)
    async for msg in bs.zmq_client.receive_data():
        res = bs.parse_msg(msg)
        print(f"channel: {res.samples[0][0]}, num_samples", len(res.samples[0][1]))

if __name__ == "__main__":
    run()
    # try:
    #     asyncio.run(test_zmq_client())
    # except KeyboardInterrupt:
    #     print("Shutting down...")
