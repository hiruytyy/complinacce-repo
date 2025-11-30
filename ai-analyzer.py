#!/usr/bin/env python3
import json
import sys
import boto3
import os

def analyze_with_ai(finding):
    """Send violation to Bedrock for AI analysis"""
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    model_id = os.environ.get('BEDROCK_MODEL_ID', 'amazon.nova-pro-v1:0')
    max_tokens = int(os.environ.get('BEDROCK_MAX_TOKENS', '1500'))
    temperature = float(os.environ.get('BEDROCK_TEMPERATURE', '0.3'))
    
    # Extract OCSF fields
    metadata = finding.get('metadata', {})
    finding_info = finding.get('finding_info', {})
    resources = finding.get('resources', [{}])[0]
    cloud = finding.get('cloud', {})
    
    check_id = metadata.get('product', {}).get('feature', {}).get('uid', 'Unknown')
    check_title = finding.get('message', 'Unknown')
    resource_uid = resources.get('uid', 'Unknown')
    region = cloud.get('region', 'N/A')
    severity = finding.get('severity', 'Unknown')
    
    prompt = f"""Analyze this AWS security violation and provide NIST 800-53 compliant fixes.

VIOLATION DETAILS:
- Check ID: {check_id}
- Check: {check_title}
- Resource: {resource_uid}
- Region: {region}
- Severity: {severity}

PROVIDE YOUR RESPONSE IN THIS EXACT FORMAT:

## 1. EXPLANATION
[Explain why this violates NIST 800-53 and which specific controls are violated]

## 2. FAILED RESOURCES
[List the specific AWS resources that failed this check]

## 3. TERRAFORM FIX CODE
[Provide complete, working, copy-paste ready Terraform code to resolve this violation]

Focus on actionable fixes with production-ready Terraform code."""

    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "system": [{"text": "You are a NIST 800-53 compliance expert specializing in AWS security and Terraform."}],
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
        return f"Check failed: {check_title}"

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
            Message=details[:262000]  # SNS max is 256KB
        )
        print(f"✓ Notification sent to SNS")
    except Exception as e:
        print(f"Warning: Notification failed: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python ai-analyzer.py <prowler-output.json>")
        sys.exit(1)
    
    results_file = sys.argv[1]
    
    try:
        with open(results_file, 'r') as f:
            prowler_results = json.load(f)
    except Exception as e:
        print(f"Error reading results: {e}")
        sys.exit(1)
    
    # OCSF format: findings array
    all_findings = prowler_results.get('findings', []) if isinstance(prowler_results, dict) else []
    
    failed_checks = [f for f in all_findings if f.get('status_id') == 2]  # OCSF: 2 = FAIL
    passed_checks = [f for f in all_findings if f.get('status_id') == 1]  # OCSF: 1 = PASS
    
    total_checks = len(failed_checks) + len(passed_checks)
    
    print(f"\n{'='*70}")
    print(f"NIST 800-53 COMPLIANCE SCAN RESULTS")
    print(f"{'='*70}")
    print(f"Total Checks: {total_checks}")
    print(f"✓ Passed: {len(passed_checks)}")
    print(f"✗ Failed: {len(failed_checks)}")
    print(f"{'='*70}\n")
    
    if len(failed_checks) == 0:
        print("✓ All NIST 800-53 compliance checks passed!")
        print("Deployment is allowed to proceed.\n")
        
        summary = f"✅ NIST 800-53 Compliance: All {total_checks} checks passed!"
        details = f"""NIST 800-53 COMPLIANCE SCAN - SUCCESS

Total Checks Run: {total_checks}
Passed: {len(passed_checks)}
Failed: 0

Status: DEPLOYMENT APPROVED
All NIST 800-53 compliance requirements met.
"""
        send_notification(summary, details)
        sys.exit(0)
    
    print(f"❌ {len(failed_checks)} NIST 800-53 violation(s) detected\n")
    print("Analyzing violations with Nova Pro AI...\n")
    
    report_lines = []
    report_lines.append("NIST 800-53 COMPLIANCE VIOLATIONS REPORT")
    report_lines.append("=" * 70)
    report_lines.append(f"Total Violations: {len(failed_checks)}\n")
    
    for idx, finding in enumerate(failed_checks, 1):
        metadata = finding.get('metadata', {})
        resources = finding.get('resources', [{}])[0]
        
        print(f"Violation {idx}/{len(failed_checks)}:")
        print(f"  Resource: {resources.get('uid', 'Unknown')}")
        print(f"  Check: {finding.get('message', 'Unknown')}")
        
        # Get AI analysis with fix suggestions
        ai_analysis = analyze_with_ai(finding)
        
        print(f"\n{ai_analysis}\n")
        print("-" * 70 + "\n")
        
        report_lines.append(f"\nVIOLATION {idx}:")
        report_lines.append(f"Resource: {resources.get('uid', 'Unknown')}")
        report_lines.append(f"Check: {finding.get('message', 'Unknown')}")
        report_lines.append(f"\n{ai_analysis}")
        report_lines.append("-" * 70)
    
    # Save report
    report_content = "\n".join(report_lines)
    with open('compliance-report.txt', 'w') as f:
        f.write(report_content)
    
    # Save full report to S3
    try:
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket = os.environ.get('ARTIFACT_BUCKET')
        if bucket:
            s3.put_object(
                Bucket=bucket,
                Key='compliance-reports/latest-report.txt',
                Body=report_content.encode('utf-8'),
                ContentType='text/plain'
            )
            print(f"✓ Full report saved to S3: s3://{bucket}/compliance-reports/latest-report.txt")
    except Exception as e:
        print(f"Warning: Failed to save report to S3: {e}")
    
    # Send notification with full content (SNS supports up to 256KB)
    summary = f"❌ NIST 800-53: {len(failed_checks)} violation(s) - AI fixes provided"
    notification_message = f"""{report_content}

---
Full report also available in S3: s3://{os.environ.get('ARTIFACT_BUCKET', 'N/A')}/compliance-reports/latest-report.txt
"""
    send_notification(summary, notification_message[:262000])  # SNS limit is 256KB
    
    print(f"\n{'='*70}")
    print("PIPELINE STATUS: FAILED")
    print(f"{'='*70}")
    print(f"\n❌ Deployment BLOCKED due to {len(failed_checks)} NIST 800-53 violation(s)")
    print("Check email for AI-powered fix suggestions.\n")
    
    sys.exit(1)

if __name__ == "__main__":
    main()
