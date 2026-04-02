#!/usr/bin/env python3
import os
import json
import math
import argparse
from collections import defaultdict


# =====================================================================================
# Basic Math Helpers
# =====================================================================================

def safe_mean(values):
    return sum(values) / len(values) if values else 0.0


def rmse(truth, pred):
    if len(truth) == 0 or len(pred) == 0:
        return None
    if len(truth) != len(pred):
        raise ValueError(f"RMSE length mismatch: {len(truth)} vs {len(pred)}")
    mse = sum((t - p) ** 2 for t, p in zip(truth, pred)) / len(truth)
    return math.sqrt(mse)


def nrmse(truth, pred, method="mean"):
    if len(truth) == 0 or len(pred) == 0:
        return None

    r = rmse(truth, pred)
    if r is None:
        return None

    if method == "mean":
        denom = safe_mean(truth)
    elif method == "range":
        denom = max(truth) - min(truth) if truth else 0
    else:
        raise ValueError("method must be 'mean' or 'range'")

    if denom == 0:
        return None

    return r / denom


# =====================================================================================
# Load Receiver Logs
# =====================================================================================

def load_receiver_log(filepath):
    records = []

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except:
                continue

            if isinstance(obj, dict) and obj.get("event") in ["receiver_started", "receiver_stopped"]:
                continue

            if isinstance(obj, dict) and "flow_id" in obj:
                records.append(obj)

    return records


def load_all_records(folder, prefix, receivers):
    all_records = []

    for r in receivers:
        fname = os.path.join(folder, f"{prefix}_{r}.txt")
        if not os.path.exists(fname):
            print(f"[WARN] Missing file: {fname}")
            continue

        print(f"[INFO] Loading {fname}")
        recs = load_receiver_log(fname)
        all_records.extend(recs)

    return all_records


# =====================================================================================
# Build Comparable Series
# =====================================================================================

def extract_metric_series(records, metric_type):
    """
    Builds:
        key   -> (flow_id, switch_id, packet_index_within_flow)
        value -> telemetry value

    metric_type:
        - "queue"
        - "hop"
        - "egress"
    """

    flow_pkt_counter = defaultdict(int)
    series = {}

    for rec in records:
        flow_id = rec["flow_id"]
        pkt_idx = flow_pkt_counter[flow_id]
        flow_pkt_counter[flow_id] += 1

        if metric_type == "queue":
            entries = rec.get("queue_metadata", [])
            for item in entries:
                switch_id = item.get("switch_id")
                value = item.get("queue_occ")
                if switch_id is not None and value is not None:
                    key = (flow_id, switch_id, pkt_idx)
                    series[key] = value

        elif metric_type == "hop":
            entries = rec.get("hop_metadata", [])
            for item in entries:
                switch_id = item.get("switch_id")
                value = item.get("hop_lat")
                if switch_id is not None and value is not None:
                    key = (flow_id, switch_id, pkt_idx)
                    series[key] = value

        elif metric_type == "egress":
            entries = rec.get("egress_metadata", [])
            for item in entries:
                switch_id = item.get("switch_id")
                value = item.get("egress_ts")
                if switch_id is not None and value is not None:
                    key = (flow_id, switch_id, pkt_idx)
                    series[key] = value

        else:
            raise ValueError("metric_type must be queue / hop / egress")

    return series


# =====================================================================================
# Coverage + Matched NRMSE
# =====================================================================================

def compare_matched(full_series, fat_series, normalize="mean"):
    common_keys = sorted(set(full_series.keys()) & set(fat_series.keys()))

    truth = [full_series[k] for k in common_keys]
    pred  = [fat_series[k] for k in common_keys]

    if len(full_series) == 0:
        coverage = 0.0
    else:
        coverage = len(common_keys) / len(full_series)

    if len(common_keys) == 0:
        return {
            "matched_count": 0,
            "coverage": coverage,
            "rmse": None,
            "nrmse": None
        }

    return {
        "matched_count": len(common_keys),
        "coverage": coverage,
        "rmse": rmse(truth, pred),
        "nrmse": nrmse(truth, pred, method=normalize)
    }


# =====================================================================================
# Forward-Fill Reconstruction
# =====================================================================================

def build_grouped_series(series):
    """
    Convert:
        (flow_id, switch_id, pkt_idx) -> value

    into:
        (flow_id, switch_id) -> {pkt_idx: value}
    """
    grouped = defaultdict(dict)
    for (flow_id, switch_id, pkt_idx), value in series.items():
        grouped[(flow_id, switch_id)][pkt_idx] = value
    return grouped


