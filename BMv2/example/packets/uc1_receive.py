#!/usr/bin/env python3
import sys
import io
import os
import time
import argparse
import json
import threading
from scapy.all import sniff, IP, TCP, bind_layers


# =====================================================================================
# FAT-INT / Classical INT Header Parsers
# =====================================================================================

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
        hdr.case = int.from_bytes(h.read(1), byteorder='big')
        hdr.queue_space = int.from_bytes(h.read(1), byteorder='big')
        hdr.hop_space = int.from_bytes(h.read(1), byteorder='big')
        hdr.egress_space = int.from_bytes(h.read(1), byteorder='big')
        return hdr


class HopMetadata():
    def __init__(self):
        self.switch_id = None
        self.hop_latency = None

    @staticmethod
    def from_bytes(data):
        hop = HopMetadata()
        d = io.BytesIO(data)
        hop.hop_latency = int.from_bytes(d.read(4), byteorder='big')
        hop.switch_id = int.from_bytes(d.read(1), byteorder='big')
        return hop


class QueueMetadata():
    def __init__(self):
        self.switch_id = None
        self.q_id = None
        self.q_occupancy = None

    @staticmethod
    def from_bytes(data):
        queue = QueueMetadata()
        d = io.BytesIO(data)
        queue.q_id = int.from_bytes(d.read(1), byteorder='big')
        queue.q_occupancy = int.from_bytes(d.read(3), byteorder='big')
        queue.switch_id = int.from_bytes(d.read(1), byteorder='big')
        return queue


class EgressMetadata():
    def __init__(self):
        self.switch_id = None
        self.egress_tstamp = None

    @staticmethod
    def from_bytes(data):
        egress = EgressMetadata()
        d = io.BytesIO(data)
        egress.egress_tstamp = int.from_bytes(d.read(4), byteorder='big')
        egress.switch_id = int.from_bytes(d.read(1), byteorder='big')
        return egress


# =====================================================================================
# Parsing Helpers
# =====================================================================================

def parse_fatint_header(pkt):
    int_metadata = bytes(pkt[TCP].payload)
    return FatIntHeader.from_bytes(int_metadata[:4])


def parse_metadata_q(pkt, queue_space):
    queue_count = int(queue_space)
    queue_meta_len = 5
    int_metadata = bytes(pkt[TCP].payload)[4:]

    queue_entries = []
    for i in range(queue_count):
        metadata_source = int_metadata[i * queue_meta_len:(i + 1) * queue_meta_len]
        if len(metadata_source) < queue_meta_len:
            continue
        meta = QueueMetadata.from_bytes(metadata_source)
        queue_entries.append({
            'switch_id': meta.switch_id,
            'q_id': meta.q_id,
            'queue_occ': meta.q_occupancy
        })

    return queue_entries, queue_count * queue_meta_len


def parse_metadata_hop(pkt, hop_space, queue_bytes):
    hop_count = int(hop_space)
    hop_meta_len = 5
    int_metadata = bytes(pkt[TCP].payload)[4 + queue_bytes:]

    hop_entries = []
    for i in range(hop_count):
        metadata_source = int_metadata[i * hop_meta_len:(i + 1) * hop_meta_len]
        if len(metadata_source) < hop_meta_len:
            continue
        meta = HopMetadata.from_bytes(metadata_source)
        hop_entries.append({
            'switch_id': meta.switch_id,
            'hop_lat': meta.hop_latency
        })

    return hop_entries, hop_count * hop_meta_len


def parse_metadata_egress(pkt, egress_space, queue_bytes, hop_bytes):
    egress_count = int(egress_space)
    egress_meta_len = 5
    int_metadata = bytes(pkt[TCP].payload)[4 + queue_bytes + hop_bytes:]

    egress_entries = []
    for i in range(egress_count):
        metadata_source = int_metadata[i * egress_meta_len:(i + 1) * egress_meta_len]
        if len(metadata_source) < egress_meta_len:
            continue
        meta = EgressMetadata.from_bytes(metadata_source)
        egress_entries.append({
            'switch_id': meta.switch_id,
            'egress_ts': meta.egress_tstamp
        })

    return egress_entries


# =====================================================================================
# Packet Parser
# =====================================================================================

