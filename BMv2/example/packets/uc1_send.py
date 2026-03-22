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

    # Create file using the exact host name passed from Mininet
    file_name = f"{args.file_path}/FAT_INT/BMv2/example/packets/sending_{args.sender}.txt"
    sys.stdout = open(file_name, 'w')

    print(f"Starting Use Case 1 Generator on {args.sender}")

    pkts = []
    for i in range(1000): 
        pkt = Ether(src=get_if_hwaddr(iface), dst='ff:ff:ff:ff:ff:ff')
        # Dummy IPs: routing is handled by port mapping in the controller
        pkt = pkt / IP(src="10.0.0.1", dst="10.0.0.2", tos=0x3, ttl=64, id=random.randint(0, 65535))
        pkt = pkt / TCP(sport=10000 + i, dport=20000 + i)
        pkts.append(pkt)
        
    sleep(5)

    count = 0
    for pkt in pkts:
        count += 1
        sendp(pkt, iface=iface, verbose=False)
        sleep(0.005) 
        if count % 100 == 0:
            print(f"Sent {count} packets...")

if __name__ == '__main__':    
    main()