def forward_fill_compare(full_series, fat_series, normalize="mean"):
    """
    Reconstruct missing FAT-INT values using forward fill (LOCF),
    then compare against Full INT over all packet indices.
    """

    full_grouped = build_grouped_series(full_series)
    fat_grouped = build_grouped_series(fat_series)

    all_groups = sorted(set(full_grouped.keys()))

    truth_all = []
    pred_all = []

    for group in all_groups:
        full_pkt_map = full_grouped[group]
        fat_pkt_map = fat_grouped.get(group, {})

        if not full_pkt_map:
            continue

        max_pkt_idx = max(full_pkt_map.keys())

        last_seen = None

        for pkt_idx in range(max_pkt_idx + 1):
            if pkt_idx not in full_pkt_map:
                continue

            truth_val = full_pkt_map[pkt_idx]

            if pkt_idx in fat_pkt_map:
                last_seen = fat_pkt_map[pkt_idx]
                pred_val = fat_pkt_map[pkt_idx]
            else:
                # Forward fill
                if last_seen is not None:
                    pred_val = last_seen
                else:
                    # If FAT-INT has never observed this group yet,
                    # skip until first available sample
                    continue

            truth_all.append(truth_val)
            pred_all.append(pred_val)

    if len(truth_all) == 0:
        return {
            "filled_count": 0,
            "rmse": None,
            "nrmse": None
        }

    return {
        "filled_count": len(truth_all),
        "rmse": rmse(truth_all, pred_all),
        "nrmse": nrmse(truth_all, pred_all, method=normalize)
    }


# =====================================================================================
# Per Metric Analysis
# =====================================================================================

def analyze_metric(full_records, fat_records, metric_type, normalize="mean"):
    full_series = extract_metric_series(full_records, metric_type)
    fat_series  = extract_metric_series(fat_records, metric_type)

    # --- ENHANCED DEBUG BLOCK ---
    full_keys_set = set(full_series.keys())
    fat_keys_set = set(fat_series.keys())
    
    common_keys = full_keys_set & fat_keys_set
    only_in_full = full_keys_set - fat_keys_set
    only_in_fat = fat_keys_set - full_keys_set

    print(f"\n[DEBUG] {metric_type.upper()} MATCHING ANALYSIS")
    print(f" -> Total Matched Keys : {len(common_keys)}")
    
    print(f" -> Keys ONLY in Full  : {len(only_in_full)}")
    if only_in_full:
        print(f"    Example orphans in Full: {list(only_in_full)[:3]}")
        
    print(f" -> Keys ONLY in FAT   : {len(only_in_fat)}")
    if only_in_fat:
        print(f"    Example orphans in FAT : {list(only_in_fat)[:3]}")
    # ----------------------------

    matched_result = compare_matched(full_series, fat_series, normalize=normalize)
    filled_result  = forward_fill_compare(full_series, fat_series, normalize=normalize)

    return {
        "full_samples": len(full_series),
        "fat_samples": len(fat_series),
        "matched": matched_result,
        "forward_fill": filled_result
    }


# =====================================================================================
# Pretty Printing
# =====================================================================================

def pretty_metric(name, result):
    print("=" * 90)
    print(f"{name}")
    print("=" * 90)
    print(f"Full INT samples         : {result['full_samples']}")
    print(f"FAT-INT samples          : {result['fat_samples']}")
    print(f"Coverage                 : {result['matched']['coverage']:.4f}")

    print("\n[Matched Samples Only]")
    print(f"Matched samples          : {result['matched']['matched_count']}")
    print(f"RMSE                     : {result['matched']['rmse']}")
    print(f"NRMSE                    : {result['matched']['nrmse']}")

    print("\n[Forward-Filled Monitoring Error]")
    print(f"Filled comparison points : {result['forward_fill']['filled_count']}")
    print(f"RMSE                     : {result['forward_fill']['rmse']}")
    print(f"NRMSE                    : {result['forward_fill']['nrmse']}")
    print()


# =====================================================================================
# Main
# =====================================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=str, required=True,
                        help="Folder containing receiver result files")
    parser.add_argument("--full_prefix", type=str, default="result_fullINT",
                        help="Prefix for Full INT files")
    parser.add_argument("--fat_prefix", type=str, default="result_fatINT",
                        help="Prefix for FAT-INT files")
    parser.add_argument("--receivers", nargs="+", default=["h5", "h6", "h7", "h8"],
                        help="Receiver host names")
    parser.add_argument("--normalize", type=str, default="mean", choices=["mean", "range"],
                        help="NRMSE normalization method")
    args = parser.parse_args()

    print("=" * 90)
    print("Loading Full INT records...")
    full_records = load_all_records(args.folder, args.full_prefix, args.receivers)

    print("\nLoading FAT-INT records...")
    fat_records = load_all_records(args.folder, args.fat_prefix, args.receivers)

    print("\n" + "=" * 90)
    print(f"Total Full INT packet records : {len(full_records)}")
    print(f"Total FAT-INT packet records  : {len(fat_records)}")
    print("=" * 90)

    queue_result  = analyze_metric(full_records, fat_records, "queue",  normalize=args.normalize)
    hop_result    = analyze_metric(full_records, fat_records, "hop",    normalize=args.normalize)
    egress_result = analyze_metric(full_records, fat_records, "egress", normalize=args.normalize)

    print("\n\nFINAL RESULTS\n")
    pretty_metric("Queue Occupancy", queue_result)
    pretty_metric("Hop Latency", hop_result)
    pretty_metric("Egress Timestamp", egress_result)

    summary = {
        "queue": queue_result,
        "hop": hop_result,
        "egress": egress_result,
        "normalize_method": args.normalize
    }

    print("=" * 90)
    print("JSON SUMMARY")
    print("=" * 90)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()