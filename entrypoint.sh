#!/bin/bash
set -e

# ===============================================
# IPMI to MQTT Entrypoint Script
# ===============================================

echo "--- 🛠️ Starting Entrypoint Setup ---"

# --- Basic Validation ---
if [ ! -f "/usr/local/bin/SMCIPMITool.jar" ]; then
    echo "FATAL ERROR: SMCIPMITool.jar not found at /usr/local/bin/SMCIPMITool.jar."
    echo "Check your Dockerfile COPY steps."
    exit 1
fi
if [ ! -f "/app/ipmi-to-mqtt.py" ]; then
    echo "FATAL ERROR: Main Script not found at /app/ipmi-to-mqtt.py."
    echo "Check your Dockerfile COPY steps."
    exit 1
fi

# --- IPMI Check ---
if [ -z "$IPMI_HOST" ] || [ -z "$IPMI_USER" ] || [ -z "$IPMI_PASS" ]; then
    echo "FATAL ERROR: IPMI credentials (IPMI_HOST, IPMI_USER, IPMI_PASS) must be set."
    exit 1
fi

# --- MQTT Check ---
if [ -z "$MQTT_BROKER" ]; then
    echo "FATAL ERROR: MQTT_BROKER environment variable must be set."
    exit 1
fi

# --- Dynamic Configuration (Optional, but good for diagnostics) ---
echo "Configuration Summary:"
echo "  Client Name: IPMI_$MQTT_ID"
echo "  IPMI Host: $IPMI_HOST"
echo "  MQTT Broker: $MQTT_BROKER:$MQTT_PORT"
echo "  Polling Interval: $INTERVAL seconds"

# --- Execute the Main Application ---
echo "--- 🚀 Launching Main Application ---"

# Execute the main application by passing control to the final command.
exec python3 /app/ipmi-to-mqtt.py