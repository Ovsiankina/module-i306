#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-5050}"
TMPDIR="$(mktemp -d)"
DB_PATH="$TMPDIR/integration.sqlite"

export FLASK_APP=app
export FLASK_ENV=development
export FLASK_DEBUG=0
export DB_URI="sqlite:///${DB_PATH}"
export ADMIN_API_TOKEN="integration-token"

cleanup() {
	if [[ -n "${FLASK_PID:-}" ]]; then
		kill "${FLASK_PID}" >/dev/null 2>&1 || true
	fi
	rm -rf "${TMPDIR}"
}
trap cleanup EXIT

python -m flask run --port "${PORT}" --no-debugger --no-reload >/tmp/integration_flask.log 2>&1 &
FLASK_PID=$!

echo "Waiting for Flask app to start on port ${PORT}..."
for _ in {1..30}; do
	if curl -s "http://127.0.0.1:${PORT}/" >/dev/null; then
		break
	fi
	sleep 0.5
done

echo "Creating admin inventory item..."
CREATE_PAYLOAD='{"name":"Integration Widget","price":49.99,"category":"Gadgets","details":"Created from integration script","price_id":"price_integration","stock_quantity":2,"low_stock_threshold":3,"is_published":true}'
CREATE_RESPONSE="$(curl -sSf -X POST "http://127.0.0.1:${PORT}/admin/api/items" \
	-H "Authorization: Bearer ${ADMIN_API_TOKEN}" \
	-H 'Content-Type: application/json' \
	-d "${CREATE_PAYLOAD}")"
echo "Create response: ${CREATE_RESPONSE}"

ITEM_ID="$(printf '%s' "${CREATE_RESPONSE}" | python - <<'PY'
import json, sys
print(json.load(sys.stdin)["id"])
PY
)"

echo "Adjusting stock by delta..."
ADJUST_RESPONSE="$(curl -sSf -X POST "http://127.0.0.1:${PORT}/admin/api/items/${ITEM_ID}/stock" \
	-H "Authorization: Bearer ${ADMIN_API_TOKEN}" \
	-H 'Content-Type: application/json' \
	-d '{"delta":5,"note":"restock via curl"}')"
echo "Adjust response: ${ADJUST_RESPONSE}"

echo "Fetching inventory listing..."
LIST_RESPONSE="$(curl -sSf "http://127.0.0.1:${PORT}/admin/api/items" \
	-H "Authorization: Bearer ${ADMIN_API_TOKEN}" \
	-H 'Accept: application/json')"
echo "List response: ${LIST_RESPONSE}"

echo "Exporting inventory CSV..."
curl -sSf "http://127.0.0.1:${PORT}/admin/api/inventory/export" \
	-H "Authorization: Bearer ${ADMIN_API_TOKEN}" \
	-o "${TMPDIR}/inventory.csv"
echo "CSV saved to ${TMPDIR}/inventory.csv"

echo "Integration checks complete. Logs stored at /tmp/integration_flask.log"
