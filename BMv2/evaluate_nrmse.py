import sys
import json
import argparse
import numpy as np
from collections import defaultdict

def load_data(filepath, target_item):
    """
    Reads the JSON log file and groups the specified telemetry item by switch_id.
    """
    node_data = defaultdict(list)
    with open(filepath, 'r') as f:
        for line in f:
            try:
                pkt = json.loads(line.strip())
                if target_item in pkt:
                    # Append tuple of (timestamp, value)
                    node_data[pkt['switch_id']].append((pkt['timestamp'], pkt[target_item]))
            except json.JSONDecodeError:
                continue
    
    # Sort chronologically for interpolation
    for node in node_data:
        node_data[node].sort(key=lambda x: x[0])
    return node_data

def calculate_nrmse(orig_times, orig_vals, samp_times, samp_vals):
    orig_times = np.array(orig_times)
    orig_vals = np.array(orig_vals)
    samp_times = np.array(samp_times)
    samp_vals = np.array(samp_vals)

    if len(samp_times) < 2 or len(orig_times) == 0:
        return float('nan')

    # --- NEW NORMALIZATION BLOCK ---
    # If the values are timestamps (very large numbers), normalize them to start at 0
    if np.mean(orig_vals) > 1000000: # Simple check to see if we are looking at Egress TS
        orig_vals = orig_vals - orig_vals[0]
        samp_vals = samp_vals - samp_vals[0]
    # -------------------------------

    # Reconstruct trace using linear interpolation
    reconstructed_vals = np.interp(orig_times, samp_times, samp_vals)
    
    # ... rest of the function remains the same ...

    # Root Mean Squared Error
    mse = np.mean((orig_vals - reconstructed_vals) ** 2)
    rmse = np.sqrt(mse)

    # Normalize by the range of the original data
    val_range = np.max(orig_vals) - np.min(orig_vals)

    if val_range == 0:
        return 0.0 if rmse == 0 else float('inf')

    return (rmse / val_range) * 100.0

def evaluate(baseline_file, sampled_file):
    telemetry_items = ['queue_occ', 'hop_lat', 'egress_ts']
    
    print(f"--- FAT-INT NRMSE Evaluation ---")
    print(f"Baseline: {baseline_file}")
    print(f"Sampled:  {sampled_file}\n")

    for item in telemetry_items:
        orig_nodes = load_data(baseline_file, item)
        samp_nodes = load_data(sampled_file, item)

        node_errors = []
        for switch_id, orig_data in orig_nodes.items():
            if switch_id not in samp_nodes:
                continue 
                
            samp_data = samp_nodes[switch_id]
            
            orig_t = [d[0] for d in orig_data]
            orig_v = [d[1] for d in orig_data]
            samp_t = [d[0] for d in samp_data]
            samp_v = [d[1] for d in samp_data]

            nrmse = calculate_nrmse(orig_t, orig_v, samp_t, samp_v)
            if not np.isnan(nrmse) and not np.isinf(nrmse):
                node_errors.append(nrmse)

        avg_nrmse = np.mean(node_errors) if node_errors else float('nan')
        
        # Formatting output for readability
        item_name = item.replace('_', ' ').title()
        print(f"{item_name.ljust(18)}: {avg_nrmse:.2f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate NRMSE for FAT-INT")
    parser.add_argument('--baseline', type=str, required=True, help="Path to 100% baseline JSON txt file")
    parser.add_argument('--sampled', type=str, required=True, help="Path to sampled JSON txt file")
    
    args = parser.parse_args()
    evaluate(args.baseline, args.sampled)