#!/bin/bash
# Run a digest pipeline: aggregate → curate → deliver
# Usage: ./run_digest.sh tech|news

set -e

MODE=${1:-tech}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="/home/ubuntu/miniconda3/bin/python"
TMPFILE="/tmp/digest_${MODE}_$$.json"
CURATED="/tmp/digest_${MODE}_curated_$$.json"

cd "$SCRIPT_DIR"

# Load env
set -a
source /home/ubuntu/.env 2>/dev/null || true
set +a

echo "[$(date)] Starting $MODE digest..."

$PYTHON src/aggregate.py --mode "$MODE" --limit 100 --output "$TMPFILE"
$PYTHON src/curate.py --mode "$MODE" --input "$TMPFILE" --top 50 --output "$CURATED"
$PYTHON src/deliver.py --mode "$MODE" --input "$CURATED" --channel "$DIGEST_CHANNEL"

rm -f "$TMPFILE" "$CURATED"
echo "[$(date)] $MODE digest done."
