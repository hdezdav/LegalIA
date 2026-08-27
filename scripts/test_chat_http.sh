#!/bin/bash
# Test the chat endpoint via HTTP
# Usage: ./test_chat_http.sh

set -e

API_URL="${API_URL:-https://localhost}"
if [ -z "$SERVICE_TOKEN" ] && [ -f .env ]; then
  SERVICE_TOKEN=$(grep '^LEGALIA_SERVICE_TOKEN=' .env | tail -n 1 | cut -d= -f2-)
fi
SERVICE_TOKEN="${SERVICE_TOKEN:-test-service-token}"

echo "=================================="
echo "LegalIA Chat Endpoint HTTP Test"
echo "=================================="
echo ""
echo "API URL: $API_URL"
echo "Service Token: ${SERVICE_TOKEN:0:16}..."
echo ""

# Test health first
echo "1. Testing health endpoint..."
curl -k -fsS "$API_URL/api/v1/health" | jq '.'
echo ""

# Test models
echo "2. Testing models endpoint..."
curl -k -fsS "$API_URL/api/v1/models" | jq '.'
echo ""

# Test chat completions
echo "3. Testing chat completions endpoint (OpenAI compatible)..."
RESPONSE=$(curl -k -fsS -X POST "$API_URL/api/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -H "X-LegalIA-User: test-user-123" \
  -d '{
    "model": "legalia",
    "messages": [
      {
        "role": "user",
        "content": "¿Qué dice el artículo 13 de la Constitución?"
      }
    ]
  }')

echo "$RESPONSE" | jq '.'
echo ""

# Extract key fields
ANSWER_TEXT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content')
MODEL_USED=$(echo "$RESPONSE" | jq -r '.model')
PROMPT_TOKENS=$(echo "$RESPONSE" | jq '.usage.prompt_tokens')
COMPLETION_TOKENS=$(echo "$RESPONSE" | jq '.usage.completion_tokens')
REFUSED=$(echo "$RESPONSE" | jq '.legalia.refused_for_lack_of_evidence')
VERIFICATION=$(echo "$RESPONSE" | jq '.legalia.verification_status')
LATENCY=$(echo "$RESPONSE" | jq '.legalia.latency_ms')

echo "=================================="
echo "Summary:"
echo "=================================="
echo "Model: $MODEL_USED"
echo "Refused for lack of evidence: $REFUSED"
echo "Verification status: $VERIFICATION"
echo "Prompt tokens: $PROMPT_TOKENS"
echo "Completion tokens: $COMPLETION_TOKENS"
echo "Latency: ${LATENCY}ms"
echo "Answer preview: ${ANSWER_TEXT:0:100}..."
echo ""
echo "✓ Chat completions endpoint test completed"
