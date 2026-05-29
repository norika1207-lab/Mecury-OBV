#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT/var/night-runs"
mkdir -p "$RUN_DIR"

DURATION_SECONDS="${MERCURY_NIGHT_SECONDS:-43200}"
INTERVAL_SECONDS="${MERCURY_NIGHT_INTERVAL_SECONDS:-1800}"
START_TS="$(date +%s)"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$RUN_DIR/night-$RUN_ID.log"
LATEST="$RUN_DIR/latest.log"

log() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$LOG"
}

run_step() {
  local name="$1"
  shift
  log "BEGIN $name"
  "$@" >> "$LOG" 2>&1
  local code=$?
  log "END $name code=$code"
  return "$code"
}

run_step_retry_once() {
  local name="$1"
  shift
  if run_step "$name" "$@"; then
    return 0
  fi
  log "RETRY $name"
  run_step "${name}_retry" "$@"
}

run_step_allow_fail() {
  local name="$1"
  shift
  run_step "$name" "$@"
  local code=$?
  if [ "$code" -ne 0 ]; then
    log "ALLOW_FAIL $name code=$code"
  fi
  return 0
}

ln -sf "$LOG" "$LATEST"
log "Neuron Mercury night runner start"
log "root=$ROOT duration=${DURATION_SECONDS}s interval=${INTERVAL_SECONDS}s"

