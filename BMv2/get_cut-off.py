import json
import math
import numpy as np
from scipy.fft import rfft, irfft, rfftfreq
from collections import defaultdict

# -----------------------------
# Signal Processing Helpers
# -----------------------------

def resample_uniform(times, values, num_points=1024):
    times = np.array(times)
    values = np.array(values)

    if len(times) < 4:
        return times, values

    t_min, t_max = times[0], times[-1]
    new_times = np.linspace(t_min, t_max, num_points)
    new_values = np.interp(new_times, times, values)

    return new_times, new_values

def smooth_signal(values, window_size=5):
    if len(values) < window_size:
        return values
    return np.convolve(values, np.ones(window_size) / window_size, mode='same')

def clip_outliers(values, percentile=99):
    upper = np.percentile(values, percentile)
    lower = np.percentile(values, 100 - percentile)
    return np.clip(values, lower, upper)

# -----------------------------
# Error Metric
# -----------------------------

def calculate_nrmse(orig_vals, recon_vals):
    orig_vals = np.array(orig_vals)
    recon_vals = np.array(recon_vals)

    if len(orig_vals) == 0:
        return float('inf')

    mse = np.mean((orig_vals - recon_vals) ** 2)
    rmse = np.sqrt(mse)

    val_range = np.max(orig_vals) - np.min(orig_vals)
    if val_range == 0:
        return 0.0 if rmse == 0 else float('inf')

    return (rmse / val_range) * 100.0

# -----------------------------
# Cutoff Frequency (IFE)
# -----------------------------

def get_cutoff_frequency(times, values, eps_th, step_size_pct=0.01):
    if len(times) < 32:
        return 0.001

    times = np.array(times)
    values = np.array(values)
    idx = np.argsort(times)
    times, values = times[idx], values[idx]

    times, unique_idx = np.unique(times, return_index=True)
    values = values[unique_idx]

    if len(times) < 32:
        return 0.001

    times, values = resample_uniform(times, values)
    # values = clip_outliers(values)
    # values = smooth_signal(values)

    dt = np.mean(np.diff(times))
    if dt <= 0:
        return 0.001

    mean_val = np.mean(values)
    d_centered = values - mean_val
    n = len(d_centered)

    P = rfft(d_centered)
    freqs = rfftfreq(n, d=dt)

    if len(freqs) < 2:
        return 0.001

    f_max = freqs[-1]
    
    delta_f = max(f_max * step_size_pct, freqs[1])
    f_cutoff = f_max

    while f_cutoff > 0:
        f_cutoff -= delta_f
        if f_cutoff <= 0:
            return freqs[1]

        P_filtered = P.copy()
        P_filtered[freqs >= f_cutoff] = 0
        d_r_centered = irfft(P_filtered, n=n)
        d_r = d_r_centered + mean_val

        error = calculate_nrmse(values, d_r)
        if error > eps_th:
            f_cutoff += delta_f
            break

    return max(f_cutoff, freqs[1])

# -----------------------------
# Main Logic
# -----------------------------

def main(file_paths):
    item_mapping = {
        'queue_occ': 'queue_metadata',
        'hop_lat': 'hop_metadata',
        'egress_ts': 'egress_metadata'
    }

    thresholds = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    item_data = {k: defaultdict(list) for k in item_mapping.keys()}
    
    node_timestamps = defaultdict(list)
    path_length = 0

    # Aggregate data from all provided files, mapping by specific switch_id
    for filepath in file_paths:
        with open(filepath, 'r') as f:
            for line in f:
                try:
                    pkt = json.loads(line.strip())
                    if "event" in pkt: continue
                    ts = pkt.get("timestamp")
                    if ts is None: continue
                    
                    if path_length == 0 and 'queue_metadata' in pkt:
                        path_length = len(pkt['queue_metadata'])
                        
                    seen_switches = set()
                    for item, meta_key in item_mapping.items():
                        if meta_key in pkt:
                            for entry in pkt[meta_key]:
                                sw = entry.get("switch_id")
                                val = entry.get(item)
                                if sw is not None:
                                    if val is not None:
                                        item_data[item][sw].append((ts, val))
                                    # Ensure we only log 1 packet arrival per switch per timestamp
                                    if sw not in seen_switches:
                                        node_timestamps[sw].append(ts)
                                        seen_switches.add(sw)
                except json.JSONDecodeError:
                    continue

    if not node_timestamps:
        print("No valid switch data found.")
        return

    # Automatically find the Bottleneck Node (the switch that processed the most packets)
    print([len(node_timestamps[k]) for k in range(1,11)])
    target_sw = max(node_timestamps, key=lambda k: len(node_timestamps[k]))
    timestamps = sorted(node_timestamps[target_sw])
    
    total_packets = len(timestamps)
    
    # Calculate Data Rate (Dr) specifically for the Target Node
    if total_packets > 1:
        duration = timestamps[-1] - timestamps[0]
        Dr = total_packets / duration if duration > 0 else 1.0
    else:
        Dr = 1.0

    N = path_length if path_length > 0 else 1

    print(f"--- Profiling Single Node: Switch {target_sw} ---")
    print(f"Network Parameters Extracted: Dr = {Dr:.2f} pkts/s | N = {N} hops")
    print(f"{'Err Thresh':<10} | {'Samp Ratio %':<12} | {'S_i (Queue)':<12} | {'S_i (Hop)':<12} | {'S_i (Egress)':<12}")
    print("-" * 70)

    for eps in thresholds:
        cutoffs = {}
        # Perform frequency analysis strictly on the Target Node's telemetry data
        for item in item_mapping.keys():
            data = item_data[item].get(target_sw, [])
            if len(data) < 32:
                cutoffs[item] = 0.001
                continue
            
            data.sort(key=lambda x: x[0])
            vals = [d[1] for d in data]
            
            f_c = get_cutoff_frequency([d[0] for d in data], vals, eps, step_size_pct=0.01)
            cutoffs[item] = f_c

        min_cutoff = max(min(cutoffs.values()), 1e-6)
        
        # Sampling Calculations
        R_prime = (2 * min_cutoff * N) / Dr
        sampling_ratio = min(R_prime, 1.0)
        r_multiplier = max(1, math.ceil(R_prime))

        spaces = {item: math.ceil(f_c / min_cutoff) * r_multiplier for item, f_c in cutoffs.items()}

        print(f"{str(eps)+'%':<10} | {sampling_ratio * 100:<12.2f} | {spaces['queue_occ']:<12} | {spaces['hop_lat']:<12} | {spaces['egress_ts']:<12}")

if __name__ == "__main__":
    # You can now safely pass all log files; it will isolate the bottleneck node automatically.
    trace_files = ["BMv2/example/packets/result_h8.txt", "BMv2/example/packets/result_h5.txt", "BMv2/example/packets/result_h6.txt", "BMv2/example/packets/result_h7.txt"]
    main(trace_files)