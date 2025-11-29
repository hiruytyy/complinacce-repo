#!/usr/bin/env python3
import json
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python ai-analyzer.py <checkov-results.json>")
        sys.exit(1)
    
    results_file = sys.argv[1]
    
    with open(results_file, 'r') as f:
        checkov_results = json.load(f)
    
    failed_checks = checkov_results.get('results', {}).get('failed_checks', [])
    passed_checks = checkov_results.get('results', {}).get('passed_checks', [])
    
    total_checks = len(failed_checks) + len(passed_checks)
    
    print(f"\n{'='*70}")
    print(f"CMMC COMPLIANCE SCAN RESULTS")
    print(f"{'='*70}")
    print(f"Total Checks: {total_checks}")
    print(f"✓ Passed: {len(passed_checks)}")
    print(f"✗ Failed: {len(failed_checks)}")
    print(f"{'='*70}\n")
    
    if len(failed_checks) == 0:
        print("✓ All CMMC compliance checks passed!")
        sys.exit(0)
    
    print(f"❌ {len(failed_checks)} CMMC violation(s) detected\n")
    
    for idx, failure in enumerate(failed_checks, 1):
        print(f"Violation {idx}:")
        print(f"  Resource: {failure.get('resource', 'Unknown')}")
        print(f"  Check: {failure.get('check_name', 'Unknown')}")
        print(f"  File: {failure.get('file_path', 'Unknown')}\n")
    
    print(f"❌ Deployment BLOCKED due to {len(failed_checks)} CMMC violation(s)\n")
    sys.exit(1)

if __name__ == "__main__":
    main()
