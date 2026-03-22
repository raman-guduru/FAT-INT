import sys
import os
sys.path.append('/home/p4/p4-utils')
import argparse
from p4utils.mininetlib.network_API import NetworkAPI
from multiprocessing import Process
from time import sleep

def run_command_on_host(host_node, command):
    host_node.cmd(command)

def config_network(p4):
    net = NetworkAPI()
    net.cli_enabled = False
    linkops = dict(bw=1000, delay='1ms', loss=0, use_htb=True)
    net.setLogLevel('info')

    # --- 1. Add 20 P4 Switches ---
    # 4 Core (c1-c4), 8 Aggregation (a1-a8), 8 Edge (e1-e8)
    core_switches = [f'c{i}' for i in range(1, 5)]
    agg_switches = [f'a{i}' for i in range(1, 9)]
    edge_switches = [f'e{i}' for i in range(1, 9)]
    
    for sw in core_switches + agg_switches + edge_switches:
        net.addP4Switch(sw)

    net.setP4SourceAll(p4)

    # --- 2. Add 16 Hosts ---
    hosts = [f'h{i}' for i in range(1, 17)]
    for h in hosts:
        net.addHost(h)

    # --- 3. Link the 4-ary Fat-Tree ---
    # Core to Aggregation
    # c1 & c2 connect to the first agg switch of each pod (a1, a3, a5, a7)
    for core in ['c1', 'c2']:
        for agg in ['a1', 'a3', 'a5', 'a7']:
            net.addLink(core, agg, **linkops)
            
    # c3 & c4 connect to the second agg switch of each pod (a2, a4, a6, a8)
    for core in ['c3', 'c4']:
        for agg in ['a2', 'a4', 'a6', 'a8']:
            net.addLink(core, agg, **linkops)

    # Aggregation to Edge (4 Pods)
    # Pod 1
    net.addLink('a1', 'e1', **linkops); net.addLink('a1', 'e2', **linkops)
    net.addLink('a2', 'e1', **linkops); net.addLink('a2', 'e2', **linkops)
    # Pod 2
    net.addLink('a3', 'e3', **linkops); net.addLink('a3', 'e4', **linkops)
    net.addLink('a4', 'e3', **linkops); net.addLink('a4', 'e4', **linkops)
    # Pod 3
    net.addLink('a5', 'e5', **linkops); net.addLink('a5', 'e6', **linkops)
    net.addLink('a6', 'e5', **linkops); net.addLink('a6', 'e6', **linkops)
    # Pod 4
    net.addLink('a7', 'e7', **linkops); net.addLink('a7', 'e8', **linkops)
    net.addLink('a8', 'e7', **linkops); net.addLink('a8', 'e8', **linkops)

    # Edge to Hosts (2 hosts per edge switch)
    for i in range(8):
        edge = f'e{i+1}'
        net.addLink(edge, f'h{(i*2)+1}', **linkops)
        net.addLink(edge, f'h{(i*2)+2}', **linkops)
        
    net.mixed()
    return net

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--p4', help='P4 source code for INT mode', type=str, required=True)
    parser.add_argument('--file_path', help='Abs file path', type=str, required=True)
    return parser.parse_args()

def main():
    processes = []
    args = get_args()

    net = config_network(args.p4)
    net.startNetwork()
    
    print("Waiting for inserting rules...")
    input()
    print("Insert rules complete!")
    
    # We will use h1 as the sender, and route it through 13 switches to h16 (receiver)
    receivers = ['h16']
    senders = ['h1']

    for recv in receivers:
        recv_cmd = f'python3 {args.file_path}/FAT_INT/BMv2/example/packets/uc2_receive.py --file_path {args.file_path} --receiver {recv}'
        host_node = net.net.get(recv)
        process = Process(target=run_command_on_host, args=(host_node, recv_cmd))
        process.start()
        processes.append(process)

    sleep(2)

    for sender in senders:
        send_cmd = f'python3 {args.file_path}/FAT_INT/BMv2/example/packets/uc2_send.py --file_path {args.file_path} --sender {sender}'
        host_node = net.net.get(sender)
        process = Process(target=run_command_on_host, args=(host_node, send_cmd))
        process.start()
        processes.append(process)
    
    for process in processes:
        process.join()
    
    net.stopNetwork()

if __name__ == '__main__':
    main()