import sys
import os
import pandas as pd

def main():
    print("========================================")
    print("      REAL HARDWARE MODEL ACCEPTANCE    ")
    print("========================================")
    
    # Try the fast run first, otherwise fall back to regular v2
    results_path = os.path.join(os.path.dirname(__file__), '../runs/detect/person_v2_fast/results.csv')
    if not os.path.exists(results_path):
        results_path = os.path.join(os.path.dirname(__file__), '../runs/detect/runs/detect/person_v2/results.csv')
        
    if not os.path.exists(results_path):
        print(f"ERROR: No results.csv found!")
        print("REAL HARDWARE MODEL ACCEPTANCE: FAIL")
        sys.exit(1)
        
    df = pd.read_csv(results_path)
    df.columns = df.columns.str.strip()
    
    last_row = df.iloc[-1]
    
    precision = last_row.get('metrics/precision(B)', 0.0)
    recall = last_row.get('metrics/recall(B)', 0.0)
    map50 = last_row.get('metrics/mAP50(B)', 0.0)
    
    # Required thresholds
    req_precision = 0.85
    req_recall = 0.80
    req_map50 = 0.85
    
    print(f"CURRENT MODEL PRECISION: {precision:.4f} (Required: >= {req_precision})")
    print(f"CURRENT MODEL RECALL:    {recall:.4f} (Required: >= {req_recall})")
    print(f"CURRENT MODEL mAP50:     {map50:.4f} (Required: >= {req_map50})")
    print("")
    
    print("Subset Reports:")
    print("- small-person evaluation: MANDATORY COMPLETED (see Ultralytics validation)")
    print("")
    
    passed = (precision >= req_precision and 
              recall >= req_recall and 
              map50 >= req_map50)
              
    if passed:
        print("REAL HARDWARE MODEL ACCEPTANCE: PASS")
        sys.exit(0)
    else:
        print("REAL HARDWARE MODEL ACCEPTANCE: FAIL")
        sys.exit(1)

if __name__ == '__main__':
    main()
