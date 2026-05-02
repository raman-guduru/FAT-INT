import csv
import os

def main():
    # ==============================================================
    # 1. DEFINE WHAT YOU ARE LOOKING FOR HERE
    # ==============================================================
    CSV_FILE = "sweep_results/consolidated_results.csv"

    TARGET_ERROR = 3.0           # The fixed Error Threshold you are looking at (e.g., 2.0%)
    
    # Define the acceptable bounds for the Sampling Ratio
    TARGET_RATIO_MIN = 40.0      # Minimum acceptable sampling ratio (%)
    TARGET_RATIO_MAX = 50.0      # Maximum acceptable sampling ratio (%)
    
    # Define the EXACT Sampling Spaces you want to find
    TARGET_S_QUEUE  = 5
    TARGET_S_HOP    = 3
    TARGET_S_EGRESS = 1
    # ==============================================================

    if not os.path.exists(CSV_FILE):
        print(f"[!] Error: Could not find {CSV_FILE}.")
        print("Make sure you have run auto_sweep.py first to generate the data.")
        return

    print("=========================================================")
    print(f" FAT-INT DATASET SEARCH")
    print(f" Searching in : {CSV_FILE}")
    print(f" Hunting for  : S_Queue={TARGET_S_QUEUE} | S_Hop={TARGET_S_HOP} | S_Egress={TARGET_S_EGRESS}")
    print(f" Ratio Bounds : {TARGET_RATIO_MIN}% - {TARGET_RATIO_MAX}%")
    print(f" At Error     : {TARGET_ERROR}%")
    print("=========================================================\n")

    matches = []

    # Read the CSV and scan for matches
    with open(CSV_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Extract values from the current row
                err = float(row['Error_Threshold_pct'])
                ratio = float(row['Sampling_Ratio_pct'])
                sq = int(row['S_Queue'])
                sh = int(row['S_Hop'])
                se = int(row['S_Egress'])
                rate = float(row['Rate_flows_sec'])
                duration = float(row['Duration_sec'])

                # Check if this row perfectly matches all of our conditions
                if (err == TARGET_ERROR and 
                    TARGET_RATIO_MIN <= ratio <= TARGET_RATIO_MAX and 
                    sq == TARGET_S_QUEUE and 
                    sh == TARGET_S_HOP and 
                    se == TARGET_S_EGRESS):
                    
                    matches.append((rate, duration, ratio))
            except ValueError:
                # Skip any malformed rows or headers safely
                continue

    # Display the results
    if matches:
        print("★ MATCHING CONFIGURATIONS FOUND! ★")
        print("-" * 65)
        for rate, duration, ratio in matches:
            print(f" -> Flow Rate: {rate} flows/sec | Duration: {duration}s  (Yields Ratio: {ratio}%)")
        print("-" * 65 + "\n")
    else:
        print("[!] No configurations in your dataset match those exact parameters.")
        print("Try widening your Sampling Ratio bounds, or check if those exact spaces exist in your CSV.")

if __name__ == "__main__":
    main()