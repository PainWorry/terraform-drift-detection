#!/usr/bin/env python3
"""
Terraform Drift Automation - Local Portfolio Demonstration Runner
Simulates end-to-end drift detection, AST JSON evaluation, and ClickUp alert payload generation.
Zero AWS credentials required for offline demonstration and portfolio screenshot capture.
"""

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone

# ANSI Terminal Styling
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

MOCK_PLAN_JSON = {
    "format_version": "1.2",
    "terraform_version": "1.10.0",
    "resource_changes": [
        {
            "address": "aws_security_group.drift_canary",
            "type": "aws_security_group",
            "name": "drift_canary",
            "provider_name": "registry.terraform.io/hashicorp/aws",
            "change": {
                "actions": ["update"],
                "before": {
                    "arn": "arn:aws:ec2:ap-southeast-1:123456789012:security-group/sg-0a8b7c6d5e4f3210a",
                    "id": "sg-0a8b7c6d5e4f3210a",
                    "name": "onelink-staging-drift-canary-sg",
                    "description": "Security group for live drift detection canary testing",
                    "vpc_id": "vpc-091a2b3c4d5e6f780",
                    "ingress": [
                        {
                            "cidr_blocks": ["10.0.0.0/8"],
                            "description": "Managed by Terraform - Baseline HTTPS",
                            "from_port": 443,
                            "protocol": "tcp",
                            "to_port": 443,
                            "ipv6_cidr_blocks": [],
                            "prefix_list_ids": [],
                            "security_groups": [],
                            "self": False
                        },
                        {
                            "cidr_blocks": ["0.0.0.0/0"],
                            "description": "OUT-OF-BAND CLICKOPS: Urgent SSH Debugging",
                            "from_port": 22,
                            "protocol": "tcp",
                            "to_port": 22,
                            "ipv6_cidr_blocks": [],
                            "prefix_list_ids": [],
                            "security_groups": [],
                            "self": False
                        }
                    ],
                    "tags": {
                        "Environment": "staging",
                        "ManagedBy": "Terraform",
                        "Purpose": "DriftCanary"
                    }
                },
                "after": {
                    "arn": "arn:aws:ec2:ap-southeast-1:123456789012:security-group/sg-0a8b7c6d5e4f3210a",
                    "id": "sg-0a8b7c6d5e4f3210a",
                    "name": "onelink-staging-drift-canary-sg",
                    "description": "Security group for live drift detection canary testing",
                    "vpc_id": "vpc-091a2b3c4d5e6f780",
                    "ingress": [
                        {
                            "cidr_blocks": ["10.0.0.0/8"],
                            "description": "Managed by Terraform - Baseline HTTPS",
                            "from_port": 443,
                            "protocol": "tcp",
                            "to_port": 443,
                            "ipv6_cidr_blocks": [],
                            "prefix_list_ids": [],
                            "security_groups": [],
                            "self": False
                        }
                    ],
                    "tags": {
                        "Environment": "staging",
                        "ManagedBy": "Terraform",
                        "Purpose": "DriftCanary"
                    }
                }
            }
        }
    ]
}

MOCK_CLI_DIFF = """Note: Objects have changed outside of Terraform

Terraform detected the following changes made outside of Terraform since the
last "terraform apply" which may have affected this plan:

  # aws_security_group.drift_canary has been modified outside of Terraform
  ~ resource "aws_security_group" "drift_canary" {
        id                     = "sg-0a8b7c6d5e4f3210a"
        name                   = "onelink-staging-drift-canary-sg"
      ~ ingress                = [
            {
                cidr_blocks      = [
                    "10.0.0.0/8",
                ]
                description      = "Managed by Terraform - Baseline HTTPS"
                from_port        = 443
                protocol         = "tcp"
                to_port          = 443
            },
          - {
              - cidr_blocks      = [
                  - "0.0.0.0/0",
                ]
              - description      = "OUT-OF-BAND CLICKOPS: Urgent SSH Debugging"
              - from_port        = 22
              - protocol         = "tcp"
              - to_port          = 22
            },
        ]
        # (4 unchanged attributes hidden)
    }

Unless you have made equivalent changes to your configuration, or ignored the
relevant attributes using "ignore_changes", the following plan will bring the
real-world infrastructure back into sync with your Terraform configuration.

Terraform will perform the following actions:

  # aws_security_group.drift_canary will be updated in-place
  ~ resource "aws_security_group" "drift_canary" {
        id   = "sg-0a8b7c6d5e4f3210a"
        name = "onelink-staging-drift-canary-sg"
      ~ ingress = [
          - {
              - cidr_blocks = ["0.0.0.0/0"]
              - from_port   = 22
              - protocol    = "tcp"
              - to_port     = 22
            },
            # (1 unchanged block hidden)
        ]
    }

Plan: 0 to add, 1 to change, 0 to destroy."""


def print_step(step_num: int, total_steps: int, title: str):
    print(f"\n{BOLD}{CYAN}[{step_num}/{total_steps}]{RESET} {BOLD}{title}{RESET}")


