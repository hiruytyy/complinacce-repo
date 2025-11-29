#!/usr/bin/env python3
import json
import sys
import boto3
import os

def analyze_with_ai(failure):
    """Send violation to Bedrock for AI analysis"""
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    model_id = os.environ.get('BEDROCK_MODEL_ID', 'amazon.nova-pro-v1:0')
    max_tokens = int(os.environ.get('BEDROCK_MAX_TOKENS', '1500'))
    temperature = float(os.environ.get('BEDROCK_TEMPERATURE', '0.3'))
    
    prompt = f"""You are a CMMC compliance expert. Analyze this Terraform violation and provide:
1. Clear explanation of why this violates CMMC
2. Which CMMC practice(s) it violates
3. Exact Terraform code to fix it
4. Severity level (CRITICAL/HIGH/MEDIUM/LOW)

Violation Details:
- Check: {failure.get('check_name', 'Unknown')}
- Resource: {failure.get('resource', 'Unknown')}
- File: {failure.get('file_path', 'Unknown')}

Provide a concise, actionable response with the fix code."""

    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "system": [{"text": "You are a CMMC (Cybersecurity Maturity Model Certification) compliance expert specializing in infrastructure security and Terraform. Your role is to analyze security violations, explain CMMC requirements, and provide actionable Terraform code fixes."}],
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature
                }
            })
        )
        
        result = json.loads(response['body'].read())
        return result['output']['message']['content'][0]['text']
    except Exception as e:
        print(f"Warning: AI analysis failed: {e}")
        return f"Check failed: {failure.get('check_name', 'Unknown')}"

def send_notification(summary, details):
    """Send SNS notification"""
    try:
        sns = boto3.client('sns', region_name='us-east-1')
        topic_arn = os.environ.get('SNS_TOPIC_ARN')
        
        if not topic_arn:
            print("Warning: SNS_TOPIC_ARN not set, skipping notification")
            return
            
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
    print("Analyzing violations with Nova Pro AI...\n")
    
    report_lines = []
    report_lines.append("CMMC COMPLIANCE VIOLATIONS REPORT")
    report_lines.append("=" * 70)
    report_lines.append(f"Total Violations: {len(failed_checks)}\n")
    
    for idx, failure in enumerate(failed_checks, 1):
        print(f"Violation {idx}/{len(failed_checks)}:")
        print(f"  Resource: {failure.get('resource', 'Unknown')}")
        print(f"  Check: {failure.get('check_name', 'Unknown')}")
        print(f"  File: {failure.get('file_path', 'Unknown')}")
        
        # Get AI analysis with fix suggestions
        ai_analysis = analyze_with_ai(failure)
        
        print(f"\n{ai_analysis}\n")
        print("-" * 70 + "\n")
        
        report_lines.append(f"\nVIOLATION {idx}:")
        report_lines.append(f"Resource: {failure.get('resource', 'Unknown')}")
        report_lines.append(f"File: {failure.get('file_path', 'Unknown')}")
        report_lines.append(f"\n{ai_analysis}")
        report_lines.append("-" * 70)
    
    # Save report
    report_content = "\n".join(report_lines)
    with open('compliance-report.txt', 'w') as f:
        f.write(report_content)
    
    # Send notification
    summary = f"❌ CMMC: {len(failed_checks)} violation(s) - AI fixes provided"
    send_notification(summary, report_content[:1000])
    
    print(f"\n{'='*70}")
    print("PIPELINE STATUS: FAILED")
    print(f"{'='*70}")
    print(f"\n❌ Deployment BLOCKED due to {len(failed_checks)} CMMC violation(s)")
    print("Check email for AI-powered fix suggestions.\n")
    
    sys.exit(1)

if __name__ == "__main__":
    main()
