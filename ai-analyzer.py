#!/usr/bin/env python3
import json
import sys
import boto3
import os

def analyze_with_ai(failure):
    """Send violation to Bedrock for AI analysis"""
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    prompt = f"""You are a CMMC compliance expert. Analyze this violation and provide:
1. Clear explanation of why this violates CMMC
2. Which CMMC practice(s) it violates
3. Terraform code to fix it
4. Severity level (CRITICAL/HIGH/MEDIUM/LOW)

Violation Details:
- Check: {failure.get('check_name', 'Unknown')}
- Resource: {failure.get('resource', 'Unknown')}
- File: {failure.get('file_path', 'Unknown')}
- Code Block:
{failure.get('code_block', 'N/A')}

Provide a concise, actionable response."""

    try:
        response = bedrock.invoke_model(
            modelId='amazon.nova-pro-v1:0',
            body=json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {
                    "max_new_tokens": 1500,
                    "temperature": 0.3
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
        
        if topic_arn:
            sns.publish(
                TopicArn=topic_arn,
                Subject='❌ CMMC Compliance Violation Detected',
                Message=f"{summary}\n\n{details}"
            )
    except Exception as e:
        print(f"Warning: Notification failed: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python ai-analyzer.py <checkov-results.json>")
        sys.exit(1)
    
    results_file = sys.argv[1]
    
    try:
        with open(results_file, 'r') as f:
            checkov_results = json.load(f)
    except Exception as e:
        print(f"Error reading results file: {e}")
        sys.exit(1)
    
    # Extract failed checks
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
        sys.exit(0)
    
    # Process failures with AI
    print(f"❌ {len(failed_checks)} CMMC violation(s) detected\n")
    print("Analyzing violations with AI...\n")
    
    report_lines = []
    report_lines.append("CMMC COMPLIANCE VIOLATIONS REPORT")
    report_lines.append("=" * 70)
    report_lines.append(f"Total Violations: {len(failed_checks)}\n")
    
    for idx, failure in enumerate(failed_checks, 1):
        print(f"Violation {idx}/{len(failed_checks)}:")
        print(f"  Resource: {failure.get('resource', 'Unknown')}")
        print(f"  Check: {failure.get('check_name', 'Unknown')}")
        print(f"  File: {failure.get('file_path', 'Unknown')}")
        
        # Get AI analysis
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
    summary = f"{len(failed_checks)} CMMC violation(s) detected in pipeline"
    send_notification(summary, report_content[:1000])
    
    print(f"\n{'='*70}")
    print("PIPELINE STATUS: FAILED")
    print(f"{'='*70}")
    print(f"\n❌ Deployment BLOCKED due to {len(failed_checks)} CMMC violation(s)")
    print("Fix the violations above and push again.\n")
    
    # Exit with failure code to block pipeline
    sys.exit(1)

if __name__ == "__main__":
    main()
