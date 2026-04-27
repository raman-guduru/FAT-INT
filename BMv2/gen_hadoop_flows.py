import random
import math
import csv
import argparse

class HadoopTrafficGenerator:
    def __init__(self, cdf_file):
        self.cdf = []
        self.load_cdf(cdf_file)
        self.avg_size = self.calculate_average()

    def load_cdf(self, cdf_file):
        """Reads the distribution file where each line is: [size_in_bytes] [CDF_probability]"""
        try:
            with open(cdf_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        val = float(parts[0])
                        prob = float(parts[1])/100
                        self.cdf.append((val, prob))
            # Ensure sorting by probability
            self.cdf.sort(key=lambda x: x[1])
        except FileNotFoundError:
            print(f"Error: Could not find {cdf_file}.")
            print("Please ensure FbHdp_distribution.txt is in the same directory.")
            exit(1)

    def calculate_average(self):
        """Calculates the average flow size from the CDF for the Poisson arrival rate."""
        avg = 0.0
        prev_prob = 0.0
        for val, prob in self.cdf:
            avg += val * (prob - prev_prob)
            prev_prob = prob
        return avg

    def get_random_flow_size(self):
        """Generates a random flow size based on the Hadoop CDF using inverse transform sampling."""
        r = random.random()
        for i, (val, prob) in enumerate(self.cdf):
            if r <= prob:
                if i == 0:
                    return int(val)
                prev_val, prev_prob = self.cdf[i-1]
                # Linear interpolation for smoother distribution
                interpolated = prev_val + (val - prev_val) * ((r - prev_prob) / (prob - prev_prob))
                return int(interpolated)
        return int(self.cdf[-1][0])

def parse_bandwidth(bw_str):
    """Converts a bandwidth string like '10G' or '1G' to bits per second."""
    bw_str = bw_str.upper().strip()
    if bw_str.endswith('G'):
        return float(bw_str[:-1]) * 1e9
    elif bw_str.endswith('M'):
        return float(bw_str[:-1]) * 1e6
    elif bw_str.endswith('K'):
        return float(bw_str[:-1]) * 1e3
    else:
        return float(bw_str)

def main():
    parser = argparse.ArgumentParser(description="Hadoop Flow Generator for FAT-INT Topology")
    parser.add_argument('-l', '--load', type=float, default=0.3, help='Network load (0.0 to 1.0)')
    parser.add_argument('-b', '--bandwidth', type=str, default='1G', help='Link bandwidth (e.g., 10G, 1G, 100M)')
    parser.add_argument('-t', '--time', type=float, default=1.0, help='Duration of trace to generate in seconds')
    parser.add_argument('-d', '--distribution', type=str, default='FbHdp_distribution.txt', help='Path to Hadoop CDF file')
    parser.add_argument('-o', '--output', type=str, default='flows.csv', help='Output CSV file name')

    args = parser.parse_args()

    # Custom Topology IP mappings
    sender_ips = ["10.0.7.1", "10.0.7.2", "10.0.8.3", "10.0.8.4"]     # h1, h2, h3, h4
    receiver_ips = ["10.0.9.5", "10.0.9.6", "10.0.10.7", "10.0.10.8"] # h5, h6, h7, h8

    generator = HadoopTrafficGenerator(args.distribution)
    bandwidth_bps = parse_bandwidth(args.bandwidth)
    
    # λ (Lambda) = (Load * Bandwidth) / (Average Flow Size * 8 bits/byte)
    lam = (args.load * bandwidth_bps) / (generator.avg_size * 8.0)
    
    print(f"--- Generating Hadoop Flows for Custom Fat-Tree ---")
    print(f"Load: {args.load} | Link BW: {args.bandwidth} | Duration: {args.time}s")
    print(f"Avg Flow Size: {generator.avg_size:.2f} bytes | Arrival Rate (λ): {lam:.2f} flows/sec")

    current_time = 0.0
    flow_count = 0

    with open(args.output, 'w', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['src_ip', 'dst_ip', 'dst_port', 'size_bytes', 'start_time_sec'])

        while current_time < args.time:
            # 1. Calculate next arrival time using Exponential Distribution
            inter_arrival = -math.log(1.0 - random.random()) / lam
            current_time += inter_arrival
            
            if current_time >= args.time:
                break

            # 2. Pick Source strictly from h1-h4, Destination strictly from h5-h8
            src_ip = random.choice(sender_ips)
            dst_ip = random.choice(receiver_ips)

            # 3. Get Flow Size from Distribution
            size_bytes = generator.get_random_flow_size()
            
            # 4. Write to CSV (using port 5000 as default)
            writer.writerow([src_ip, dst_ip, 5000, size_bytes, current_time])
            flow_count += 1

    print(f"Done! {flow_count} flows successfully written to {args.output}")

if __name__ == "__main__":
    main()