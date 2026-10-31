#!/usr/bin/env bash
# Local Helm checks only. No dependency fetching, installation or cluster validation.

lint_only=false
if [ "${1:-}" = "--lint-only" ]; then
    lint_only=true
    shift
fi

if [ "$#" -gt 1 ]; then
    printf 'Usage: %s [--lint-only] [chart-directory]\n' "$0" >&2
    exit 64
fi

chart_dir=${1:-.}
case "$chart_dir" in
    -*) chart_dir="./$chart_dir" ;;
esac

if [ ! -f "$chart_dir/Chart.yaml" ]; then
    printf 'Chart.yaml not found in chart directory.\n' >&2
    exit 66
fi

if ! command -v helm >/dev/null 2>&1; then
    printf 'Helm is unavailable; use the project-selected tool environment.\n' >&2
    exit 127
fi

helm lint "$chart_dir"
lint_status=$?
if [ "$lint_status" -ne 0 ]; then
    exit "$lint_status"
fi

if [ "$lint_only" = true ]; then
    printf 'Local Helm lint passed; consumer-chart rendering remains unverified, as do cluster admission and rollout.\n'
    exit 0
fi

# Keep rendered resources, which may contain Secrets, out of normal output.
helm template validation "$chart_dir" >/dev/null
template_status=$?
if [ "$template_status" -ne 0 ]; then
    exit "$template_status"
fi

printf 'Local Helm lint/render checks passed; cluster admission and rollout remain unverified.\n'
