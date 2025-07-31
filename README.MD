# Synapse Oephys Driver

The [Open Ephys GUI](https://open-ephys.org/gui) is designed to provide a fast and flexible interface for acquiring and visualizing data from extracellular electrodes. This synapse connector is a wrapper over the data received from the GUI and effectively makes the following devices compatible with rest of the synapse ecosystem:

- Open Ephys Acquisition Board
- Open Ephys ONIX System
- IMEC Neuropixels PXIe Basestations
- IMEC Neuropixels OneBox
- Intan Recording Controller
- Intan RHD USB Interface Board
- National Instruments DAQs

[Demo Video (1 min)](https://drive.google.com/file/d/1PN1MTfGKxDtWwhRWlow_KYOtEbvzWjCf/view?usp=drive_link)

### Setup project
```
pip install -r requirements.txt
pip install -e .
```

### Run Server
```
python -m synapse_oephys --iface-ip 127.0.0.1
```

### Run Client
**CLI**
```
synapsectl -u 127.0.0.1 configure device_config.json
synapsectl -u 127.0.0.1 info
synapsectl -u 127.0.0.1 start
synapsectl -u 127.0.0.1 taps list
synapsectl -u 127.0.0.1 read device_config.json --tap-name open_ephys_connector
synapsectl -u 127.0.0.1 read device_config.json --tap-name open_ephys_connector --output <output_dir>
```

**Script**
```
python synapse_oephys/stream_out.py
```
