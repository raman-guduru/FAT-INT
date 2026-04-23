#!/usr/bin/env python3
import sys
import os
import time
import random
import argparse
import threading
import json
import numpy as np
from scapy.all import sendp, get_if_list, get_if_hwaddr, Ether, IP, TCP, Raw

LINK_BW_BPS = 10_000_000
MTU_PAYLOAD = 1446
SERIALIZATION_DELAY = (1500 * 8) / LINK_BW_BPS

random.seed(42)

link_lock = threading.Lock()
next_available_time = 0.0

log_file = None
log_lock = threading.Lock()

# ⚠️ FIX: real MAC mapping (CRITICAL)
IP_TO_MAC = {
    "10.0.7.1": "00:00:0a:00:07:01", "10.0.7.2": "00:00:0a:00:07:02",
    "10.0.8.3": "00:00:0a:00:08:03", "10.0.8.4": "00:00:0a:00:08:04",
    "10.0.9.5": "00:00:0a:00:09:05", "10.0.9.6": "00:00:0a:00:09:06",
    "10.0.10.7": "00:00:0a:00:0a:07", "10.0.10.8": "00:00:0a:00:0a:08",
}

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
    p.add_argument('--load', type=float, default=0.4)
    p.add_argument('--num_flows', type=int, default=100)
    return p.parse_args()

HOST_IP_MAP = {
    "h1": "10.0.7.1", "h2": "10.0.7.2",
    "h3": "10.0.8.3", "h4": "10.0.8.4",
    "h5": "10.0.9.5", "h6": "10.0.9.6",
    "h7": "10.0.10.7", "h8": "10.0.10.8",
}

RECEIVER_POOL = ["10.0.9.5", "10.0.9.6", "10.0.10.7", "10.0.10.8"]

def load_cdf(path):
    data = np.loadtxt(path, delimiter=',')
    return data[:, 0], data[:, 1]

def sample_cdf(x, y):
    return np.interp(random.random(), y, x)

def log_packet(ts, flow_id, pkt_len):
    record = {"timestamp": ts, "flow_id": flow_id, "pkt_len": pkt_len}
    with log_lock:
        log_file.write(json.dumps(record) + "\n")

def send_packet(pkt, iface, flow_id):
    global next_available_time

    with link_lock:
        now = time.time()
        send_time = max(now, next_available_time)

        wait = send_time - now
        if wait > 0:
            time.sleep(wait)

        log_packet(send_time, flow_id, len(pkt))

        sendp(pkt, iface=iface, verbose=False)

        next_available_time = send_time + SERIALIZATION_DELAY

def send_flow(fid, iface, src_ip, dst_ip, size_bytes):
    sport = random.randint(10000, 60000)
    dport = random.randint(20000, 65000)

    flow_id = f"{src_ip}:{sport}->{dst_ip}:{dport}"
    bytes_left = size_bytes

    while bytes_left > 0:
        p_size = min(bytes_left, MTU_PAYLOAD)

        pkt = Ether(
            src=get_if_hwaddr(iface),
            dst=IP_TO_MAC[dst_ip]   # ✅ FIXED
        ) / IP(
            src=src_ip,
            dst=dst_ip,
            tos=0x03
        ) / TCP(
            sport=sport,
            dport=dport,
            flags="PA"
        ) / Raw(load=b"X" * p_size)

        send_packet(pkt, iface, flow_id)

        bytes_left -= p_size

def main():
    global log_file

    args = get_args()
    iface = get_if()
    src_ip = HOST_IP_MAP[args.sender]

    size_x, size_y = load_cdf(args.size_csv)
    arr_x, arr_y = load_cdf(args.arrival_csv)

    log_file = open(f"sender_{args.sender}.log", "w", buffering=1)

    threads = []

    for i in range(args.num_flows):
        dst_ip = random.choice(RECEIVER_POOL)

        size_bytes = int(sample_cdf(size_x, size_y) * 1024)
        gap = (sample_cdf(arr_x, arr_y) / 1e6) / args.load

        time.sleep(gap)

        t = threading.Thread(
            target=send_flow,
            args=(i, iface, src_ip, dst_ip, size_bytes)
        )
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    log_file.close()

if __name__ == "__main__":
    main()