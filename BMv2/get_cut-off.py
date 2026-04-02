import json
import math
import numpy as np
from scipy.fft import rfft, irfft, rfftfreq
from collections import defaultdict

def calculate_nrmse(orig_vals, recon_vals):
    mse = np.mean((orig_vals - recon_vals) ** 2)
    rmse = np.sqrt(mse)
    val_range = np.max(orig_vals) - np.min(orig_vals)
    if val_range == 0:
        return 0.0 if rmse == 0 else float('inf')
    return (rmse / val_range) * 100.0

def get_cutoff_frequency(times, values, eps_th, step_size_pct=0.01):
    d_o = np.array(values)
    times = np.array(times)
    
    mean_val = np.mean(d_o)
    d_centered = d_o - mean_val
    n = len(d_centered)
    dt = np.mean(np.diff(times)) if n > 1 else 1.0
    
    P = rfft(d_centered)
    freqs = rfftfreq(n, d=dt)
    
    f_max = freqs[-1]
    f_cutoff = f_max
    delta_f = f_max * step_size_pct 
    
    while True:
        f_cutoff -= delta_f
        if f_cutoff <= 0:
            return 0.001 # Return a tiny value to prevent division by zero
            
        P_filtered = P.copy()
        P_filtered[freqs >= f_cutoff] = 0
        
        d_r_centered = irfft(P_filtered, n=n)
        d_r = d_r_centered + mean_val
        
        if calculate_nrmse(d_o, d_r) > eps_th:
            f_cutoff += delta_f 
            break
            
    return f_cutoff

def main(filepath):
    item_mapping = {
        'queue_occ': 'queue_metadata',
        'hop_lat': 'hop_metadata',
        'egress_ts': 'egress_metadata'
    }
    
    # Define the exact thresholds used in Figure 19 (UC1 and UC2)
    thresholds = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    
    # 1. Parse Data to calculate Data Rate (Dr) and Path Length (N)
    all_timestamps = set()
    path_length = 0
    item_data = {k: defaultdict(list) for k in item_mapping.keys()}
    
    with open(filepath, 'r') as f:
        for line in f:
            try:
                pkt = json.loads(line.strip())
                if "event" in pkt: continue
                
                ts = pkt.get("timestamp")
                if ts:
                    all_timestamps.add(ts)
                
                if path_length == 0 and 'queue_metadata' in pkt:
                    path_length = len(pkt['queue_metadata'])

                for item, meta_key in item_mapping.items():
                    if meta_key in pkt:
                        for entry in pkt[meta_key]:
                            # Arbitrarily taking switch_id = 9 to analyze flow
                            if entry.get("switch_id") == 9:
                                item_data[item][9].append((ts, entry.get(item)))
                                
            except json.JSONDecodeError:
                continue
                
    # Calculate Data Rate (Dr)
    sorted_ts = sorted(list(all_timestamps))
    if len(sorted_ts) > 1:
        duration = sorted_ts[-1] - sorted_ts[0] 
        Dr = len(sorted_ts) / duration
    else:
        Dr = 1.0
        
    N = path_length
    
    print(f"================================================================")
    print(f"Network Parameters Extracted: Dr = {Dr:.2f} pkts/s | N = {N} hops")
    print(f"================================================================\n")
    
    # Header for the results table
    print(f"{'Err Thresh':<10} | {'Samp Ratio %':<12} | {'S_i (Queue)':<12} | {'S_i (Hop)':<12} | {'S_i (Egress)':<12}")
    print("-" * 70)

    # 2 & 3. Calculate metrics for ALL defined error thresholds
    for eps in thresholds:
        cutoffs = {}
        for item in item_mapping.keys():
            data = item_data[item][9]
            data.sort(key=lambda x: x[0])
            times = [d[0] for d in data]
            vals = [d[1] for d in data]
            
            if item == 'egress_ts':
                vals = [v - vals[0] for v in vals]
                
            cutoffs[item] = get_cutoff_frequency(times, vals, eps_th=eps)

        min_cutoff = min(cutoffs.values())
        
        # Calculate Sampling Ratio
        R_prime = (2 * min_cutoff * N) / Dr
        sampling_ratio = min(R_prime, 1.0)
        
        r_multiplier = max(1, math.ceil(R_prime))
        
        # Calculate Item-wise Spaces
        spaces = {}
        for item, f_c in cutoffs.items():
            base_space = math.ceil(f_c / min_cutoff)
            spaces[item] = base_space * r_multiplier

        print(f"{str(eps)+'%':<10} | {sampling_ratio * 100:<12.2f} | {spaces['queue_occ']:<12} | {spaces['hop_lat']:<12} | {spaces['egress_ts']:<12}")

if __name__ == "__main__":
    main("BMv2/example/packets/result_temp_h5.txt")