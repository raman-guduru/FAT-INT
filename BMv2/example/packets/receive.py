#!/usr/bin/env python
import sys
import io
import os
import time
import argparse

from scapy.all import sniff
from scapy.all import IP, TCP, bind_layers
import threading

################################################################################################
##########                      Parsing customized packet headers                      #########
################################################################################################

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

    def __str__(self):
        return str(vars(self))

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

    def __str__(self):
        return str(vars(self))

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

    def __str__(self):
        return str(vars(self))

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

    def __str__(self):
        return str(vars(self))
    
def parse_fatint_header(pkt):
    int_metadata = pkt[TCP].load[:]
    meta = FatIntHeader.from_bytes(int_metadata)
    # print(meta)
    return meta

def parse_metadata_hop(pkt, hop_space):
    global hop_byte, queue_byte, sw_id_hop
    hop_count = int(hop_space)
    hop_meta_len = 5
    hop_byte = hop_meta_len * hop_count
    hop_metadata = []
    int_metadata = pkt[TCP].load[queue_byte+4:]    
    for i in range(hop_count):
        metadata_source = int_metadata[i * hop_meta_len:(i+1)*hop_meta_len]
        meta = HopMetadata.from_bytes(metadata_source)
        sw_id_hop.append(meta.switch_id)
        hop_metadata.append(meta)
        # print(meta)
    return hop_metadata

def parse_metadata_q(pkt,queue_space):
    global hop_byte, queue_byte,sw_id_q
    queue_count = int(queue_space)
    queue_meta_len = 5
    queue_byte = queue_meta_len  * queue_count    
    queue_metadata = []
    int_metadata = pkt[TCP].load[4:]
    for i in range(queue_count):
        metadata_source = int_metadata[i * queue_meta_len:(i+1)*queue_meta_len]
        meta = QueueMetadata.from_bytes(metadata_source)
        sw_id_q.append(meta.switch_id)
        queue_metadata.append(meta)
        # print(meta)
    return queue_metadata

def parse_metadata_egress(pkt,egress_space):
    global hop_byte, queue_byte,sw_id_egress
    egress_count = int(egress_space)
    egress_meta_len = 5
    egress_metadata = []
    int_metadata = pkt[TCP].load[(hop_byte+queue_byte+4):]
    for i in range(egress_count):
        metadata_source = int_metadata[i * egress_meta_len:(i+1)*egress_meta_len]
        meta = EgressMetadata.from_bytes(metadata_source)
        sw_id_egress.append(meta.switch_id)
        egress_metadata.append(meta)
        # print(meta)
    return egress_metadata

def parsing_recv_packets(pkt):
    global count_case_1, count_case_2, count_normal
    try:
        if pkt[IP].tos == 0x3:
            print("Normal Packet")
            count_normal +=1
        else:
            FatIntHdr = parse_fatint_header(pkt)
            print(f"[queue, hop, egress] = [{FatIntHdr.queue_space}, {FatIntHdr.hop_space}, {FatIntHdr.egress_space}]")
            if FatIntHdr.case == 0:
                count_case_1 += 1
                parse_metadata_q(pkt,FatIntHdr.queue_space)
                parse_metadata_hop(pkt,FatIntHdr.hop_space)
                parse_metadata_egress(pkt,FatIntHdr.egress_space)
            elif FatIntHdr.case == 1:
                count_case_2 += 1
                parse_metadata_q(pkt,FatIntHdr.queue_space)
                parse_metadata_hop(pkt,FatIntHdr.hop_space)
                parse_metadata_egress(pkt,FatIntHdr.egress_space)
            
    except Exception as e:
        print(f"Error parsing packet: {e}")


#################################################################################################
##########                           Receiving packet headers                           #########
#################################################################################################

def handle_pkt(pkt):
    global recv_pkts
    bind_layers(IP,TCP)
    recv_pkts.append(pkt)

def receive_packet():
    global iface
    sniff(iface = iface, prn = lambda x: handle_pkt(x))

#################################################################################################
##########                                     main                                     #########
#################################################################################################

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', help='Abs file path', type=str, required=True)
    return parser.parse_args()

def main():
    global iface, sw_id_hop, sw_id_q,sw_id_egress, count_case_1, count_case_2, count_normal, recv_pkts
    recv_pkts = []
    sw_id_hop = []
    sw_id_q= []
    sw_id_egress= []
    count_case_1 = 0
    count_case_2 = 0
    count_normal = 0

    args = get_args()

    init_time = time.time()

    file_name = f"{args.file_path}/FAT_INT/BMv2/example/packets/result.txt"
    sys.stdout = open(file_name,'w')

    ifaces = [i for i in os.listdir('/sys/class/net/') if 'eth' in i]
    iface = ifaces[0]

    receive_thread = threading.Thread(target=receive_packet, args=())
    receive_thread.daemon = True
    receive_thread.start()

    current_time = 0
    while current_time < 600:
        current_time = time.time()-init_time

    for pkt in recv_pkts:
        parsing_recv_packets(pkt)
    sys.exit()
    
if __name__ == '__main__':   
    main()
