import socket
import time
import threading
import csv
import argparse
import random
from scapy.all import Ether, IP, TCP, Raw, get_if_hwaddr

# Hardcoded topology mapping from your Fat-Tree setup
HOST_IP_MAP = {
    "h1": "10.0.7.1", "h2": "10.0.7.2",
    "h3": "10.0.8.3", "h4": "10.0.8.4",
    "h5": "10.0.9.5", "h6": "10.0.9.6",
    "h7": "10.0.10.7", "h8": "10.0.10.8",
}

IP_TO_MAC = {
    "10.0.7.1": "00:00:0a:00:07:01", "10.0.7.2": "00:00:0a:00:07:02",
    "10.0.8.3": "00:00:0a:00:08:03", "10.0.8.4": "00:00:0a:00:08:04",
    "10.0.9.5": "00:00:0a:00:09:05", "10.0.9.6": "00:00:0a:00:09:06",
    "10.0.10.7": "00:00:0a:00:0a:07", "10.0.10.8": "00:00:0a:00:0a:08",
}

def send_flow_tcp_raw(iface, src_ip, dst_ip, size_bytes):
    """
    Independent worker function to send a specific flow.
    Uses raw sockets to blast TCP packets without connection overhead.
    """
    try:
        sport = random.randint(10000, 60000)
        dport = random.randint(20000, 65000)
        
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
        sock.bind((iface, 0))
        
        base_pkt = Ether(
            src=get_if_hwaddr(iface),
            dst=IP_TO_MAC[dst_ip]
        ) / IP(
            src=src_ip,
            dst=dst_ip,
            tos=0x03
        ) / TCP(
            sport=sport,
            dport=dport,
            flags="PA"
        )
        
        MTU_PAYLOAD = 1400
        bytes_left = size_bytes
        
        # PERFORMANCE FIX: Pre-compile the full MTU packet to bytes once.
        # Scapy packet building is too slow to put inside the while loop.
        full_pkt_bytes = bytes(base_pkt / Raw(load=b"X" * MTU_PAYLOAD))
        
        while bytes_left >= MTU_PAYLOAD:
            sock.send(full_pkt_bytes)
            bytes_left -= MTU_PAYLOAD
            
        # Send the remaining bytes
        if bytes_left > 0:
            remainder_pkt_bytes = bytes(base_pkt / Raw(load=b"X" * bytes_left))
            sock.send(remainder_pkt_bytes)
            
        sock.close()
    except Exception as e:
        print(f"Error sending flow to {dst_ip}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Distributed TCP Flow Sender for FAT-INT")
    parser.add_argument('--host', type=str, required=True, help="This host's name (e.g., h1, h2)")
    parser.add_argument('--trace', type=str, required=True, help="Path to the flow trace CSV")
    parser.add_argument('--iface', type=str, default=None, help="Specific interface (defaults to host-eth0)")
    args = parser.parse_args()

    # Look up IP and derive default Mininet interface name (e.g., h1-eth0)
    target_ip = HOST_IP_MAP.get(args.host)
    iface = args.iface if args.iface else f"{args.host}-eth0"
    
    if not target_ip:
        print(f"Error: Unknown host '{args.host}'.")
        return

    flows = []
    
    # 1. Read and Filter
    with open(args.trace, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['src_ip'] == target_ip:
                flows.append({
                    'dst_ip': row['dst_ip'],
                    'size': int(row['size_bytes']),
                    'time': float(row['start_time_sec'])
                })

    if not flows:
        print(f"No flows mapped to {args.host}.")
        return

    flows.sort(key=lambda x: x['time'])
    print(f"Host {args.host} ({target_ip}) on {iface} ready. Triggering {len(flows)} TCP flows...")

    # 2. Synchronized Execution
    start_epoch = time.time()

    for flow in flows:
        current_time = time.time() - start_epoch
        
        if flow['time'] > current_time:
            time.sleep(flow['time'] - current_time)

        # Fire and forget raw socket threads
        t = threading.Thread(
            target=send_flow_tcp_raw,
            args=(iface, target_ip, flow['dst_ip'], flow['size'])
        )
        t.start()

if __name__ == "__main__":
    main()