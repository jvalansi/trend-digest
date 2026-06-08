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
source "$SCRIPT_DIR/.env" 2>/dev/null || true
set +a

echo "[$(date)] Starting $MODE digest..."

$PYTHON src/aggregate.py --mode "$MODE" --limit 5 --output "$TMPFILE"

# Archive global trends for later clustering analysis
if [ "$MODE" = "news" ]; then
    GLOBAL_DIR="$SCRIPT_DIR/data/global_trends"
    mkdir -p "$GLOBAL_DIR"
    $PYTHON -c "
import json, sys
data = json.load(open('$TMPFILE'))
gt = data.get('sections', {}).get('Google Trends Global', [])
print(json.dumps(gt, ensure_ascii=False))
" > "$GLOBAL_DIR/$(date +%Y-%m-%d).json"
fi

$PYTHON src/curate.py --mode "$MODE" --input "$TMPFILE" --top 50 --output "$CURATED"
$PYTHON src/deliver.py --mode "$MODE" --input "$CURATED" --telegram --publish

rm -f "$TMPFILE" "$CURATED"
echo "[$(date)] $MODE digest done."
