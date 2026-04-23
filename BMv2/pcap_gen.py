import numpy as np
import random
from scapy.all import Ether, IP, TCP, Raw, wrpcap

random.seed(42)
np.random.seed(42)

# --- CONFIG ---
NUM_FLOWS = 750
TARGET_LOAD = 0.40
LINK_BW_BPS = 10_000_000  # 10 Mbps
MTU_PAYLOAD = 1446

# Correct serialization delay
SERIALIZATION_DELAY = (1500 * 8) / LINK_BW_BPS  # = 0.0012 sec

SIZE_CSV = "/home/p4/FAT_INT/BMv2/flow_size.csv"
ARRIVAL_CSV = "/home/p4/FAT_INT/BMv2/syn_inter.csv"

IP_TO_MAC = {
    "10.0.7.1": "00:00:0a:00:07:01", "10.0.7.2": "00:00:0a:00:07:02",
    "10.0.8.3": "00:00:0a:00:08:03", "10.0.8.4": "00:00:0a:00:08:04",
    "10.0.9.5": "00:00:0a:00:09:05", "10.0.9.6": "00:00:0a:00:09:06",
    "10.0.10.7": "00:00:0a:00:0a:07", "10.0.10.8": "00:00:0a:00:0a:08",
}

def load_cdf(path):
    data = np.loadtxt(path, delimiter=',')
    return data[:, 0], data[:, 1]

def sample_log_cdf(x_vals, y_vals):
    prob = random.random()
    log_x = np.log10(np.clip(x_vals, 1e-9, None))
    interp_log_x = np.interp(prob, y_vals, log_x)
    return 10 ** interp_log_x

# Load distributions
size_x, size_y = load_cdf(SIZE_CSV)
arrival_x, arrival_y = load_cdf(ARRIVAL_CSV)

print("Sampling distributions...")

# Pre-sample
raw_flow_sizes = []
raw_gaps = []

for _ in range(NUM_FLOWS):
    raw_flow_sizes.append(int(sample_log_cdf(size_x, size_y) * 1024))
    raw_gaps.append(sample_log_cdf(arrival_x, arrival_y) / 1_000_000.0)

avg_flow_size = np.mean(raw_flow_sizes)
raw_avg_gap = np.mean(raw_gaps)

# Target throughput
target_Bps = (LINK_BW_BPS * TARGET_LOAD) / 8.0
target_flows_per_sec = target_Bps / avg_flow_size
target_avg_gap = 1.0 / target_flows_per_sec

GAP_SCALE = target_avg_gap / raw_avg_gap

print(f"Avg flow size: {avg_flow_size:.2f} bytes")
print(f"Target throughput: {target_Bps:.2f} Bps")
print(f"Gap scale: {GAP_SCALE:.4f}")

SENDERS = ["10.0.7.1", "10.0.7.2", "10.0.8.3", "10.0.8.4"]
RECEIVERS = ["10.0.9.5", "10.0.9.6", "10.0.10.7", "10.0.10.8"]

# --- Generate flows ---
flows = []
current_time = 0.0

for i in range(NUM_FLOWS):
    gap = raw_gaps[i] * GAP_SCALE
    current_time += gap

    size = raw_flow_sizes[i]
    pkts = max(1, int(np.ceil(size / MTU_PAYLOAD)))

    flows.append({
        'start': current_time,
        'bytes': size,
        'pkts': pkts,
        'src': random.choice(SENDERS),
        'dst': random.choice(RECEIVERS),
        'sport': random.randint(1024, 65535),
        'dport': random.randint(1024, 65535),
    })

# --- GLOBAL LINK SCHEDULER ---
print("Generating packets with global link constraint...")

events = []
for f in flows:
    events.append({
        'time': f['start'],
        'flow': f,
        'bytes_left': f['bytes']
    })

# sort by flow start time
events.sort(key=lambda x: x['time'])

global_time = 0.0
packets = []

for ev in events:
    f = ev['flow']
    temp_time = max(ev['time'], global_time)
    bytes_left = ev['bytes_left']

    while bytes_left > 0:
        p_size = min(bytes_left, MTU_PAYLOAD)

        pkt = Ether(src=IP_TO_MAC[f['src']], dst=IP_TO_MAC[f['dst']]) / \
              IP(src=f['src'], dst=f['dst'], tos=0x03) / \
              TCP(sport=f['sport'], dport=f['dport'], flags="PA") / \
              Raw(load=b"X" * p_size)

        pkt.time = temp_time
        packets.append(pkt)

        bytes_left -= p_size

        # enforce single link
        temp_time += SERIALIZATION_DELAY
        global_time = temp_time

# Final sort
packets.sort(key=lambda x: x.time)

print(f"Writing {len(packets)} packets...")
wrpcap("hadoop_master_fixed.pcap", packets)

print("Done.")