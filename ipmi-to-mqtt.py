#!/usr/bin/env python3
import socket
import subprocess
import paho.mqtt.client as mqtt
import time
import os
import re
import json
import logging

# --- Logging Setup ---
# Configure basic logging format
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Configuration (via Environment Variables)
MQTT_BROKER = os.environ.get("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_USER = os.environ.get("MQTT_USER", None)
MQTT_PASS = os.environ.get("MQTT_PASS", None)
IPMI_HOST = os.environ.get("IPMI_HOST", "192.168.1.10")
IPMI_USER = os.environ.get("IPMI_USER", "ADMIN")
IPMI_PASS = os.environ.get("IPMI_PASS", "PASSWORD")
INTERVAL = int(os.environ.get("INTERVAL", 60))

# SMCIPMITool command
SMCIPMI_CMD = ["java", "-jar", "/usr/local/bin/SMCIPMITool.jar"]
SMCIPMI_PMINFO = [IPMI_HOST, IPMI_USER, IPMI_PASS, "pminfo"]

# --- Global Client and Connection Status ---
MQTT_CLIENT = None
BASE_CLIENT_ID = os.environ.get("MQTT_ID", socket.gethostname())
BASE_TOPIC = f"techthom/ipmi_{BASE_CLIENT_ID}"

# --- Discovery Constants ---
HA_DISCOVERY_PREFIX = "homeassistant"
DISCOVERY_SENT = False # Flag to ensure discovery runs only once

# --- Energy Counter Persistence ---
ENERGY_FILE = "/app/data/energy_total.json"
# Define initial state to avoid None errors
ENERGY_STATE = {
    "last_power_w": 0.0,
    "last_update_ts": time.time(),
    "total_energy_kwh": 0.0
}

# --- Persistence Functions ---

def load_energy_state():
    #Loads cumulative energy state from file
    global ENERGY_STATE
    if os.path.exists(ENERGY_FILE):
        try:
            with open(ENERGY_FILE, 'r') as f:
                ENERGY_STATE.update(json.load(f))
            logger.info(f"Loaded energy state from file. Total kWh: {ENERGY_STATE['total_energy_kwh']:.3f}")
        except Exception as e:
            logger.error(f"Failed to load energy state: {e}")
            pass # Use default initial state
    else:
        logger.info("No existing energy state file found. Starting from 0 kWh.")

def save_energy_state():
    #Saves cumulative energy state to file
    try:
        with open(ENERGY_FILE, 'w') as f:
            json.dump(ENERGY_STATE, f)
    except Exception as e:
        logger.error(f"Failed to save energy state: {e}")

# --- MQTT Callbacks ---

def on_connect(client, userdata, flags, rc, *args):
    #Callback triggered upon connecting to the MQTT broker
    global DISCOVERY_SENT
    if rc == 0:
        logger.info(f"MQTT Connected successfully. Client ID: {client._client_id.decode()}")
        # Run discovery only after a successful connection and only once
        if not DISCOVERY_SENT:
            publish_discovery_config()
            DISCOVERY_SENT = True
    else:
        logger.error(f"MQTT Connection failed with code {rc}.")

def on_disconnect(client, userdata, rc, *args):
    #Callback triggered upon disconnecting from the MQTT broker
    logger.warning(f"MQTT Disconnected. Code: {rc}. Attempting to reconnect...")

def initialize_mqtt_client():
    #Initializes and connects the global MQTT client
    global MQTT_CLIENT
    
    # Create the Client ID using the container's hostname
    client_id = f"IPMI_{BASE_CLIENT_ID}" 

    # Initialize client with V5 protocol and V2 callback API (to avoid warnings)
    MQTT_CLIENT = mqtt.Client(
        client_id=client_id, 
        protocol=mqtt.MQTTv5,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    
    # Set up credentials and callbacks
    if MQTT_USER and MQTT_PASS:
        MQTT_CLIENT.username_pw_set(MQTT_USER, MQTT_PASS)

    MQTT_CLIENT.on_connect = on_connect
    MQTT_CLIENT.on_disconnect = on_disconnect
    
    # Attempt to connect and start the loop thread
    try:
        MQTT_CLIENT.connect(MQTT_BROKER, MQTT_PORT, 60)
        MQTT_CLIENT.loop_start() # Start the network loop in a background thread
    except Exception as e:
        logger.critical(f"FATAL ERROR: Could not connect to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}. {e}")
        # The script will continue to run, but will fail to publish.

# --- Discovery Function ---

def publish_discovery_config():
    
    # Define the sensors we expect to find and their properties
    SENSORS = {
        'psu1/status':   {'Name': 'PSU 1 Status', 'Icon': 'mdi:check-circle'},
        'psu2/status':   {'Name': 'PSU 2 Status', 'Icon': 'mdi:check-circle'},
        'psu1/volt':   {'Name': 'PSU 1 Voltage', 'Unit': 'V', 'Icon': 'mdi:sine-wave'},
        'psu2/volt':   {'Name': 'PSU 2 Voltage', 'Unit': 'V', 'Icon': 'mdi:sine-wave'},
        'psu1/amp':   {'Name': 'PSU 1 Amperé', 'Unit': 'A', 'Icon': 'mdi:current-ac'},
        'psu2/amp':   {'Name': 'PSU 2 Amperé', 'Unit': 'A', 'Icon': 'mdi:current-ac'},
        'psu1/watts':  {'Name': 'PSU 1 Power', 'Unit': 'W', 'Icon': 'mdi:flash'},
        'psu2/watts':  {'Name': 'PSU 2 Power', 'Unit': 'W', 'Icon': 'mdi:flash'},
        'total/watts': {'Name': 'Total Power', 'Unit': 'W', 'Icon': 'mdi:flash', 'Class': 'power'},
        'total/kwh':   {'Name': 'Total Energy', 'Unit': 'kWh', 'Icon': 'mdi:lightning-bolt', 'Class': 'energy', 'StateClass': 'total_increasing'},
    }
    
    # Define the device (the Supermicro Server itself)
    DEVICE_INFO = {
        'identifiers': [f"ipmi_{BASE_CLIENT_ID}"],
        'name': f"IPMI Server ({BASE_CLIENT_ID})",
        'model': 'Supermicro IPMI',
        'manufacturer': 'TechThom'
    }

    logger.info("Publishing MQTT Discovery Config...")
    
    for key, props in SENSORS.items():
        # Sensor ID: e.g., ipmi_server1_total_power
        sensor_id = f"{BASE_CLIENT_ID}_{key.replace('/', '_')}"
        
        # Discovery Topic: homeassistant/sensor/total_power/config
        discovery_topic = f"{HA_DISCOVERY_PREFIX}/sensor/{sensor_id}/config"
        
        # State Topic: techthom/ipmi_server1/power/total/watts
        state_topic = f"{BASE_TOPIC}/power/{key}"
        
        # Configuration Payload
        payload = {
            'name': f"{props['Name']}",
            'unique_id': sensor_id,
            'state_topic': state_topic,
            'unit_of_measurement': props.get('Unit', ''),
            'device': DEVICE_INFO,
            'icon': props.get('Icon', '')
        }
        
        # Add Energy/Power specific classes if defined
        if 'Class' in props:
            payload['device_class'] = props['Class']
        if 'StateClass' in props:
            payload['state_class'] = props['StateClass']
        elif 'Class' in props: # Default state class for instant measurements
            payload['state_class'] = 'measurement'

        try:
            MQTT_CLIENT.publish(discovery_topic, json.dumps(payload), retain=True)
            logger.debug(f"Discovery published for: {props['Name']}")
        except Exception as e:
            logger.error(f"Error publishing discovery for {key}: {e}")

# --- Data Parsing Functions ---

def get_readings():
    try:
        # Execute the SMCIPMITool command
        command = SMCIPMI_CMD + SMCIPMI_PMINFO
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Regex to split output by module header
        modules = re.split(r"\[Module\s*(\d+)\]", result.stdout)

        # Define Variables
        readings = {}
        total_watts = 0.0

        # Iterate over the split modules
        for i in range(1, len(modules), 2):
            module_num = modules[i]
            module_content = modules[i+1]
            
            # Simplified Regex: Finds "Input Power" in the module content and captures the value.
            # Pattern: "name" + spaces + "|" + spaces + (Capture Group: number) + spaces + "symbol"
            status_match = re.search(r"Status\s*\|\s*(\s*\S+)", module_content, re.MULTILINE)
            voltage_match = re.search(r"Input Voltage\s*\|\s*(\s*\d+\.?\d*)\s*V", module_content, re.MULTILINE)
            current_match = re.search(r"Input Current\s*\|\s*(\s*\d+\.?\d*)\s*A", module_content, re.MULTILINE)
            power_match = re.search(r"Input Power\s*\|\s*(\s*\d+\.?\d*)\s*W", module_content, re.MULTILINE)

            if status_match:
                try:
                    readings[f'psu{module_num}/status'] = str(status_match.group(1).strip())
                except ValueError:
                    # Ignore if the captured value isn't a valid string
                    logger.warning(f"Failed to convert status value for PSU {module_num}.")
                    continue

            if voltage_match:
                try:
                    readings[f'psu{module_num}/volt'] = float(voltage_match.group(1).strip())
                except ValueError:
                    # Ignore if the captured value isn't a valid number
                    logger.warning(f"Failed to convert voltage value for PSU {module_num}.")
                    continue

            if current_match:
                try:
                    readings[f'psu{module_num}/amp'] = float(current_match.group(1).strip())
                except ValueError:
                    # Ignore if the captured value isn't a valid number
                    logger.warning(f"Failed to convert amperé value for PSU {module_num}.")
                    continue

            if power_match:
                try:
                    power = float(power_match.group(1).strip())
                    readings[f'psu{module_num}/watts'] = power
                    total_watts += power
                except ValueError:
                    # Ignore if the captured value isn't a valid number
                    logger.warning(f"Failed to convert power value for PSU {module_num}.")
                    continue

        # Calculate and return results
        if readings:
            readings['total/watts'] = total_watts
            readings['total/kwh'] = calculate_energy(total_watts)
            return readings

        # Fallback if no readings were found
        logger.error("Could not parse any power values from 'pminfo' output.")
        logger.debug("--- First 5 lines of the SMCIPMITool output to check ---")
        logger.debug('\n'.join(result.stdout.splitlines()[:5]))
        return None

    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing SMCIPMITool (Exit Code {e.returncode}): {e.stderr}")
        return None
    except FileNotFoundError:
        logger.critical("SMCIPMITool.jar or 'java' command not found.")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return None

# --- Energy Calculation Function ---

def calculate_energy(current_watts):
    # Calculates the energy consumed (kWh) since the last reading using the 
    # trapezoidal rule (averaging the current and previous power reading).

    global ENERGY_STATE
    
    current_ts = time.time()
    
    # Time difference in hours
    time_diff_hrs = (current_ts - ENERGY_STATE["last_update_ts"]) / 3600.0

    # Average power during the interval (in Watts)
    avg_power_w = (current_watts + ENERGY_STATE["last_power_w"]) / 2.0
    
    # Energy consumed (Watt-hours)
    energy_wh = avg_power_w * time_diff_hrs
    
    # Convert to Kilowatt-hours (kWh)
    energy_kwh = energy_wh / 1000.0

    # Update state
    ENERGY_STATE["total_energy_kwh"] += energy_kwh
    ENERGY_STATE["last_power_w"] = current_watts
    ENERGY_STATE["last_update_ts"] = current_ts

    logger.debug(f"Calculated energy: +{energy_kwh:.5f} kWh. New Total: {ENERGY_STATE['total_energy_kwh']:.3f} kWh")
    save_energy_state()
    
    return ENERGY_STATE["total_energy_kwh"]

def publish_to_mqtt(topic: str, value):
    # Uses the global client to publish sensor data
    try:
        # Publish the state value as a string
        result = MQTT_CLIENT.publish(topic, str(value), retain=False)
        result.wait_for_publish()
        logger.debug(f"Published: {value} to topic: {topic}")
        return True
        
    except Exception as e:
        logger.error(f"Error publishing to MQTT topic {topic}: {e}")
        return False
        
# --- Main Execution ---

if __name__ == "__main__":
    logger.info("Start SMCIPMITool to MQTT service with HA Discovery...")
    
    if not os.path.exists("/usr/local/bin/SMCIPMITool.jar"):
        logger.critical("FATAL ERROR: SMCIPMITool.jar not found.")
        exit(1)

    # Load any persistent energy state
    load_energy_state()

    # Initialize the persistent client connection
    initialize_mqtt_client()

    # Start the main polling loop
    while True:
        data = get_readings()
        
        # Publish readings
        if MQTT_CLIENT is None or not MQTT_CLIENT.is_connected():
            logger.warning("MQTT client is not connected. Skipping publication.")
        else:
            if data:
                for key, value in data.items():
                    full_topic = f"{BASE_TOPIC}/power/{key}"
                    publish_to_mqtt(full_topic, value)
       
        time.sleep(INTERVAL)