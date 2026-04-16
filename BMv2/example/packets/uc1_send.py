#!/usr/bin/env python3
import sys
import os
import time
import random
import argparse
from scapy.all import sendp, get_if_list, get_if_hwaddr
from scapy.all import Ether, IP, TCP, Raw

random.seed(42)

# ---------------------------------------------------------------------
# Interface Helper
# ---------------------------------------------------------------------
def get_if():
    ifs = get_if_list()
    iface = None
    for i in ifs:
        if "eth0" in i:
            iface = i
            break
    if not iface:
        print("Cannot find eth0 interface")
        sys.exit(1)
    return iface


# ---------------------------------------------------------------------
# Argument Parser
# ---------------------------------------------------------------------
def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--file_path', help='Absolute project path', type=str, required=True)
    parser.add_argument('--sender', help='Sender host name (e.g., h1)', type=str, required=True)

    # Hadoop workload controls
    parser.add_argument('--load', help='Workload factor (0.4 = 40%)', type=float, default=0.4)
    parser.add_argument('--num_flows', help='Number of logical flows to generate', type=int, default=80)
    parser.add_argument('--tos', help='IP ToS/DSCP value (hex or int)', type=lambda x: int(x, 0), default=0x3)

    # Optional fixed destination override
    parser.add_argument('--fixed_dst', help='Force all flows to one destination IP', type=str, default=None)

    return parser.parse_args()


# ---------------------------------------------------------------------
# REAL Host IP Mapping (matches your Mininet)
# ---------------------------------------------------------------------
HOST_IP_MAP = {
    "h1": "10.0.7.1",
    "h2": "10.0.7.2",
    "h3": "10.0.8.3",
    "h4": "10.0.8.4",
    "h5": "10.0.9.5",
    "h6": "10.0.9.6",
    "h7": "10.0.10.7",
    "h8": "10.0.10.8",
}

# Hadoop-like receiver pool
RECEIVER_POOL = ["10.0.9.5", "10.0.9.6", "10.0.10.7", "10.0.10.8"]


# ---------------------------------------------------------------------
# Weighted Random Selection
# ---------------------------------------------------------------------
def weighted_choice(values, weights):
    return random.choices(values, weights=weights, k=1)[0]


# ---------------------------------------------------------------------
# Hadoop-like Flow Profile Generator
# ---------------------------------------------------------------------
def generate_hadoop_flow_profile():
    """
    Approximate Hadoop shuffle / datacenter traffic:
      - many small flows
      - some medium flows
      - few large shuffle-like flows
    """
    flow_class = weighted_choice(
        ["small", "medium", "large"],
        [60, 30, 10]
    )

    if flow_class == "small":
        packets_in_flow = random.randint(8, 25)
        payload_size = random.randint(200, 600)
        inter_pkt_gap = random.uniform(0.002, 0.006)
        inter_flow_gap = random.uniform(0.03, 0.10)

    elif flow_class == "medium":
        packets_in_flow = random.randint(30, 80)
        payload_size = random.randint(500, 1000)
        inter_pkt_gap = random.uniform(0.0015, 0.004)
        inter_flow_gap = random.uniform(0.08, 0.20)

    else:  # large
        packets_in_flow = random.randint(100, 300)
        payload_size = random.randint(900, 1400)
        inter_pkt_gap = random.uniform(0.0008, 0.003)
        inter_flow_gap = random.uniform(0.15, 0.40)

    return packets_in_flow, payload_size, inter_pkt_gap, inter_flow_gap, flow_class


# ---------------------------------------------------------------------
# Load Scaling
# ---------------------------------------------------------------------
def scale_profile_for_load(packets_in_flow, inter_pkt_gap, inter_flow_gap, load_factor):
    if load_factor <= 0:
        load_factor = 0.4

    scaled_inter_pkt_gap = inter_pkt_gap * (1-load_factor)
    scaled_inter_flow_gap = inter_flow_gap / load_factor
    scaled_packets = max(3, int(packets_in_flow * (0.7 + 0.3 * load_factor)))

    return scaled_packets, scaled_inter_pkt_gap, scaled_inter_flow_gap


# ---------------------------------------------------------------------
# Destination Selection
# ---------------------------------------------------------------------
def choose_destination(fixed_dst=None):
    if fixed_dst is not None:
        return fixed_dst
    return random.choice(RECEIVER_POOL)


