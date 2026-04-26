import json
import glob
import numpy as np
import matplotlib.pyplot as plt

def get_cdf(data):
    """Helper function to calculate the CDF of a dataset."""
    sorted_data = np.sort(data)
    p = 1. * np.arange(len(data)) / (len(data) - 1)
    return sorted_data, p

def main():
    # Automatically grab all receiver log files
    # Adjust this path if your files are located elsewhere
    files = glob.glob("BMv2/example/packets/result_h*.txt")
    
    if not files:
        print("No result_*.txt files found. Please check the path.")
        return

    item_mapping = {
        'queue_occ': 'queue_metadata',
        'hop_lat': 'hop_metadata',
        'egress_ts': 'egress_metadata'
    }
    
    # Data structure: { 'queue_occ': { 1: [val1, val2], 2: [val1, val2] }, ... }
    metrics = {k: {} for k in item_mapping.keys()}
    
    print(f"Parsing {len(files)} log files...")
    
    for fpath in files:
        with open(fpath, 'r') as f:
            for line in f:
                try:
                    pkt = json.loads(line.strip())
                    if "event" in pkt: 
                        continue
                    
                    for item, meta_key in item_mapping.items():
                        if meta_key in pkt:
                            for entry in pkt[meta_key]:
                                sw_id = entry.get("switch_id")
                                val = entry.get(item)
                                if sw_id is not None and val is not None:
                                    if sw_id not in metrics[item]:
                                        metrics[item][sw_id] = []
                                    metrics[item][sw_id].append(val)
                except json.JSONDecodeError:
                    continue
                    
    # -----------------------------
    # Plotting
    # -----------------------------
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    titles = {
        'queue_occ': 'Queue Occupancy Distribution',
        'hop_lat': 'Hop Latency Distribution',
        'egress_ts': 'Egress Timestamp Distribution'
    }
    
    for ax, item in zip(axes, item_mapping.keys()):
        ax.set_title(titles[item], fontsize=14)
        ax.set_xlabel("Value", fontsize=12)
        ax.set_ylabel("CDF", fontsize=12)
        ax.grid(True, which="both", ls="--", alpha=0.7)
        
        has_data = False
        
        # Sort switch IDs so the legend is in order
        for sw_id, vals in sorted(metrics[item].items()):
            if len(vals) > 0:
                has_data = True
                x, y = get_cdf(vals)
                ax.plot(x, y, label=f"Switch {sw_id}", linewidth=2)
        
        if has_data:
            ax.legend(loc='lower right')
            
        # Optional: For queue_occ, force the X-axis to start at 0 to clearly see if it's flatlining
        if item == 'queue_occ' and has_data:
            ax.set_xlim(left=0)

    plt.suptitle("FAT-INT Telemetry Distribution Across All Switches", fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig("telemetry_distribution.png", dpi=300)
    print("Graph saved as 'telemetry_distribution.png'")
    plt.show()

if __name__ == "__main__":
    main()