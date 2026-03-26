import sys
import os
sys.path.append('/home/p4/p4-utils')
import argparse
from p4utils.mininetlib.network_API import NetworkAPI
from multiprocessing import Process
from time import sleep

# Run command on Mininet node
def run_command_on_host(host_node, command):
    result = host_node.cmd(command)

# Configure Network
def config_network(p4):
    net = NetworkAPI()

    # If want to use Mininet CLI, modify to True
    net.cli_enabled = False
    
    # Link option
    linkops = dict(bw=1000, delay='1ms', loss=0, use_htb=True)

    # Network general options
    net.setLogLevel('info')

    # Add 10 P4 switches (2 Core, 4 Aggregation, 4 Edge)
    core_switches = [f'c{i}' for i in range(1, 3)]
    agg_switches = [f'a{i}' for i in range(1, 5)]
    edge_switches = [f'e{i}' for i in range(1, 5)]
    
    for sw in core_switches + agg_switches + edge_switches:
        net.addP4Switch(sw)

    # Execute P4 program on switch
    net.setP4SourceAll(p4)

    # Add 8 hosts
    hosts = [f'h{i}' for i in range(1, 9)]
    for h in hosts:
        net.addHost(h)

    # Construct Network Topology: 2-ary fat-tree
    # 1. Core to Aggregation 
    for core in core_switches:
        for agg in agg_switches:
            net.addLink(core, agg, **linkops)

    # 2. Aggregation to Edge (Pod 1)
    net.addLink('a1', 'e1', **linkops)
    net.addLink('a1', 'e2', **linkops)
    net.addLink('a2', 'e1', **linkops)
    net.addLink('a2', 'e2', **linkops)

    # 3. Aggregation to Edge (Pod 2)
    net.addLink('a3', 'e3', **linkops)
    net.addLink('a3', 'e4', **linkops)
    net.addLink('a4', 'e3', **linkops)
    net.addLink('a4', 'e4', **linkops)

    # 4. Edge to Hosts
    net.addLink('e1', 'h1', **linkops)
    net.addLink('e1', 'h2', **linkops)
    net.addLink('e2', 'h3', **linkops)
    net.addLink('e2', 'h4', **linkops)
    net.addLink('e3', 'h5', **linkops)
    net.addLink('e3', 'h6', **linkops)
    net.addLink('e4', 'h7', **linkops)
    net.addLink('e4', 'h8', **linkops)
        
    # Assignment strategy
    net.mixed()

    return net

# Parser for P4 program and file path
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--p4', help='P4 source code for INT mode', type=str, required=True)
    parser.add_argument('--file_path', help='Abs file path', type=str, required=True)
    return parser.parse_args()


def main():
    commands = []
    processes = []
    
    args = get_args()

    net = config_network(args.p4)
    net.startNetwork()
    
    print("Waiting for inserting rules...")
    input()
    print("Insert rules complete!")

    
    
    # As per the paper: Divide into sending and receiving hosts equally
    # We will use Pod 1 hosts as senders, Pod 2 hosts as receivers.
    senders = ['h1', 'h2', 'h3', 'h4']
    receivers = ['h5', 'h6', 'h7', 'h8']

    # 1. Start receiver scripts first so they are listening
    for recv in receivers:
        recv_cmd = f'python3 {args.file_path}/FAT_INT/BMv2/example/packets/uc1_receive.py --file_path {args.file_path} --receiver {recv}'
        host_node = net.net.get(recv)
        process = Process(target=run_command_on_host, args=(host_node, recv_cmd))
        process.start()
        processes.append(process)

    # Brief pause to ensure receivers are fully initialized
    sleep(2)

    # 2. Start sender scripts generating the Hadoop workload
    for sender in senders:
        send_cmd = f'python3 {args.file_path}/FAT_INT/BMv2/example/packets/uc1_send.py --file_path {args.file_path} --sender {sender} --load 0.4 --num_flows 80'
        host_node = net.net.get(sender)
        process = Process(target=run_command_on_host, args=(host_node, send_cmd))
        process.start()
        processes.append(process)
    
    for process in processes:
        process.join()
    
    # Turn off the Mininet
    net.stopNetwork()

if __name__ == '__main__':
    main()