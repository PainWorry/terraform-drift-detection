#!/usr/bin/env bash
set -eo pipefail

if [[ "${BASH_SOURCE[0]}" == */* ]]; then
  SCRIPT_DIR="$(cd "${BASH_SOURCE[0]%/*}" && pwd)"
else
  SCRIPT_DIR="$(pwd)"
fi

TARGET_DIR="${1:-environments/staging}"

echo "=========================================================="
echo " Starting Terraform Configuration Drift Detection"
echo " Target Environment : ${TARGET_DIR}"
echo " Concurrency Limit  : -parallelism=2 (Token Bucket Bounded)"
echo " Timestamp (UTC)    : $(date -u '+%Y-%m-%d %H:%M:%S UTC' 2>/dev/null || date)"
echo "=========================================================="

# Validate target directory
if [ ! -d "${TARGET_DIR}" ]; then
  echo "[FATAL] Target environment directory '${TARGET_DIR}' does not exist." >&2
  exit 1
fi

# Resolve Python interpreter
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "[FATAL] Neither 'python3' nor 'python' was found in PATH." >&2
  exit 1
fi

# Allocate temporary files
PLAN_LOG=$(mktemp 2>/dev/null || mktemp -t tf_drift_plan.XXXXXX 2>/dev/null || echo "tf_drift_plan_$$.log")
PLAN_BIN=$(mktemp 2>/dev/null || mktemp -t tf_drift_bin.XXXXXX 2>/dev/null || echo "tf_drift_bin_$$.bin")
PLAN_JSON=$(mktemp 2>/dev/null || mktemp -t tf_drift_json.XXXXXX 2>/dev/null || echo "tf_drift_json_$$.json")

# Trap cleanup on exit
trap 'rm -f "${PLAN_LOG}" "${PLAN_BIN}" "${PLAN_JSON}"' EXIT INT TERM

echo "[INFO] Executing: terraform plan -detailed-exitcode -no-color -input=false -parallelism=2 in ${TARGET_DIR}"
set +e
terraform -chdir="${TARGET_DIR}" plan -detailed-exitcode -no-color -input=false -parallelism=2 -out="${PLAN_BIN}" > "${PLAN_LOG}" 2>&1
TF_EXIT_CODE=$?
set -e

# Output full execution logs for CI visibility
cat "${PLAN_LOG}"

# Handle Terraform exit codes:
# 0 = Clean (no drift)
# 1 = Error
# 2 = Drift detected
case ${TF_EXIT_CODE} in
  0)
    echo ""
    echo "=========================================================="
    echo " [STATUS: CLEAN] Zero drift detected in ${TARGET_DIR}."
    echo " Live cloud infrastructure matches code baseline."
    echo "=========================================================="
    if [ -n "${GITHUB_STEP_SUMMARY}" ]; then
      echo "### [STATUS: CLEAN] Zero Drift Detected" >> "${GITHUB_STEP_SUMMARY}"
      echo "- **Environment**: \`${TARGET_DIR}\`" >> "${GITHUB_STEP_SUMMARY}"
      echo "- **State**: Infrastructure matches Terraform baseline." >> "${GITHUB_STEP_SUMMARY}"
    fi
    exit 0
    ;;
  1)
    echo ""
    echo "=========================================================="
    echo " [STATUS: ERROR] Terraform plan failed with execution error." >&2
    echo " Review provider errors, IAM policies, or syntax faults." >&2
    echo "=========================================================="
    if [ -n "${GITHUB_STEP_SUMMARY}" ]; then
      echo "### [STATUS: ERROR] Terraform Plan Execution Failed" >> "${GITHUB_STEP_SUMMARY}"
      echo "- **Environment**: \`${TARGET_DIR}\`" >> "${GITHUB_STEP_SUMMARY}"
      echo "- **Details**: Check step logs for provider, IAM, or syntax errors." >> "${GITHUB_STEP_SUMMARY}"
    fi
    exit 1
    ;;
  2)
    echo ""
    echo "=========================================================="
    echo " [STATUS: DRIFT DETECTED] Infrastructure divergence identified!"
    echo " Inspecting plan JSON for break-glass tags (DriftExempt)..."
    echo "=========================================================="
    
    # Export plan to JSON for tag quarantine and hash extraction
    set +e
    terraform -chdir="${TARGET_DIR}" show -json "${PLAN_BIN}" > "${PLAN_JSON}" 2>/dev/null
    set -e

    set +e
    CLICKUP_OUTPUT=$("${PYTHON_BIN}" "${SCRIPT_DIR}/create_clickup_task.py" \
      --env "${TARGET_DIR}" \
      --plan-file "${PLAN_LOG}" \
      --plan-json "${PLAN_JSON}" 2>&1)
    CLICKUP_EXIT=$?
    set -e

    echo "${CLICKUP_OUTPUT}"

    # Handle break-glass quarantine suppression
    if echo "${CLICKUP_OUTPUT}" | grep -q "\[QUARANTINE\]"; then
      echo "[INFO] Break-glass quarantine recognized: All drifts are tagged DriftExempt=true. Exiting clean."
      if [ -n "${GITHUB_STEP_SUMMARY}" ]; then
        echo "### [STATUS: QUARANTINE] Break-Glass Emergency Drift Quarantined" >> "${GITHUB_STEP_SUMMARY}"
        echo "- **Environment**: \`${TARGET_DIR}\`" >> "${GITHUB_STEP_SUMMARY}"
        echo "- **Reason**: All drifted resources possess \`DriftExempt=true\`." >> "${GITHUB_STEP_SUMMARY}"
      fi
      exit 0
    fi

    if [ ${CLICKUP_EXIT} -eq 0 ]; then
      echo "[INFO] ClickUp task created/deduplicated successfully."
      echo "::warning::Terraform drift detected in ${TARGET_DIR}. Alert dispatched."
      if [ -n "${GITHUB_STEP_SUMMARY}" ]; then
        echo "### [STATUS: DRIFT DETECTED] Alert Dispatched to ClickUp" >> "${GITHUB_STEP_SUMMARY}"
        echo "- **Environment**: \`${TARGET_DIR}\`" >> "${GITHUB_STEP_SUMMARY}"
        echo '```text' >> "${GITHUB_STEP_SUMMARY}"
        echo "${CLICKUP_OUTPUT}" >> "${GITHUB_STEP_SUMMARY}"
        echo '```' >> "${GITHUB_STEP_SUMMARY}"
      fi
      exit 2
    else
      echo "[ERROR] ClickUp task dispatch script failed with exit code ${CLICKUP_EXIT}." >&2
      echo "::error::Terraform drift detected in ${TARGET_DIR}, but ClickUp alert creation FAILED." >&2
      if [ -n "${GITHUB_STEP_SUMMARY}" ]; then
        echo "### [STATUS: CRITICAL] Drift Detected BUT ClickUp Dispatch FAILED" >> "${GITHUB_STEP_SUMMARY}"
        echo "- **Environment**: \`${TARGET_DIR}\`" >> "${GITHUB_STEP_SUMMARY}"
        echo "- **ClickUp Status**: FAILED with exit code ${CLICKUP_EXIT}." >> "${GITHUB_STEP_SUMMARY}"
        echo "- **Action Required**: Inspect credentials/network; on-call task was NOT created." >> "${GITHUB_STEP_SUMMARY}"
      fi
      exit 3
    fi
    ;;
  *)
    echo "[ERROR] Unknown Terraform plan exit code: ${TF_EXIT_CODE}" >&2
    exit ${TF_EXIT_CODE}
    ;;
esac
