#!/usr/bin/env python
import sys
from time import sleep
from scapy.all import sendp, send, get_if_list, get_if_hwaddr, sendpfast
from scapy.all import Ether, IP, UDP, TCP
import argparse
import random

def get_if():
    ifs=get_if_list()
    iface=None # "h1-eth0"
    for i in get_if_list():
        if "eth0" in i:
            iface=i
            break;
    if not iface:
        print("Cannot find eth0 interface")
        exit(1)
    return iface

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', help='Abs file path', type=str, required=True)
    return parser.parse_args()

def main():
    args = get_args()

    # For logging
    file_name = f"{args.file_path}/FAT_INT/BMv2/example/packets/sending.txt"
    sys.stdout = open(file_name,'w')

    iface = get_if()
    
    pkts = []
    for i in range(10000):
        pkt =  Ether(src=get_if_hwaddr(iface), dst='ff:ff:ff:ff:ff:ff')
        pkt = pkt /IP(src="100.101.102.103", dst="200.201.202.203",tos=0x3, ttl=0x40, id=random.randint(0,200))
        pkt = pkt / TCP(sport=10000+i, dport=20000+i)
        pkts.append(pkt)
        
    count = 0

    sleep(20)

    for pkt in pkts:
        count +=1
        sendp(pkt, iface=iface, verbose=False)
        print(count)

if __name__ == '__main__':    
    main()
