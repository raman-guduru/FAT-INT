#!/usr/bin/env python3
import os
import json
import math
import random
import argparse
from collections import defaultdict

# =====================================================================
# FAT-INT SIMULATION PARAMETERS (Based strictly on 3.0% Error Profile)
# =====================================================================
INGRESS_SAMPLING_RATIO = 0.2003  # 20.03%
SPACES = {
    "queue": 20,
    "hop": 7,
    "egress": 1
}

def load_full_records(folder, prefix, receivers):
    records = []
    for r in receivers:
        filepath = os.path.join(folder, f"{prefix}_{r}.txt")
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r") as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                    if "flow_id" in obj:
                        records.append(obj)
                except:
                    continue
    return records

def simulate_fat_int(records, metric_type):
    truth_series = defaultdict(dict)
    sampled_series = defaultdict(dict)
    
    metadata_key = f"{metric_type}_metadata"
    val_key = "queue_occ" if metric_type == "queue" else "hop_lat" if metric_type == "hop" else "egress_ts"
    S_i = SPACES[metric_type]

    for pkt_idx, rec in enumerate(records):
        for item in rec.get(metadata_key, []):
            sw_id = item.get("switch_id")
            val = item.get(val_key)
            if sw_id is not None and val is not None:
                truth_series[sw_id][pkt_idx] = val

        if random.random() > INGRESS_SAMPLING_RATIO:
            continue

        slots = {}
        path_data = rec.get(metadata_key, [])
        
        for hop_idx, item in enumerate(path_data):
            n = hop_idx + 1
            sw_id = item.get("switch_id")
            val = item.get(val_key)
            
            if sw_id is None or val is None:
                continue
                
            slot_idx = (n - 1) % S_i
            prob = 1.0 / math.ceil(n / S_i)
            
            if random.random() <= prob:
                slots[slot_idx] = (sw_id, val)
                
        for slot_data in slots.values():
            final_sw_id, final_val = slot_data
            sampled_series[final_sw_id][pkt_idx] = final_val

    return truth_series, sampled_series

def calculate_nrmse(truth_series, sampled_series, normalize_method, is_egress=False):
    switch_nrmses = []

    for sw_id, full_pkts in truth_series.items():
        fat_pkts = sampled_series.get(sw_id, {})
        if not full_pkts: continue
        
        max_pkt = max(full_pkts.keys())
        last_seen = None
        
        truth_sw = []
        pred_sw = []

        # ========================================================
        # RECONSTRUCTION: FORWARD FILL (LOCF)
        # ========================================================
        for p in range(max_pkt + 1):
            if p not in full_pkts: 
                continue
                
            truth_val = full_pkts[p]
            
            if p in fat_pkts:
                last_seen = fat_pkts[p]
                pred_val = last_seen
            else:
                if last_seen is not None:
                    pred_val = last_seen
                else:
                    continue # Wait until we capture the first valid sample
                    
            truth_sw.append(truth_val)
            pred_sw.append(pred_val)

        if not truth_sw:
            continue

        # For Egress TS, normalize absolute UNIX timestamps to relative elapsed time
        if is_egress:
            base_val = truth_sw[0]
            truth_sw = [v - base_val for v in truth_sw]
            pred_sw = [v - base_val for v in pred_sw]

        # Calculate NRMSE for this switch
        mse = sum((t - p)**2 for t, p in zip(truth_sw, pred_sw)) / len(truth_sw)
        rmse = math.sqrt(mse)
        
        if normalize_method == "range":
            denom = max(truth_sw) - min(truth_sw)
        else: # "mean"
            denom = sum(truth_sw) / len(truth_sw)
            
        if denom > 0:
            switch_nrmses.append(rmse / denom)

    if not switch_nrmses: return 0.0
    return (sum(switch_nrmses) / len(switch_nrmses)) * 100.0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=str, required=True)
    parser.add_argument("--full_prefix", type=str, default="result_fullINT")
    parser.add_argument("--receivers", nargs="+", default=["h5", "h6", "h7", "h8"])
    args = parser.parse_args()

    print(f"Loading files from {args.folder}...")
    records = load_full_records(args.folder, args.full_prefix, args.receivers)
    
    if not records:
        print("No records found. Check your folder path and prefix.")
        return

    print(f"Loaded {len(records)} packets. Simulating FAT-INT with Forward Fill...")

    truth_q, samp_q = simulate_fat_int(records, "queue")
    queue_nrmse = calculate_nrmse(truth_q, samp_q, normalize_method="range")
    
    truth_h, samp_h = simulate_fat_int(records, "hop")
    hop_nrmse = calculate_nrmse(truth_h, samp_h, normalize_method="range")
    
    truth_e, samp_e = simulate_fat_int(records, "egress")
    egress_nrmse = calculate_nrmse(truth_e, samp_e, normalize_method="range", is_egress=False)

    print("\n=== FAT-INT Offline Simulation Results ===")
    print(f"Queue Occupancy  : {queue_nrmse:.3f}%")
    print(f"Hop Latency      : {hop_nrmse:.3f}%")
    print(f"Egress Timestamp : {egress_nrmse:.3f}%")

if __name__ == "__main__":
    main()