def parsing_recv_packets(pkt):
    try:
        # We still strictly need IP and TCP layers to log basic flow info
        if IP not in pkt or TCP not in pkt:
            return

        # FIX: Extract the true capture timestamp from Scapy rather than the parsing time
        timestamp = float(pkt.time)

        src_ip = pkt[IP].src
        dst_ip = pkt[IP].dst
        sport = pkt[TCP].sport
        dport = pkt[TCP].dport
        ip_id = pkt[IP].id
        ttl = pkt[IP].ttl
        pkt_len = len(pkt)

        flow_id = f"{src_ip}:{sport}->{dst_ip}:{dport}"

        # ---------------------------------------------------------------------
        # Set Default values for Non-INT packets
        # ---------------------------------------------------------------------
        int_case = None
        queue_space = 0
        hop_space = 0
        egress_space = 0
        queue_entries = []
        hop_entries = []
        egress_entries = []

        # ---------------------------------------------------------------------
        # Attempt to parse INT Metadata (Only if payload exists and TOS != 0x3)
        # ---------------------------------------------------------------------
        if pkt[TCP].payload and pkt[IP].tos != 0x3:
            try:
                fat_hdr = parse_fatint_header(pkt)

                if fat_hdr.case in [0, 1]:
                    q_ents, q_bytes = parse_metadata_q(pkt, fat_hdr.queue_space)
                    h_ents, h_bytes = parse_metadata_hop(pkt, fat_hdr.hop_space, q_bytes)
                    e_ents = parse_metadata_egress(pkt, fat_hdr.egress_space, q_bytes, h_bytes)
                    
                    int_case = fat_hdr.case
                    queue_space = fat_hdr.queue_space
                    hop_space = fat_hdr.hop_space
                    egress_space = fat_hdr.egress_space
                    queue_entries = q_ents
                    hop_entries = h_ents
                    egress_entries = e_ents
            except Exception:
                pass

        # ---------------------------------------------------------------------
        # Log the Packet
        # ---------------------------------------------------------------------
        record = {
            'timestamp': timestamp,
            'flow_id': flow_id,
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'sport': sport,
            'dport': dport,
            'ip_id': ip_id,
            'ttl': ttl,
            'pkt_len': pkt_len,
            'int_case': int_case,
            'queue_space': queue_space,
            'hop_space': hop_space,
            'egress_space': egress_space,
            'queue_metadata': queue_entries,
            'hop_metadata': hop_entries,
            'egress_metadata': egress_entries
        }

        print(json.dumps(record))

    except Exception as e:
        pass


# =====================================================================================
# Packet Capture
# =====================================================================================

def handle_pkt(pkt):
    global recv_pkts
    recv_pkts.append(pkt)


def receive_packet():
    global iface
    bind_layers(IP, TCP)
    sniff(iface=iface, filter="tcp", prn=lambda x: handle_pkt(x), store=False)


# =====================================================================================
# Args
# =====================================================================================

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', help='Absolute project path', type=str, required=True)
    parser.add_argument('--receiver', help='Name of the receiving host', type=str, required=True)
    parser.add_argument('--duration', help='Sniff duration in seconds', type=int, default=240)
    return parser.parse_args()


# =====================================================================================
# Main
# =====================================================================================

def main():
    global iface, recv_pkts
    recv_pkts = []
    args = get_args()

    # Pick Mininet interface
    ifaces = [i for i in os.listdir('/sys/class/net/') if 'eth' in i]
    if not ifaces:
        print("No ethernet interface found")
        sys.exit(1)

    iface = ifaces[0]

    # Output directory
    log_dir = os.path.join(args.file_path, "FAT_INT", "BMv2", "example", "packets")
    os.makedirs(log_dir, exist_ok=True)

    file_name = os.path.join(log_dir, f"result_temp_{args.receiver}.txt")
    sys.stdout = open(file_name, 'w', buffering=1)

    print(json.dumps({
        "event": "receiver_started",
        "receiver": args.receiver,
        "iface": iface,
        "duration": args.duration
    }))

    receive_thread = threading.Thread(target=receive_packet, args=())
    receive_thread.daemon = True
    receive_thread.start()

    init_time = time.time()

    while (time.time() - init_time) < args.duration:
        time.sleep(1)

    print(json.dumps({
        "event": "receiver_stopped",
        "receiver": args.receiver,
        "captured_packets": len(recv_pkts)
    }))

    # Now when we parse, Scapy's saved `pkt.time` will be accurate
    for pkt in recv_pkts:
        parsing_recv_packets(pkt)

    sys.exit(0)


if __name__ == '__main__':
    main()