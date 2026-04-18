#!/bin/bash

LOG_DIR="artifacts/monitoring"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
HEALTH_LOG="${LOG_DIR}/health_${TIMESTAMP}.log"
CONNECTIONS_LOG="${LOG_DIR}/connections_${TIMESTAMP}.log"
SUMMARY_LOG="${LOG_DIR}/summary_${TIMESTAMP}.log"

echo "=== Translation Agent Monitoring Started ===" | tee -a "$SUMMARY_LOG"
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$SUMMARY_LOG"
echo "Log Files:" | tee -a "$SUMMARY_LOG"
echo "  - Health: $HEALTH_LOG" | tee -a "$SUMMARY_LOG"
echo "  - Connections: $CONNECTIONS_LOG" | tee -a "$SUMMARY_LOG"
echo "  - Summary: $SUMMARY_LOG" | tee -a "$SUMMARY_LOG"
echo "" | tee -a "$SUMMARY_LOG"

START_TIME=$(date +%s)
HEALTH_CHECK_COUNT=0
ERROR_COUNT=0
MAX_CONNECTIONS=0
TOTAL_CONNECTIONS=0

while true; do
  CURRENT_TIME=$(date '+%Y-%m-%d %H:%M:%S')
  ELAPSED=$(($(date +%s) - START_TIME))

  # Health check
  HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:54321/api/health 2>&1)
  HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -1)
  HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | head -n -1)

  if [ "$HTTP_CODE" = "200" ]; then
    echo "[$CURRENT_TIME] OK - $HEALTH_BODY" >> "$HEALTH_LOG"
    HEALTH_CHECK_COUNT=$((HEALTH_CHECK_COUNT + 1))
  else
    echo "[$CURRENT_TIME] ERROR - HTTP $HTTP_CODE" >> "$HEALTH_LOG"
    ERROR_COUNT=$((ERROR_COUNT + 1))
  fi

  # Connection monitoring
  CONN_COUNT=$(netstat -ano | grep :54321 | grep ESTABLISHED | wc -l)
  echo "[$CURRENT_TIME] Active: $CONN_COUNT" >> "$CONNECTIONS_LOG"

  TOTAL_CONNECTIONS=$((TOTAL_CONNECTIONS + CONN_COUNT))
  if [ "$CONN_COUNT" -gt "$MAX_CONNECTIONS" ]; then
    MAX_CONNECTIONS=$CONN_COUNT
  fi

  # Console output every 30 seconds
  if [ $((ELAPSED % 30)) -eq 0 ]; then
    echo "[$CURRENT_TIME] Elapsed: ${ELAPSED}s | Health: OK($HEALTH_CHECK_COUNT) ERR($ERROR_COUNT) | Connections: $CONN_COUNT (max: $MAX_CONNECTIONS)"
  fi

  sleep 5
done
