# Use a python base image with a package manager and minimal utilities
FROM python:3.11-slim

# Install necessary packages: OpenJDK Headless, and utilities.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        default-jre-headless \
        curl \
        tar \
        grep \
        sed \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install the Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the SMCIPMITool
COPY SMCIPMITool.jar /usr/local/bin/SMCIPMITool.jar

# Copy the entrypoint script and make it executable
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Copy the Python script
COPY ipmi-to-mqtt.py /app/

# Preset Environment Variables
ENV MQTT_BROKER="mosquitto" \
    MQTT_PORT=1883 \
    MQTT_ID="" \
    IPMI_HOST="192.168.1.10" \
    INTERVAL=60

# Define the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]