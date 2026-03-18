import argparse
from p4utils.mininetlib.network_API import NetworkAPI
from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.link import TCLink
from multiprocessing import Process
from time import sleep
import subprocess

# # Run command on Mininet node
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

    # Add p4 switches
    net.addP4Switch('s1')
    net.addP4Switch('s2') 
    net.addP4Switch('s3')
    net.addP4Switch('s4') 
    net.addP4Switch('s5')

    # Execute P4 program on switch
    net.setP4SourceAll(p4)

    # Add hosts
    hosts = []
    for i in range (0,2):
        hosts.append(net.addHost('h%d' % (i+1)))

    # Construct Network Topology : Linear with 5 hops
    net.addLink('h1', 's1',**linkops)
    net.addLink('h2', 's5',**linkops)
    net.addLink('s1', 's2',**linkops)
    net.addLink('s2', 's3',**linkops)
    net.addLink('s3', 's4',**linkops)
    net.addLink('s4', 's5',**linkops)
        
    # Assignment strategy
    net.mixed()

    # Nodes general options: Log, Pcap ,,,
    # net.enableCpuPortAll()
    # net.enablePcapDumpAll()
    # net.enableLogAll()

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
    
    # Execute command on Mininet nodes simultaneously
    command1 = f'python3 {args.file_path}/FAT_INT/BMv2/example/packets/send.py --file_path {args.file_path}'
    command2 = f'python3 {args.file_path}/FAT_INT/BMv2/example/packets/receive.py --file_path {args.file_path}'
    commands.append(command1)
    commands.append(command2)

    process1 = Process(target=run_command_on_host, args=(net.net.get('h1'), command1))
    process1.start()
    processes.append(process1)

    process2 = Process(target=run_command_on_host, args=(net.net.get('h2'), command2))
    process2.start()    
    processes.append(process2)
    

    for process in processes :
        process.join()
    
    # Turn off the Mininet
    net.stopNetwork()


if __name__ == '__main__':
    main()
