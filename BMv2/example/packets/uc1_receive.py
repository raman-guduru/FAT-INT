#!/usr/bin/env python
import sys
import io
import os
import time
import argparse
import json
import threading
from scapy.all import sniff, IP, TCP, bind_layers

# ... [KEEP ALL THE CLASS AND PARSING FUNCTIONS EXACTLY THE SAME AS MY PREVIOUS MESSAGE] ...
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

def parse_fatint_header(pkt):
    int_metadata = pkt[TCP].load[:]
    return FatIntHeader.from_bytes(int_metadata)

def parse_metadata_q(pkt, queue_space, timestamp):
    queue_count = int(queue_space)
    queue_meta_len = 5
    global queue_byte
    queue_byte = queue_meta_len * queue_count    
    int_metadata = pkt[TCP].load[4:]
    
    for i in range(queue_count):
        metadata_source = int_metadata[i * queue_meta_len:(i+1)*queue_meta_len]
        meta = QueueMetadata.from_bytes(metadata_source)
        print(json.dumps({'timestamp': timestamp, 'switch_id': meta.switch_id, 'queue_occ': meta.q_occupancy}))

def parse_metadata_hop(pkt, hop_space, timestamp):
    hop_count = int(hop_space)
    hop_meta_len = 5
    global hop_byte, queue_byte
    hop_byte = hop_meta_len * hop_count
    int_metadata = pkt[TCP].load[queue_byte+4:]    
    
    for i in range(hop_count):
        metadata_source = int_metadata[i * hop_meta_len:(i+1)*hop_meta_len]
        meta = HopMetadata.from_bytes(metadata_source)
        print(json.dumps({'timestamp': timestamp, 'switch_id': meta.switch_id, 'hop_lat': meta.hop_latency}))

def parse_metadata_egress(pkt, egress_space, timestamp):
    egress_count = int(egress_space)
    egress_meta_len = 5
    global hop_byte, queue_byte
    int_metadata = pkt[TCP].load[(hop_byte+queue_byte+4):]
    
    for i in range(egress_count):
        metadata_source = int_metadata[i * egress_meta_len:(i+1)*egress_meta_len]
        meta = EgressMetadata.from_bytes(metadata_source)
        print(json.dumps({'timestamp': timestamp, 'switch_id': meta.switch_id, 'egress_ts': meta.egress_tstamp}))

def parsing_recv_packets(pkt):
    try:
        if IP in pkt and pkt[IP].tos != 0x3 and TCP in pkt and pkt[TCP].load:
            FatIntHdr = parse_fatint_header(pkt)
            timestamp = float(pkt.time)
            if FatIntHdr.case == 0 or FatIntHdr.case == 1:
                parse_metadata_q(pkt, FatIntHdr.queue_space, timestamp)
                parse_metadata_hop(pkt, FatIntHdr.hop_space, timestamp)
                parse_metadata_egress(pkt, FatIntHdr.egress_space, timestamp)
    except Exception as e:
        pass

def handle_pkt(pkt):
    global recv_pkts
    recv_pkts.append(pkt)

def receive_packet():
    global iface
    bind_layers(IP, TCP)
    sniff(iface=iface, filter="tcp", prn=lambda x: handle_pkt(x))

# --- UPDATED ARGUMENT AND MAIN LOGIC ---
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', help='Abs file path', type=str, required=True)
    parser.add_argument('--receiver', help='Name of the receiving host', type=str, required=True)
    return parser.parse_args()

def main():
    global iface, recv_pkts
    recv_pkts = []
    args = get_args()

    ifaces = [i for i in os.listdir('/sys/class/net/') if 'eth' in i]
    iface = ifaces[0]

    # Use the passed argument for the filename
    file_name = f"{args.file_path}/FAT_INT/BMv2/example/packets/baseline_{args.receiver}.txt"
    sys.stdout = open(file_name, 'w')

    receive_thread = threading.Thread(target=receive_packet, args=())
    receive_thread.daemon = True
    receive_thread.start()

    init_time = time.time()
    # Listens for 60 seconds before closing
    while (time.time() - init_time) < 60:
        time.sleep(1)

    for pkt in recv_pkts:
        parsing_recv_packets(pkt)
    
    sys.exit(0)
    
if __name__ == '__main__':   
    main()