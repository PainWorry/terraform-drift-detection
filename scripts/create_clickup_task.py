import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone


def compute_drift_hash(env_name: str, resource_addresses: list[str]) -> str:
    """Compute deterministic SHA256 hash of drifted resource addresses for idempotency."""
    canonical_payload = f"{env_name}:" + ",".join(sorted(resource_addresses))
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()[:16]


def parse_plan_json(plan_json_path: str) -> tuple[list[dict], list[str], bool]:
    """Parse Terraform plan JSON output to detect drifted resources and evaluate DriftExempt tag quarantine."""
    if not plan_json_path or not os.path.exists(plan_json_path):
        return [], [], False

    try:
        with open(plan_json_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception as err:
        sys.stderr.write(f"[WARN] Failed to parse plan JSON: {err}\n")
        return [], [], False

    resource_changes = data.get("resource_changes", [])
    active_drifts = []
    quarantined_drifts = []

    for rc in resource_changes:
        actions = rc.get("change", {}).get("actions", [])
        if actions == ["no-op"] or not actions:
            continue

        address = rc.get("address", "unknown_resource")
        after_tags = rc.get("change", {}).get("after", {}).get("tags") or {}
        before_tags = rc.get("change", {}).get("before", {}).get("tags") or {}
        tags = {**before_tags, **after_tags}

        # Break-Glass Cryptographic Quarantine Check
        is_exempt = str(tags.get("DriftExempt", "")).lower() == "true"

        item = {
            "address": address,
            "type": rc.get("type", "unknown"),
            "actions": actions,
            "is_exempt": is_exempt,
        }

        if is_exempt:
            quarantined_drifts.append(item)
        else:
            active_drifts.append(item)

    all_exempt = len(quarantined_drifts) > 0 and len(active_drifts) == 0
    drift_addresses = [item["address"] for item in active_drifts]
    return active_drifts, drift_addresses, all_exempt


def find_existing_active_task(api_token: str, list_id: str, drift_hash: str) -> dict | None:
    """Query ClickUp for existing open tasks with matching drift-hash tag to prevent alert flooding."""
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task?include_closed=false&subtasks=false"
    headers = {
        "Authorization": api_token.strip(),
        "Accept": "application/json",
        "User-Agent": "Terraform-Drift-Detector/2.0",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            tasks = data.get("tasks", [])
            target_tag = f"drift-hash-{drift_hash}"
            for task in tasks:
                task_tags = [t.get("name") for t in task.get("tags", [])]
                if target_tag in task_tags:
                    return task
    except Exception as err:
        sys.stderr.write(f"[WARN] Failed to query existing ClickUp tasks for deduplication: {err}\n")
    return None


def add_comment_to_task(api_token: str, task_id: str, comment_text: str) -> bool:
    """Append comment to existing ClickUp task when drift persists across scheduled runs."""
    url = f"https://api.clickup.com/api/v2/task/{task_id}/comment"
    payload = json.dumps({"comment_text": comment_text, "notify_all": False}).encode("utf-8")
    headers = {
        "Authorization": api_token.strip(),
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 201)
    except Exception as err:
        sys.stderr.write(f"[WARN] Failed to add comment to ClickUp task {task_id}: {err}\n")
        return False


def extract_drift_summary(diff_text: str, max_chars: int = 12000) -> str:
    """Sanitize and format plan output for ClickUp task payload."""
    if not diff_text or not diff_text.strip():
        return "No plan diff captured."

    lines = diff_text.strip().splitlines()
    summary_lines = []
    capture = False

    for line in lines:
        if "Terraform will perform the following actions" in line or "Note: Objects have changed outside of Terraform" in line:
            capture = True
        if capture:
            summary_lines.append(line)

    formatted_summary = "\n".join(summary_lines) if summary_lines else diff_text.strip()
    if len(formatted_summary) > max_chars:
        return formatted_summary[:max_chars] + f"\n\n... [Diff truncated to {max_chars} characters for ClickUp payload]"

    return formatted_summary


def build_markdown_description(env_name: str, diff_summary: str, drift_hash: str, timestamp_str: str) -> str:
    """Generate structured markdown description with cryptographic idempotency key and CI runbook."""
    return f"""## Terraform Configuration Drift Detected

- **Environment**: `{env_name}`
- **Detected At**: `{timestamp_str}`
- **Idempotency Key**: `drift-hash-{drift_hash}`
- **Severity**: HIGH / URGENT (Unplanned infrastructure mutation)
- **Reconciliation Mode**: Audited CI/CD Pipeline (Local Workstation Apply Prohibited)

---

### Plan Summary & Diff

```terraform
{diff_summary}
```

---

### Production Reconciliation Runbook
1. **Triage Diff**: Inspect modified cloud resources above.
2. **Forensic Audit**: Check CloudTrail Event History for modifying IAM User / Role.
3. **Reconciliation Decision**:
   - **Legitimate Change**: Backport configuration into Git feature branch and merge via Pull Request.
   - **Unauthorized Mutation**: Execute automated reconciliation workflow via GitHub Actions:
     ```bash
     gh workflow run terraform-reconcile.yml -f environment={env_name}
     ```
     *(Requires 2-person quorum approval via GitHub Environment Protection Rules)*
"""


def create_or_dedup_clickup_task(
    api_token: str,
    list_id: str,
    env_name: str,
    diff_summary: str,
    drift_hash: str,
) -> dict:
    """Post an urgent task or update existing open task to prevent duplicate alert storms."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Step 1: Check for existing open task with matching idempotency key
    existing_task = find_existing_active_task(api_token, list_id, drift_hash)
    if existing_task:
        task_id = existing_task.get("id")
        task_url = existing_task.get("url", f"https://app.clickup.com/t/{task_id}")
        comment = f"[DRIFT PERSISTS] Automated scan verified drift still active at {now_utc}.\nIdempotency Key: drift-hash-{drift_hash}"
        add_comment_to_task(api_token, task_id, comment)
        print(f"[DEDUP] Found existing open ClickUp task {task_id}. Updated with persistence comment.")
        return {"id": task_id, "url": task_url, "deduped": True}

    # Step 2: Create new task if no active task matches drift hash
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    task_name = f"[DRIFT ALERT] Infrastructure Drift Detected - {env_name}"
    markdown_content = build_markdown_description(env_name, diff_summary, drift_hash, now_utc)

    payload = {
        "name": task_name,
        "description": markdown_content,
        "markdown_description": markdown_content,
        "priority": 1,
        "tags": [
            "terraform",
            "drift-detection",
            "infra-alert",
            env_name.replace("/", "-"),
            f"drift-hash-{drift_hash}",
        ],
    }

    req_data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": api_token.strip(),
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Terraform-Drift-Detector/2.0",
    }

    req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8")
            result = json.loads(resp_body)
            result["deduped"] = False
            return result
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace")
        sys.stderr.write(f"ClickUp API HTTP Error: {err.code} {err.reason}\nResponse: {err_body}\n")
        raise


def main():
    parser = argparse.ArgumentParser(description="Create or deduplicate ClickUp alert task for Terraform drift.")
    parser.add_argument("--env", "-e", default=os.environ.get("DRIFT_ENV", "environments/staging"), help="Target environment name")
    parser.add_argument("--plan-file", "-f", default=None, help="Path to raw terraform plan output file")
    parser.add_argument("--plan-json", "-j", default=None, help="Path to terraform plan JSON file")
    parser.add_argument("--summary", "-s", default=None, help="Inline diff summary text")
    args = parser.parse_args()

    api_token = os.environ.get("CLICKUP_API_TOKEN")
    list_id = os.environ.get("CLICKUP_LIST_ID")

    if not api_token or not list_id:
        sys.stderr.write("Error: CLICKUP_API_TOKEN and CLICKUP_LIST_ID environment variables must be set.\n")
        sys.exit(1)

    # 1. Parse JSON for Break-Glass Tag Quarantine & Resource Addresses
    drift_addresses = []
    if args.plan_json:
        active_drifts, drift_addresses, all_exempt = parse_plan_json(args.plan_json)
        if all_exempt:
            print("[QUARANTINE] All detected resource mutations possess DriftExempt=true. Alert suppressed per Break-Glass Policy.")
            sys.exit(0)

    # 2. Extract Raw Plan Output
    diff_text = ""
    if args.plan_file and os.path.exists(args.plan_file):
        with open(args.plan_file, "r", encoding="utf-8", errors="replace") as f:
            diff_text = f.read()
    elif args.summary:
        diff_text = args.summary
    elif not sys.stdin.isatty():
        diff_text = sys.stdin.read()
    else:
        diff_text = "No diff output supplied."

    diff_summary = extract_drift_summary(diff_text)
    drift_hash = compute_drift_hash(args.env, drift_addresses or [diff_summary[:64]])

    try:
        task_data = create_or_dedup_clickup_task(
            api_token=api_token,
            list_id=list_id,
            env_name=args.env,
            diff_summary=diff_summary,
            drift_hash=drift_hash,
        )
        task_id = task_data.get("id", "UNKNOWN")
        task_url = task_data.get("url", f"https://app.clickup.com/t/{task_id}")
        action_verb = "updated" if task_data.get("deduped") else "created"
        print(f"ClickUp Task {action_verb} successfully.")
        print(f"Task ID:   {task_id}")
        print(f"Task URL:  {task_url}")
        print(f"Drift Key: drift-hash-{drift_hash}")
    except Exception as exc:
        sys.stderr.write(f"Failed to post task to ClickUp: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
