#!/usr/bin/env python
import sys
from time import sleep
from scapy.all import sendp, get_if_list, get_if_hwaddr
from scapy.all import Ether, IP, TCP
import argparse
import random

def get_if():
    ifs = get_if_list()
    iface = None
    for i in ifs:
        if "eth0" in i:
            iface = i
            break
    if not iface:
        print("Cannot find eth0 interface")
        exit(1)
    return iface

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', help='Abs file path', type=str, required=True)
    parser.add_argument('--sender', help='Name of the sending host', type=str, required=True)
    return parser.parse_args()

def main():
    args = get_args()
    iface = get_if()

    file_name = f"{args.file_path}/FAT_INT/BMv2/example/packets/sending_{args.sender}_uc2.txt"
    sys.stdout = open(file_name, 'w')

    print(f"Starting Use Case 2 (MCN) Generator on {args.sender}")

    pkts = []
    # Increased to 5000 packets to better simulate the 5800 TPS MCN workload
    # and provide enough data points for the 13-hop trajectory.
    for i in range(5000): 
        pkt = Ether(src=get_if_hwaddr(iface), dst='ff:ff:ff:ff:ff:ff')
        # Dummy IPs: routing is strictly handled by the ingress port mappings 
        # in our 13-hop tromboning controller.
        pkt = pkt / IP(src="10.0.0.1", dst="10.0.0.16", tos=0x3, ttl=64, id=random.randint(0, 65535))
        
        # Sequence number embedded in TCP source port for NRMSE calculation
        pkt = pkt / TCP(sport=10000 + i, dport=20000 + i)
        pkts.append(pkt)
        
    # Give the 20-switch network a moment to stabilize before blasting traffic
    sleep(5)

    count = 0
    for pkt in pkts:
        count += 1
        sendp(pkt, iface=iface, verbose=False)
        # Reduced sleep to 0.001 to push packets faster, mimicking the heavy MCN signaling rate
        sleep(0.001) 
        if count % 500 == 0:
            print(f"Sent {count} packets through the 13-hop chain...")

if __name__ == '__main__':    
    main()