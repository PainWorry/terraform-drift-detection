# Automated Cloud Drift Detection & Reconciliation Pipeline

> Enterprise SRE watchdog detecting out-of-band AWS infrastructure drift (ClickOps) using Terraform 1.10+, native S3 state locking, AST break-glass quarantine, and idempotent ClickUp alerting.

---

## 1. Quick Overview

* **Target Cloud**: AWS (`ap-southeast-1` Singapore)
* **IaC Engine**: Terraform 1.10+ (Native S3 State Locking `use_lockfile = true`)
* **Security & Auth**: GitHub OIDC Role (`AssumeRoleWithWebIdentity` - zero static credentials)
* **Alerting & Deduplication**: ClickUp REST API v2 with SHA256 idempotency key (`drift-hash-{sha256}`)
* **Safety Controls**: Break-Glass Tag Quarantine (`DriftExempt=true`), bounded EC2 Describe API parallelism (`-parallelism=2`), and Anti-Laptop Apply Governance.

---

## 2. OS Compatibility Matrix

| Operating System | Support Level | Execution Environment | Primary Command |
| :--- | :--- | :--- | :--- |
| **Windows 11 / 10** | Supported | PowerShell 7+ / WinPS 5.1 | `python scripts/demo_drift_simulation.py` |
| **Linux (Ubuntu / AL2023)** | Supported | POSIX Bash | `./scripts/check_drift.sh environments/staging` |
| **macOS** | Supported | Zsh / Bash | `./scripts/check_drift.sh environments/staging` |

---

## 3. How to Run Locally

### 3.1 Run Offline Demonstration Runner (Zero AWS Credentials Required)
Simulate the full drift detection pipeline, AST evaluation, and ClickUp ticket generation:

```bash
python scripts/demo_drift_simulation.py
```

### 3.2 View Interactive Portfolio Mockup Showcase
Open the high-resolution portfolio asset directly in your browser:

* Double-click [`deliverables/PORTFOLIO_MOCKUP_SHOWCASE.html`](deliverables/PORTFOLIO_MOCKUP_SHOWCASE.html)

---

## 4. Production CI/CD Pipeline

The daily watchdog runs via GitHub Actions at 08:00 ICT (`01:00 UTC`):

* Detection Workflow: [`.github/workflows/drift-detection.yml`](../../.github/workflows/drift-detection.yml)
* Automated Reconciliation: [`.github/workflows/terraform-reconcile.yml`](../../.github/workflows/terraform-reconcile.yml)
* Operational Runbook: [`docs/RUNBOOK_DRIFT_DETECTION.md`](docs/RUNBOOK_DRIFT_DETECTION.md)
* Staff Architect Review Rebuttal: [`docs/STAFF_ARCHITECT_REBUTTAL.md`](docs/STAFF_ARCHITECT_REBUTTAL.md)