def run_demo():
    print(f"{BOLD}{BLUE}======================================================================{RESET}")
    print(f"{BOLD}{BLUE}  TERRAFORM DRIFT DETECTION & AUTOMATION WATCHDOG - DEMO RUNNER     {RESET}")
    print(f"{BOLD}{BLUE}  Environment: environments/staging | Region: ap-southeast-1        {RESET}")
    print(f"{BOLD}{BLUE}  Operator:    Herren Karsemsak (Cloud Engineer)                     {RESET}")
    print(f"{BOLD}{BLUE}======================================================================{RESET}")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    plan_json_path = os.path.join(data_dir, "mock_drift_plan.json")
    plan_txt_path = os.path.join(data_dir, "mock_drift_plan.txt")

    with open(plan_json_path, "w", encoding="utf-8") as f:
        json.dump(MOCK_PLAN_JSON, f, indent=2)

    with open(plan_txt_path, "w", encoding="utf-8") as f:
        f.write(MOCK_CLI_DIFF)

    time.sleep(0.4)
    print_step(1, 5, "Authenticating to AWS via GitHub OIDC & Setting Up S3 Backend")
    print(f"  {GREEN}✓{RESET} OIDC Token exchanged: arn:aws:iam::123456789012:role/GitHubActions-DriftScanner")
    print(f"  {GREEN}✓{RESET} S3 Remote Backend: onelink-terraform-state-staging-ap-southeast-1")
    print(f"  {GREEN}✓{RESET} Terraform 1.10 Native Lockfile: staging/drift-canary/terraform.tfstate.tflock")

    time.sleep(0.5)
    print_step(2, 5, "Executing Drift Detection (terraform plan -detailed-exitcode -parallelism=2)")
    print(f"  AWS Token Bucket Pacing: Rate = 20 req/s, Parallelism = 2 (Safe Threshold)")
    time.sleep(0.6)
    print(f"  {YELLOW}⚠️  DRIFT DETECTED: Terraform plan returned Exit Code 2 (Changes Present){RESET}")

    time.sleep(0.4)
    print_step(3, 5, "Parsing Plan AST & Evaluating Break-Glass Quarantine Policy")
    drifted_resources = []
    for rc in MOCK_PLAN_JSON["resource_changes"]:
        addr = rc["address"]
        tags = rc["change"]["before"].get("tags", {})
        is_exempt = str(tags.get("DriftExempt", "")).lower() == "true"
        print(f"  - Resource: {BOLD}{addr}{RESET}")
        print(f"    Action:   {rc['change']['actions']}")
        print(f"    Tags:     {tags}")
        print(f"    Quarantine Check: DriftExempt={is_exempt} -> {RED}VIOLATION (Alert Required){RESET}")
        drifted_resources.append(addr)

    time.sleep(0.4)
    print_step(4, 5, "Computing Cryptographic Idempotency Hash for Deduplication")
    canonical_payload = "environments/staging:" + ",".join(sorted(drifted_resources))
    drift_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()[:16]
    idempotency_tag = f"drift-hash-{drift_hash}"
    print(f"  Payload:         {canonical_payload}")
    print(f"  SHA256 Hash:     {drift_hash}")
    print(f"  Idempotency Key: {BOLD}{GREEN}{idempotency_tag}{RESET}")

    time.sleep(0.4)
    print_step(5, 5, "Generating ClickUp Urgent Incident Ticket & Runbook")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    task_id = "8694k2m9z"
    task_url = f"https://app.clickup.com/t/{task_id}"

    print(f"\n{BOLD}{GREEN}=== CLICKUP TASK DISPATCHED SUCCESSFULLY ==={RESET}")
    print(f"  Status:       {BOLD}CREATED (Task #{task_id}){RESET}")
    print(f"  Priority:     {BOLD}{RED}URGENT (P1){RESET}")
    print(f"  Assignee:     Herren Karsemsak (Cloud Engineer)")
    print(f"  Task Title:   [DRIFT ALERT] Infrastructure Drift Detected - environments/staging")
    print(f"  Tags:         ['terraform', 'drift-detection', 'staging', '{idempotency_tag}']")
    print(f"  Deep Link:    {BLUE}{task_url}{RESET}")
    print(f"  AWS SG URL:   {BLUE}https://ap-southeast-1.console.aws.amazon.com/ec2/home?region=ap-southeast-1#SecurityGroup:groupId=sg-0a8b7c6d5e4f3210a{RESET}")
    print(f"  Timestamp:    {now_str}")
    print(f"{BOLD}{GREEN}============================================={RESET}\n")

    print(f"{BOLD}Demo artifacts written to disk:{RESET}")
    print(f"  - Plan JSON: {plan_json_path}")
    print(f"  - Plan Diff: {plan_txt_path}\n")
    print(f"{GREEN}To view or capture screenshots, open the portfolio showcase HTML deliverable.{RESET}")


if __name__ == "__main__":
    run_demo()
