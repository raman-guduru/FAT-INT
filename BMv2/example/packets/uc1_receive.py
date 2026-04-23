#!/usr/bin/env python3
import sys
import io
import os
import time
import argparse
import json
from scapy.all import sniff, IP, TCP

# ============================================================
# FAT-INT HEADER
# ============================================================

class FatIntHeader():
    def __init__(self):
        self.case = None
        self.queue_space = None
        self.hop_space = None
        self.egress_space = None

    @staticmethod
    def from_bytes(data):
        hdr = FatIntHeader()
        h = io.BytesIO(data)
        hdr.case = int.from_bytes(h.read(1), 'big')
        hdr.queue_space = int.from_bytes(h.read(1), 'big')
        hdr.hop_space = int.from_bytes(h.read(1), 'big')
        hdr.egress_space = int.from_bytes(h.read(1), 'big')
        return hdr


# ============================================================
# METADATA PARSERS
# ============================================================

def parse_queue_metadata(raw, count):
    entries = []
    offset = 0
    size = 5

    for _ in range(count):
        chunk = raw[offset:offset+size]
        if len(chunk) < size:
            break

        d = io.BytesIO(chunk)
        q_id = int.from_bytes(d.read(1), 'big')
        q_occ = int.from_bytes(d.read(3), 'big')
        switch_id = int.from_bytes(d.read(1), 'big')

        entries.append({
            "switch_id": switch_id,
            "q_id": q_id,
            "queue_occ": q_occ
        })

        offset += size

    return entries, offset


def parse_hop_metadata(raw, count):
    entries = []
    offset = 0
    size = 5

    for _ in range(count):
        chunk = raw[offset:offset+size]
        if len(chunk) < size:
            break

        d = io.BytesIO(chunk)
        hop_lat = int.from_bytes(d.read(4), 'big')
        switch_id = int.from_bytes(d.read(1), 'big')

        entries.append({
            "switch_id": switch_id,
            "hop_lat": hop_lat
        })

        offset += size

    return entries, offset


def parse_egress_metadata(raw, count):
    entries = []
    offset = 0
    size = 5

    for _ in range(count):
        chunk = raw[offset:offset+size]
        if len(chunk) < size:
            break

        d = io.BytesIO(chunk)
        egress_ts = int.from_bytes(d.read(4), 'big')
        switch_id = int.from_bytes(d.read(1), 'big')

        entries.append({
            "switch_id": switch_id,
            "egress_ts": egress_ts
        })

        offset += size

    return entries


# ============================================================
# PACKET PROCESSING
# ============================================================

def process_packet(pkt):
    try:
        if IP not in pkt or TCP not in pkt:
            return

        # Ignore ACK-only packets
        if len(pkt[TCP].payload) == 0:
            return

        timestamp = float(pkt.time)

        src_ip = pkt[IP].src
        dst_ip = pkt[IP].dst
        sport = pkt[TCP].sport
        dport = pkt[TCP].dport

        flow_id = f"{src_ip}:{sport}->{dst_ip}:{dport}"

        record = {
            'timestamp': timestamp,
            'flow_id': flow_id,
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'pkt_len': len(pkt),
            'int_case': None,
            'queue_metadata': [],
            'hop_metadata': [],
            'egress_metadata': []
        }

        raw = bytes(pkt[TCP].payload)

        # Need at least header
        if len(raw) < 4:
            print(json.dumps(record), flush=True)
            return

        # ---------------- INT HEADER ----------------
        hdr = FatIntHeader.from_bytes(raw[:4])

        # sanity check (prevents parsing garbage)
        if hdr.case not in [0, 1]:
            print(json.dumps(record), flush=True)
            return

        record['int_case'] = hdr.case

        offset = 4

        # ---------------- QUEUE ----------------
        q_raw = raw[offset:]
        q_entries, used_q = parse_queue_metadata(q_raw, hdr.queue_space)
        record['queue_metadata'] = q_entries
        offset += used_q

        # ---------------- HOP ----------------
        h_raw = raw[offset:]
        h_entries, used_h = parse_hop_metadata(h_raw, hdr.hop_space)
        record['hop_metadata'] = h_entries
        offset += used_h

        # ---------------- EGRESS ----------------
        e_raw = raw[offset:]
        e_entries = parse_egress_metadata(e_raw, hdr.egress_space)
        record['egress_metadata'] = e_entries

        print(json.dumps(record), flush=True)

    except Exception:
        pass


# ============================================================
# MAIN
# ============================================================

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', required=True)
    parser.add_argument('--receiver', required=True)
    parser.add_argument('--duration', type=int, default=240)
    return parser.parse_args()


def main():
    args = get_args()

    iface = [i for i in os.listdir('/sys/class/net/') if 'eth' in i][0]

    log_dir = os.path.join(args.file_path, "FAT_INT", "BMv2", "example", "packets")
    os.makedirs(log_dir, exist_ok=True)

    file_name = os.path.join(log_dir, f"result_{args.receiver}.txt")

    # 🔥 line-buffered → real-time file updates
    sys.stdout = open(file_name, 'w', buffering=1)

    print(json.dumps({
        "event": "receiver_started",
        "receiver": args.receiver,
        "iface": iface,
        "duration": args.duration
    }), flush=True)

    sniff(
        iface=iface,
        filter="tcp",
        prn=process_packet,
        store=False,
        timeout=args.duration
    )

    print(json.dumps({
        "event": "receiver_stopped",
        "receiver": args.receiver
    }), flush=True)


if __name__ == '__main__':
    main()