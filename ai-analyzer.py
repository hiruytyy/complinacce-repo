#!/usr/bin/env python3
import json
import sys
import boto3
import os

def send_notification(summary, details):
    """Send SNS notification"""
    try:
        sns = boto3.client('sns', region_name='us-east-1')
        topic_arn = "arn:aws:sns:us-east-1:645275603244:cmmc-compliance-alerts"
        
        sns.publish(
            TopicArn=topic_arn,
            Subject=summary[:100],
            Message=details[:1000]
        )
        print(f"✓ Notification sent to SNS")
    except Exception as e:
        print(f"Warning: Notification failed: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python ai-analyzer.py <checkov-output.json>")
        sys.exit(1)
    
    results_file = sys.argv[1]
    
    try:
        with open(results_file, 'r') as f:
            checkov_results = json.load(f)
    except Exception as e:
        print(f"Error reading results: {e}")
        sys.exit(1)
    
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
        print("Deployment is allowed to proceed.\n")
        
        # Send success notification
        summary = f"✅ CMMC Compliance: All {total_checks} checks passed!"
        details = f"""CMMC COMPLIANCE SCAN - SUCCESS

Total Checks Run: {total_checks}
Passed: {len(passed_checks)}
Failed: 0

Status: DEPLOYMENT APPROVED
All CMMC compliance requirements met.
"""
        send_notification(summary, details)
        sys.exit(0)
    
    print(f"❌ {len(failed_checks)} CMMC violation(s) detected\n")
    
    report_lines = []
    for idx, failure in enumerate(failed_checks, 1):
        print(f"Violation {idx}:")
        print(f"  Resource: {failure.get('resource', 'Unknown')}")
        print(f"  Check: {failure.get('check_name', 'Unknown')}")
        print(f"  File: {failure.get('file_path', 'Unknown')}")
        print(f"  Guideline: {failure.get('guideline', 'N/A')}\n")
        
        report_lines.append(f"Violation {idx}: {failure.get('check_name', 'Unknown')}")
        report_lines.append(f"  Resource: {failure.get('resource', 'Unknown')}")
        report_lines.append(f"  File: {failure.get('file_path', 'Unknown')}\n")
    
    # Send notification
    summary = f"❌ CMMC Compliance: {len(failed_checks)} violation(s) detected"
    details = f"""CMMC COMPLIANCE SCAN - FAILED

Total Checks: {total_checks}
Passed: {len(passed_checks)}
Failed: {len(failed_checks)}

VIOLATIONS:
{chr(10).join(report_lines[:500])}

Status: DEPLOYMENT BLOCKED
"""
    send_notification(summary, details)
    
    print(f"\n{'='*70}")
    print("PIPELINE STATUS: FAILED")
    print(f"{'='*70}")
    print(f"\n❌ Deployment BLOCKED due to {len(failed_checks)} CMMC violation(s)\n")
    
    sys.exit(1)

if __name__ == "__main__":
    main()