round=0
while true; do
  now="$(date +%s)"
  elapsed=$((now - START_TS))
  if [ "$elapsed" -ge "$DURATION_SECONDS" ]; then
    break
  fi

  round=$((round + 1))
  log "ROUND $round elapsed=${elapsed}s"
  run_step syntax node "$ROOT/src/mercury.js" help
  run_step_retry_once reflex_bench node "$ROOT/src/mercury.js" bench-reflex --count=128
  run_step semantic_reflex_bench node "$ROOT/src/mercury.js" bench-semantic-reflex --count=64
  run_step_retry_once llm_fast_hotpath_bench node "$ROOT/src/mercury.js" bench-llm-fast-hotpath
  run_step_retry_once rag_evidence_packet_bench node "$ROOT/src/mercury.js" bench-rag-evidence-packet
  run_step result_cache_bench node "$ROOT/src/mercury.js" bench-result-cache
  run_step uma_rag_bench node "$ROOT/src/mercury.js" bench-uma-rag
  run_step uma_hot_pages_bench node "$ROOT/src/mercury.js" bench-uma-hot-pages
  run_step uma_hot_cache_coherence_bench node "$ROOT/src/mercury.js" bench-uma-hot-cache-coherence
  run_step neuron_catalog_500_bench node "$ROOT/src/mercury.js" bench-neuron-catalog-500
  run_step neuron_catalog_1500_bench node "$ROOT/src/mercury.js" bench-neuron-catalog-1500
  run_step neuron_deployment_map_1500_bench node "$ROOT/src/mercury.js" bench-neuron-deployment-map-1500
  run_step neuron_concurrent_control_3000_bench node "$ROOT/src/mercury.js" bench-neuron-concurrent-control-3000
  run_step virtual_neuron_field_bench node "$ROOT/src/mercury.js" bench-virtual-neuron-field --target=10000
  run_step virtual_field_routing_bench node "$ROOT/src/mercury.js" bench-virtual-field-routing
  run_step model_field_neurons_500_bench node "$ROOT/src/mercury.js" bench-model-field-neurons-500
  run_step model_rosen_plan_bench node "$ROOT/src/mercury.js" bench-model-rosen-plan
  run_step_allow_fail model_inside_map_bench node "$ROOT/src/mercury.js" bench-model-inside-map
  run_step_allow_fail model_inside_qualitative_shift_bench node "$ROOT/src/mercury.js" bench-model-inside-qualitative-shift
  run_step_allow_fail model_inside_preheat_bench node "$ROOT/src/mercury.js" bench-model-inside-preheat
  run_step_allow_fail model_cortex_bench node "$ROOT/src/mercury.js" bench-model-cortex --models=qwen2.5:7b,deepseek-r1:7b,qwen2.5:3b
  run_step_allow_fail qwen_3060_first_packet_proof node "$ROOT/src/mercury.js" bench-qwen-3060-first-packet-proof --model=qwen2.5:7b --num-predict=48
  run_step_allow_fail local_model_first_packet_matrix node "$ROOT/src/mercury.js" bench-local-model-first-packet-matrix --models=qwen2.5:7b,deepseek-r1:7b,qwen2.5:3b --num-predict=24
  run_step neuron_coverage_rotation_bench node "$ROOT/src/mercury.js" bench-neuron-coverage-rotation
  run_step neuron_score_ledger_coverage_bench node "$ROOT/src/mercury.js" bench-neuron-score-ledger-coverage
  run_step neuron_state_field_bindings_bench node "$ROOT/src/mercury.js" bench-neuron-state-field-bindings
  run_step neuron_state_field_hotpath_bench node "$ROOT/src/mercury.js" bench-neuron-state-field-hotpath
  run_step neuron_thermal_collapse_bench node "$ROOT/src/mercury.js" bench-neuron-thermal-collapse
  run_step neuron_coverage_trend_bench node "$ROOT/src/mercury.js" bench-neuron-coverage-trend
  run_step control_map_score_routing_bench node "$ROOT/src/mercury.js" bench-control-map-score-routing
  run_step lane_dispatch_engine_bench node "$ROOT/src/mercury.js" bench-lane-dispatch-engine
  run_step anti_overactivation_bench node "$ROOT/src/mercury.js" bench-anti-overactivation
  run_step neuron_lane_health_bench node "$ROOT/src/mercury.js" bench-neuron-lane-health
  run_step self_accelerate_bench node "$ROOT/src/mercury.js" bench-self-accelerate
  run_step project_isolation_bench node "$ROOT/src/mercury.js" bench-project-isolation
  run_step project_accelerate_bench node "$ROOT/src/mercury.js" bench-project-accelerate
  run_step project_scale_accelerate_bench node "$ROOT/src/mercury.js" bench-project-scale-accelerate
  run_step namespace_acceleration_isolation_bench node "$ROOT/src/mercury.js" bench-namespace-acceleration-isolation
  run_step uma_preload_budget_bench node "$ROOT/src/mercury.js" bench-uma-preload-budget
  run_step uma_target_file_first_bench node "$ROOT/src/mercury.js" bench-uma-target-file-first
  run_step_retry_once code_cortex_metadata_bench node "$ROOT/src/mercury.js" bench-code-cortex-metadata
  run_step uma_hot_path_caches_bench node "$ROOT/src/mercury.js" bench-uma-hot-path-caches
  run_step uma_product_proof_bench node "$ROOT/src/mercury.js" bench-uma-product-proof
  run_step uma_batch_search_bench node "$ROOT/src/mercury.js" bench-uma-batch-search
  run_step uma_batch_neuron_preload_bench node "$ROOT/src/mercury.js" bench-uma-batch-neuron-preload
  run_step uma_project_warmup_bench node "$ROOT/src/mercury.js" bench-uma-project-warmup
  run_step resident_uma_keep_warm_bench node "$ROOT/src/mercury.js" bench-resident-uma-keep-warm
  run_step_retry_once monster_doctor_bench node "$ROOT/src/mercury.js" bench-monster-doctor
  if [[ "${MERCURY_RUN_DOC_ARTIFACTS:-0}" == "1" ]]; then
    run_step_retry_once monster_proof_report_bench node "$ROOT/src/mercury.js" bench-monster-proof-report
  else
    log "skip monster_proof_report_bench page writer (MERCURY_RUN_DOC_ARTIFACTS=0)"
  fi
  run_step_retry_once monster_doctor_coherence_refresh_bench node "$ROOT/src/mercury.js" bench-monster-doctor-coherence-refresh
  run_step rosen_bridge_route_bench node "$ROOT/src/mercury.js" bench-rosen-bridge-route
  run_step rosen_execute_plan_bench node "$ROOT/src/mercury.js" bench-rosen-execute-plan
  run_step rosen_neuron_boost_bench node "$ROOT/src/mercury.js" bench-rosen-neuron-boost
  run_step rosen_pair_runtime_bench node "$ROOT/src/mercury.js" bench-rosen-pair-runtime
  if [[ "${MERCURY_RUN_DOC_ARTIFACTS:-0}" == "1" ]]; then
    run_step rosen_proof_report_bench node "$ROOT/src/mercury.js" bench-rosen-proof-report
    run_step launch_experiment_report node "$ROOT/src/mercury.js" launch-experiment-report
  else
    log "skip doc artifact proof exports (MERCURY_RUN_DOC_ARTIFACTS=0)"
  fi
  if [[ "${MERCURY_RUN_DOC_ARTIFACTS:-0}" == "1" ]]; then
    run_step paper_experiment_suite_bench node "$ROOT/src/mercury.js" bench-paper-experiment-suite
  run_step paper_experiment_suite node "$ROOT/src/mercury.js" paper-experiment-suite --repeat=3 --limit=300
  else
    log "skip paper suite page writers (MERCURY_RUN_DOC_ARTIFACTS=0)"
  fi
  run_step night_runner_product_core_bench node "$ROOT/src/mercury.js" bench-night-runner-product-core
  run_step diskspd_proof_artifact_guard_bench node "$ROOT/src/mercury.js" bench-diskspd-proof-artifact-guard
  run_step speed_state_product_proof_bench node "$ROOT/src/mercury.js" bench-speed-state-product-proof
  run_step product_activate_bench node "$ROOT/src/mercury.js" bench-product-activate
  run_step resident_product_proof_endpoint_bench node "$ROOT/src/mercury.js" bench-resident-product-proof-endpoint
  run_step resident_virtual_field_endpoint_bench node "$ROOT/src/mercury.js" bench-resident-virtual-field-endpoint
  run_step product_first_impression_bench node "$ROOT/src/mercury.js" bench-product-first-impression
  run_step product_first_impression_trend_bench node "$ROOT/src/mercury.js" bench-product-first-impression-trend
  run_step product_proof_integrity_bench node "$ROOT/src/mercury.js" bench-product-proof-integrity
  run_step product_proof_freshness_guard_bench node "$ROOT/src/mercury.js" bench-product-proof-freshness-guard
  run_step product_proof_refresh_plan_bench node "$ROOT/src/mercury.js" bench-product-proof-refresh-plan
  run_step product_3060_acceptance_bench node "$ROOT/src/mercury.js" bench-product-3060-acceptance
  run_step product_command_bench node "$ROOT/src/mercury.js" bench-product-command
  if [[ "${MERCURY_RUN_DOC_ARTIFACTS:-0}" == "1" ]]; then
    run_step product_boost_bench node "$ROOT/src/mercury.js" bench-product-boost
  else
    log "skip product_boost_bench page writer (MERCURY_RUN_DOC_ARTIFACTS=0)"
  fi
  run_step windows_3060_product_proof_bench node "$ROOT/src/mercury.js" bench-windows-3060-product-proof
  run_step product_activate node "$ROOT/src/mercury.js" product activate
  if [[ "${MERCURY_RUN_DOC_ARTIFACTS:-0}" == "1" ]]; then
    run_step product_boost node "$ROOT/src/mercury.js" product boost "diagnose this project for latency and paid provider risk" --path=.
  else
    log "skip product_boost page writer (MERCURY_RUN_DOC_ARTIFACTS=0)"
  fi
  run_step installer_manifest_bench node "$ROOT/src/mercury.js" bench-installer-manifest
  run_step installer_manifest node "$ROOT/src/mercury.js" installer-manifest --target=100000000
  run_step product_status node "$ROOT/src/mercury.js" product status
  if [[ "${MERCURY_RUN_DOC_ARTIFACTS:-0}" == "1" ]]; then
    run_step universe_map_bench node "$ROOT/src/mercury.js" bench-universe-map
    run_step universe_map node "$ROOT/src/mercury.js" universe-map
    run_step product_dashboard_bench node "$ROOT/src/mercury.js" bench-product-dashboard
    run_step product_dashboard node "$ROOT/src/mercury.js" product-dashboard --fast
    run_step investor_brief_bench node "$ROOT/src/mercury.js" bench-investor-brief
    run_step investor_brief node "$ROOT/src/mercury.js" investor-brief
  else
    log "skip public page writers (MERCURY_RUN_DOC_ARTIFACTS=0)"
  fi
  if [[ "${MERCURY_RUN_DEMO_ARTIFACTS:-0}" == "1" ]]; then
    run_step demo_console_bench node "$ROOT/src/mercury.js" bench-demo-console
    run_step demo_console node "$ROOT/src/mercury.js" demo-console
  else
    log "skip demo_console artifacts (MERCURY_RUN_DEMO_ARTIFACTS=0)"
  fi
  run_step task_route_memory_spend_bench node "$ROOT/src/mercury.js" bench-task-route-memory-spend
  run_step accelerate_task_bench node "$ROOT/src/mercury.js" bench-accelerate-task
  run_step workflow_replay_invalidation_bench node "$ROOT/src/mercury.js" bench-workflow-replay-invalidation
  run_step accelerate_task_first_gen_bench node "$ROOT/src/mercury.js" bench-accelerate-task-first-gen
  run_step cold_start_accelerate_bench node "$ROOT/src/mercury.js" bench-cold-start-accelerate
  run_step_retry_once first_gen_accelerate_bench node "$ROOT/src/mercury.js" bench-first-gen-accelerate
  run_step cost_scan node "$ROOT/src/mercury.js" cost-scan --path=. --limit=500
  run_step spend_guard node "$ROOT/src/mercury.js" spend-guard --path=. --limit=500
  run_step code_cortex node "$ROOT/src/mercury.js" code-cortex --path=. --limit=500
  run_step uma_coherence node "$ROOT/src/mercury.js" uma-coherence
  run_step monster_doctor node "$ROOT/src/mercury.js" monster-doctor "find provider spend leaks, cache bypasses, stale UMA pages, and hot path latency" --path=. --limit=500 --warm=4
  if [[ "${MERCURY_RUN_DOC_ARTIFACTS:-0}" == "1" ]]; then
    run_step monster_proof_report node "$ROOT/src/mercury.js" monster-proof-report "find provider spend leaks, cache bypasses, stale UMA pages, and hot path latency" --path=. --limit=500 --warm=4
  else
    log "skip monster_proof_report page writer (MERCURY_RUN_DOC_ARTIFACTS=0)"
  fi
  run_step resident_start node "$ROOT/src/mercury.js" resident start --low-impact
  run_step resident_bench node "$ROOT/src/mercury.js" bench-resident --count=64
  run_step resident_llm_fast_endpoint_bench node "$ROOT/src/mercury.js" bench-resident-llm-fast-endpoint
  run_step resident_llm_fast_final_merge_endpoint_bench node "$ROOT/src/mercury.js" bench-resident-llm-fast-final-merge-endpoint
  run_step resident_thermal_state_endpoint_bench node "$ROOT/src/mercury.js" bench-resident-thermal-state-endpoint
  run_step resident_task_cache_coherence_bench node "$ROOT/src/mercury.js" bench-resident-task-cache-coherence
  run_step resident_route_cache_coherence_bench node "$ROOT/src/mercury.js" bench-resident-route-cache-coherence
  run_step warmup node "$ROOT/src/mercury.js" warmup --models=game-mode,bench-semantic --limit=512
  run_step cache_stats node "$ROOT/src/mercury.js" llm-cache stats --limit=8
  run_step slow_jobs node "$ROOT/src/mercury.js" slow-jobs list --limit=8
  if [[ "${MERCURY_NIGHT_ALLOW_SLOW_WORKER:-0}" == "1" ]]; then
    run_step slow_worker node "$ROOT/src/mercury.js" slow-worker --limit=1 --seed-response="Slow path captured this miss; keep the hot path on reflex/cache and refine this answer when a local model is available."
  else
    log "skip slow_worker foreground-safe night mode (MERCURY_NIGHT_ALLOW_SLOW_WORKER=0)"
  fi
  run_step reflex_scores node "$ROOT/src/mercury.js" reflex-scores --limit=8
  run_step reflex_score_summary node "$ROOT/src/mercury.js" reflex-scores summarize --limit=8
  run_step_retry_once speed_state_bench node "$ROOT/src/mercury.js" bench-speed-state
  run_step speed_state_cache_bench node "$ROOT/src/mercury.js" bench-speed-state-cache
  run_step speed_trends_bench node "$ROOT/src/mercury.js" bench-speed-trends
  if [[ "${MERCURY_RUN_DOC_ARTIFACTS:-0}" == "1" ]]; then
    run_step visual_speed_dashboard_bench node "$ROOT/src/mercury.js" bench-visual-speed-dashboard
    run_step visual_speed_export node "$ROOT/src/mercury.js" visual-speed-export
    run_step rosen_proof_report node "$ROOT/src/mercury.js" rosen-proof-report
    run_step monster_proof_report_export node "$ROOT/src/mercury.js" monster-proof-report "find provider spend leaks, cache bypasses, stale UMA pages, and hot path latency" --path=. --limit=500 --warm=4
  else
    log "skip visual/public proof page writers (MERCURY_RUN_DOC_ARTIFACTS=0)"
  fi
  run_step atomic_json_write_bench node "$ROOT/src/mercury.js" bench-atomic-json-write
  run_step docs_consistency_bench node "$ROOT/src/mercury.js" bench-docs-consistency
  run_step gpu_policy_state_bench node "$ROOT/src/mercury.js" bench-gpu-policy-state
  run_step runtime_detector_bench node "$ROOT/src/mercury.js" bench-runtime-detector
  run_step runtime_route_bench node "$ROOT/src/mercury.js" bench-runtime-route
  run_step slow_provider_hint_bench node "$ROOT/src/mercury.js" bench-slow-provider-hint
  run_step_retry_once qwer_speed_plan_bench node "$ROOT/src/mercury.js" bench-qwer-speed-plan
  if [[ "${MERCURY_RUN_WINDOWS_HOTPATH:-0}" == "1" ]]; then
    run_step_retry_once windows_hotpath_plan node "$ROOT/src/mercury.js" windows-hotpath-plan
    run_step_retry_once qwen_3060_demo_bench node "$ROOT/src/mercury.js" bench-qwen-3060-demo --model="${MERCURY_QWEN_MODEL:-qwen2.5:7b}" --repeat="${MERCURY_QWEN_REPEAT:-3}"
    run_step_retry_once qwen_3060_cold_start_bench node "$ROOT/src/mercury.js" bench-qwen-3060-cold-start --model="${MERCURY_QWEN_MODEL:-qwen2.5:7b}"
  else
    log "skip windows_hotpath checks (MERCURY_RUN_WINDOWS_HOTPATH=0)"
  fi
  run_step slow_worker_provider_gate_bench node "$ROOT/src/mercury.js" bench-slow-worker-provider-gate
  run_step_retry_once slow_worker_provider_cache_bench node "$ROOT/src/mercury.js" bench-slow-worker-provider-cache
  run_step_retry_once llm_fast_final_merge_bench node "$ROOT/src/mercury.js" bench-llm-fast-final-merge
  run_step slow_job_priority_bench node "$ROOT/src/mercury.js" bench-slow-job-priority
  run_step semantic_risk_gate_bench node "$ROOT/src/mercury.js" bench-semantic-risk-gate
  run_step_retry_once workflow_memory_bench node "$ROOT/src/mercury.js" bench-workflow-memory
  run_step_retry_once nervous_system_bench node "$ROOT/src/mercury.js" bench-nervous-system
  run_step_retry_once first_gen_dispatch_state_bench node "$ROOT/src/mercury.js" bench-first-gen-dispatch-state
  run_step_retry_once first_gen_dispatch_run_bench node "$ROOT/src/mercury.js" bench-first-gen-dispatch-run
  run_step first_gen_dispatch_plan_bench node "$ROOT/src/mercury.js" bench-first-gen-dispatch-plan
  run_step speed_state node "$ROOT/src/mercury.js" speed-state
  run_step speed_trends node "$ROOT/src/mercury.js" speed-trends
  run_step nervous_system node "$ROOT/src/mercury.js" nervous-system
  run_step runtime_detect node "$ROOT/src/mercury.js" runtime-detect
  run_step qwer_speed_plan node "$ROOT/src/mercury.js" qwer-speed-plan
  run_step model_openability node "$ROOT/src/mercury.js" model-openability
  run_step model_rosen_plan node "$ROOT/src/mercury.js" model-rosen-plan
  run_step_allow_fail model_inside_map node "$ROOT/src/mercury.js" model-inside-map
  run_step_allow_fail model_preheat node "$ROOT/src/mercury.js" model-preheat
  run_step virtual_field node "$ROOT/src/mercury.js" virtual-field --target=10000
  run_step virtual_route node "$ROOT/src/mercury.js" virtual-route "accelerate local model first useful packet with UMA model cortex and 3060 low-impact mode"
  run_step_allow_fail model_cortex node "$ROOT/src/mercury.js" model-cortex --models=qwen2.5:7b,deepseek-r1:7b,qwen2.5:3b
  run_step_allow_fail llm_preheat_first_packet node "$ROOT/src/mercury.js" llm-fast --model=qwen2.5:7b --prompt="prepare first useful qwen response with model preheat" --preheat-first
  run_step workflow_cache_stats node "$ROOT/src/mercury.js" workflow-cache --limit=8
  run_step memory_graph_stats node "$ROOT/src/mercury.js" memory-graph --limit=8
  run_step rosen_route node "$ROOT/src/mercury.js" rosen-route "find hidden Anthropic billing loops and hot path latency" --limit=12
  run_step task_memory node "$ROOT/src/mercury.js" task-memory --limit=5000
  run_step task_route node "$ROOT/src/mercury.js" task-route "find hidden Anthropic billing loops and hot path latency" --path=.
  run_step cold_start_accelerate node "$ROOT/src/mercury.js" cold-start-accelerate "create first useful diagnosis before any model call" --path=. --limit=500 --budget-ms=12
  run_step first_gen_accelerate node "$ROOT/src/mercury.js" first-gen-accelerate "generate first 5000 word report with UMA evidence packets before model calls" --path=. --limit=500 --sections=8 --workers=4 --serial-ms=120000
  run_step first_gen_dispatch node "$ROOT/src/mercury.js" first-gen-dispatch --limit=8
  run_step accelerate_task node "$ROOT/src/mercury.js" accelerate-task "find hidden Anthropic billing loops and hot path latency" --path=.

  if [ -d /root/afu-brain ] && [ -x /root/afu-brain ]; then
    run_step_retry_once afu_namespace_refresh bash -lc "cd /root/afu-brain && node '$ROOT/src/mercury.js' uma project refresh --path=. --limit=240"
    run_step_retry_once afu_project_accelerate bash -lc "cd /root/afu-brain && node '$ROOT/src/mercury.js' accelerate-project --path=. --limit=240 --warm=6"
    run_step_retry_once afu_monster_doctor bash -lc "cd /root/afu-brain && node '$ROOT/src/mercury.js' monster-doctor 'find provider spend leaks and hot path latency in AFU' --path=. --limit=240 --warm=4"
    run_step_retry_once afu_bench bash -lc "cd /root/afu-brain && node '$ROOT/src/mercury.js' bench '$ROOT/tasks/afu-uma.json' --profile --budget --warmup --repeat=2"
  else
    log "SKIP afu_bench missing or inaccessible /root/afu-brain"
  fi

  if [ -d /root ] && [ -x /root ]; then
    run_step_retry_once lobster_namespace_refresh bash -lc "cd /root && node '$ROOT/src/mercury.js' uma project refresh --path=. --limit=80 --include='lobster' --exclude='Neuron Mercury,afu-brain'"
    run_step_retry_once lobster_project_accelerate bash -lc "cd /root && node '$ROOT/src/mercury.js' accelerate-project --path=. --limit=80 --warm=6 --include='lobster' --exclude='Neuron Mercury,afu-brain'"
    run_step_retry_once lobster_cost_scan bash -lc "cd /root && node '$ROOT/src/mercury.js' cost-scan --path=. --limit=160 --include='lobster' --exclude='Neuron Mercury,afu-brain'"
    run_step_retry_once lobster_spend_guard bash -lc "cd /root && node '$ROOT/src/mercury.js' spend-guard --path=. --limit=160 --include='lobster' --exclude='Neuron Mercury,afu-brain'"
    run_step_retry_once lobster_monster_doctor bash -lc "cd /root && node '$ROOT/src/mercury.js' monster-doctor 'find hidden paid-provider loops and hot path latency in Lobster' --path=. --limit=160 --warm=4 --include='lobster' --exclude='Neuron Mercury,afu-brain'"
    run_step_retry_once lobster_bench bash -lc "cd /root && node '$ROOT/src/mercury.js' bench '$ROOT/tasks/lobster-debug.json' --profile --budget --warmup --repeat=2"
  else
    log "SKIP lobster_bench missing or inaccessible /root"
  fi

  log "ROUND $round complete"
  sleep "$INTERVAL_SECONDS"
done

log "Neuron Mercury night runner complete"
