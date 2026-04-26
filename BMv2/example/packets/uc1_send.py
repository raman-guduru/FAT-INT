#!/usr/bin/env python3
import sys
import time
import random
import argparse
import threading
import json
import numpy as np
import socket
from scapy.all import get_if_list, get_if_hwaddr, Ether, IP, TCP, Raw

# --- NETWORK PARAMETERS ---
LINK_BW_BPS = 5_000_000  
BASELINE_BW_BPS = 10_000_000_000  
MTU_PAYLOAD = 1446
SERIALIZATION_DELAY = (1500 * 8) / LINK_BW_BPS

BW_SCALING_FACTOR = BASELINE_BW_BPS / LINK_BW_BPS 

link_lock = threading.Lock()
next_available_time = 0.0

log_file = None
log_lock = threading.Lock()

IP_TO_MAC = {
    "10.0.7.1": "00:00:0a:00:07:01", "10.0.7.2": "00:00:0a:00:07:02",
    "10.0.8.3": "00:00:0a:00:08:03", "10.0.8.4": "00:00:0a:00:08:04",
    "10.0.9.5": "00:00:0a:00:09:05", "10.0.9.6": "00:00:0a:00:09:06",
    "10.0.10.7": "00:00:0a:00:0a:07", "10.0.10.8": "00:00:0a:00:0a:08",
}

HOST_IP_MAP = {
    "h1": "10.0.7.1", "h2": "10.0.7.2",
    "h3": "10.0.8.3", "h4": "10.0.8.4",
    "h5": "10.0.9.5", "h6": "10.0.9.6",
    "h7": "10.0.10.7", "h8": "10.0.10.8",
}

RECEIVER_POOL = ["10.0.9.5", "10.0.9.6", "10.0.10.7", "10.0.10.8"]

def get_if():
    for i in get_if_list():
        if "eth0" in i:
            return i
    sys.exit("No eth0 found")

def get_args():
    p = argparse.ArgumentParser()
    p.add_argument('--sender', required=True)
    p.add_argument('--size_csv', required=True)
    p.add_argument('--arrival_csv', required=True)
    p.add_argument('--load', type=float, default=1.0)
    # Changed from --num_flows to --duration
    p.add_argument('--duration', type=float, default=60.0, help="Duration to run in seconds")
    return p.parse_args()

def load_cdf(path):
    data = np.loadtxt(path, delimiter=',')
    return data[:, 0], data[:, 1]

def sample_cdf(x, y):
    return np.interp(random.random(), y, x)

def log_packet(ts, flow_id, pkt_len):
    record = {"timestamp": ts, "flow_id": flow_id, "pkt_len": pkt_len}
    with log_lock:
        log_file.write(json.dumps(record) + "\n")

def send_flow(fid, iface, src_ip, dst_ip, size_bytes):
    global next_available_time
    
    sport = random.randint(10000, 60000)
    dport = random.randint(20000, 65000)
    flow_id = f"{src_ip}:{sport}->{dst_ip}:{dport}"
    
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    sock.bind((iface, 0))
    
    base_pkt = Ether(
        src=get_if_hwaddr(iface),
        dst=IP_TO_MAC[dst_ip]
    ) / IP(
        src=src_ip,
        dst=dst_ip,
        tos=0x03
    ) / TCP(
        sport=sport,
        dport=dport,
        flags="PA"
    )
    
    bytes_left = size_bytes

    while bytes_left > 0:
        p_size = min(bytes_left, MTU_PAYLOAD)
        raw_pkt_bytes = bytes(base_pkt / Raw(load=b"X" * p_size))
        pkt_len = len(raw_pkt_bytes)

        with link_lock:
            now = time.time()
            send_time = max(now, next_available_time)
            next_available_time = send_time + SERIALIZATION_DELAY
            
        wait = send_time - time.time()
        if wait > 0:
            time.sleep(wait)

        log_packet(send_time, flow_id, pkt_len)
        sock.send(raw_pkt_bytes)
        bytes_left -= p_size
        
    sock.close()

def main():
    global log_file
    args = get_args()
    iface = get_if()
    src_ip = HOST_IP_MAP[args.sender]
    
    random.seed(args.sender)

    size_x, size_y = load_cdf(args.size_csv)
    arr_x, arr_y = load_cdf(args.arrival_csv)

    log_file = open(f"sender_{args.sender}.log", "w", buffering=1)
    threads = []

    print(f"Starting traffic generation for {args.sender}...")
    print(f"Target Link Speed: {LINK_BW_BPS / 1e6} Mbps | Load: {args.load * 100}%")
    print(f"Running for {args.duration} seconds...")

    # Track start time and flow count
    start_simulation = time.time()
    flow_idx = 0

    try:
        while (time.time() - start_simulation) < args.duration:
            dst_ip = random.choice(RECEIVER_POOL)
            size_bytes = int(sample_cdf(size_x, size_y) * 1024)
            
            base_gap_seconds = sample_cdf(arr_x, arr_y) / 1e6
            gap = (base_gap_seconds * BW_SCALING_FACTOR) / args.load

            # Sleep for the inter-arrival gap
            time.sleep(gap)

            # Check again after sleep to ensure we don't start a flow past the duration
            if (time.time() - start_simulation) >= args.duration:
                break

            t = threading.Thread(
                target=send_flow,
                args=(flow_idx, iface, src_ip, dst_ip, size_bytes)
            )
            t.start()
            threads.append(t)
            flow_idx += 1
            
    except KeyboardInterrupt:
        print("\nStopping simulation early...")

    print(f"Duration reached. Waiting for {len(threads)} active flows to complete...")
    for t in threads:
        t.join()

    log_file.close()
    print(f"Done. Total flows sent: {flow_idx}")

if __name__ == "__main__":
    main()