# ---------------------------------------------------------------------
# Packet Builder
# ---------------------------------------------------------------------
def make_packet(iface, src_ip, dst_ip, tos, sport, dport, payload_size):
    payload = os.urandom(payload_size)

    pkt = Ether(src=get_if_hwaddr(iface), dst='ff:ff:ff:ff:ff:ff')
    pkt = pkt / IP(
        src=src_ip,
        dst=dst_ip,
        tos=tos,
        ttl=64,
        id=random.randint(0, 65535)
    )
    pkt = pkt / TCP(
        sport=sport,
        dport=dport,
        seq=random.randint(0, 2**32 - 1),
        ack=0,
        flags="PA",
        window=8192
    )
    pkt = pkt / Raw(load=payload)

    return pkt


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main():
    args = get_args()
    iface = get_if()

    if args.sender not in HOST_IP_MAP:
        print(f"Unknown sender host: {args.sender}")
        sys.exit(1)

    src_ip = HOST_IP_MAP[args.sender]

    # Log directory
    log_dir = os.path.join(args.file_path, "FAT_INT", "BMv2", "example", "packets")
    os.makedirs(log_dir, exist_ok=True)

    file_name = os.path.join(log_dir, f"sending_{args.sender}.txt")
    sys.stdout = open(file_name, 'w', buffering=1)

    print("=" * 80)
    print(f"Starting Hadoop-like Traffic Generator on {args.sender}")
    print(f"Interface           : {iface}")
    print(f"Source IP           : {src_ip}")
    print(f"Logical flows       : {args.num_flows}")
    print(f"Load factor         : {args.load * 100:.1f}%")
    print(f"Receiver pool       : {RECEIVER_POOL if args.fixed_dst is None else [args.fixed_dst]}")
    print("=" * 80)

    time.sleep(5)

    total_packets_sent = 0
    total_bytes_sent = 0
    flow_stats = []

    for flow_id in range(args.num_flows):
        dst_ip = choose_destination(args.fixed_dst)

        packets_in_flow, payload_size, inter_pkt_gap, inter_flow_gap, flow_class = generate_hadoop_flow_profile()

        packets_in_flow, inter_pkt_gap, inter_flow_gap = scale_profile_for_load(
            packets_in_flow,
            inter_pkt_gap,
            inter_flow_gap,
            args.load
        )

        sport = random.randint(10000, 60000)
        dport = random.randint(20000, 65000)

        flow_bytes = 0
        flow_start = time.time()

        print(f"\n[FLOW {flow_id+1}/{args.num_flows}] "
              f"class={flow_class.upper()} "
              f"src={src_ip} -> dst={dst_ip} "
              f"pkts={packets_in_flow} "
              f"payload={payload_size}B "
              f"sport={sport} dport={dport}")

        for pkt_idx in range(packets_in_flow):
            pkt = make_packet(
                iface=iface,
                src_ip=src_ip,
                dst_ip=dst_ip,
                tos=args.tos,
                sport=sport,
                dport=dport,
                payload_size=payload_size
            )

            sendp(pkt, iface=iface, verbose=False)

            pkt_size = len(pkt)
            total_packets_sent += 1
            total_bytes_sent += pkt_size
            flow_bytes += pkt_size

            if total_packets_sent % 100 == 0:
                print(f"  -> Total packets sent so far: {total_packets_sent}")

            time.sleep(inter_pkt_gap)

        flow_end = time.time()
        flow_duration = flow_end - flow_start

        flow_stats.append({
            "flow_id": flow_id + 1,
            "class": flow_class,
            "src": src_ip,
            "dst": dst_ip,
            "packets": packets_in_flow,
            "bytes": flow_bytes,
            "duration": round(flow_duration, 4)
        })

        print(f"  Completed flow {flow_id+1}: "
              f"{packets_in_flow} pkts, {flow_bytes} bytes, "
              f"{flow_duration:.3f}s")

        time.sleep(inter_flow_gap)

    print("\n" + "=" * 80)
    print("HADOOP-LIKE WORKLOAD REPLAY COMPLETE")
    print("=" * 80)
    print(f"Sender host         : {args.sender}")
    print(f"Source IP           : {src_ip}")
    print(f"Total logical flows : {args.num_flows}")
    print(f"Total packets sent  : {total_packets_sent}")
    print(f"Total bytes sent    : {total_bytes_sent}")
    print(f"Approx MB sent      : {total_bytes_sent / (1024 * 1024):.2f} MB")
    print("=" * 80)

    print("\nPer-flow summary:")
    for stat in flow_stats:
        print(f"Flow {stat['flow_id']:03d} | "
              f"{stat['class']:>6} | "
              f"{stat['src']} -> {stat['dst']} | "
              f"{stat['packets']:4d} pkts | "
              f"{stat['bytes']:7d} bytes | "
              f"{stat['duration']:6.3f}s")


if __name__ == '__main__':
    main()