# Synapse Oephys Driver

Synapse connector for the [open-ephys GUI](https://open-ephys.org/gui).

**Run Server**
```
pip install -r requirements.txt
pip install -e .
python -m synapse_oephys --iface-ip 127.0.0.1
```

**Run Client**
```
python synapse_oephys/stream_out.py
```
