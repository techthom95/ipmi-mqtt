# Supermicro IPMI to MQTT Bridge


This container is designed to poll Supermicro IPMI systems for sensor and status data and publish that information to an MQTT broker.

This is ideal for integrating server health metrics into home automation systems (like Home Assistant) or monitoring dashboards.


## Usage & Deployment


To deploy and start this container, you can use either Docker Compose (recommended) or the standard Docker Command Line Interface (CLI).


### Docker Compose (Recommended)


Using Docker Compose is the preferred method for managing the container lifecycle and configuration.


```yaml

---

services:

  ipmi-mqtt:

    image: techthom995/ipmi-mqtt:1.0.0

    container_name: ipmi-mqtt

    restart: unless-stopped

    volumes:

      - /path/to/ipmi-mqtt/data:/app/data

    environment:

      - MQTT_BROKER=MQTT_BROKER_IP

      - MQTT_PORT=1883 #optional

      - MQTT_ID=MQTT_CLIENT_ID #optional

      - MQTT_USER=MQTT_BROKER_USERNAME

      - MQTT_PASS=MQTT_BROKER_PASSWORD

      - IPMI_HOST=IPMI_SERVER_IP

      - IPMI_USER=IPMI_SERVER_USERNAME

      - IPMI_PASS=IPMI_SERVER_PASSWORD

      - INTERVAL=60 #optional


```


### Docker CLI


For quick testing or minimal setups, the standard docker run command can be used.


```bash

docker run -d \

  --name=ipmi-mqtt\

  --restart unless-stopped \

  -v /path/to/ipmi-mqtt/data:/app/data \

  -e MQTT_BROKER=MQTT_BROKER_IP \

  -e MQTT_USER=MQTT_BROKER_USERNAME \

  -e MQTT_PASS=MQTT_BROKER_PASSWORD \

  -e IPMI_HOST=IPMI_SERVER_IP \

  -e IPMI_USER=IPMI_SERVER_USERNAME \

  -e IPMI_PASS=IPMI_SERVER_PASSWORD \

  techthom995/ipmi-mqtt:1.0.0

```


## Parameters


The container is configured using parameters passed at runtime (such as those above). These parameters are separated by a colon and indicate `<external>:<internal>` respectively. For example, `-v /path/to/ipmi-mqtt/data:/app/data` would expose the data path `/app/data` from inside the container to be accessible from the host's data path `/path/to/ipmi-mqtt/data` outside the container.


| Parameter | Function |

| :----: | --- |

| `-v /app/data` | This is used for persistent data storage |

| `-e MQTT_BROKER` | The IP address or hostname of the MQTT broker the client should connect to |

| `-e MQTT_PORT` | The network port the MQTT broker is listening on for client connections |

| `-e MQTT_ID` | A unique client identifier required by the MQTT broker. This helps the broker track the client's session |

| `-e MQTT_USER` | The username required for authentication and logging onto the MQTT broker |

| `-e MQTT_PASS` | The corresponding password for authentication with the MQTT broker |

| `-e IPMI_HOST` | The IP address or hostname of the IPMI Client |

| `-e IPMI_USER` | The username required for authentication with the IPMI Client |

| `-e IPMI_PASS` | The corresponding password for authentication with the IPMI Client |

| `-e INTERVAL` | The frequency (in seconds) at which the application queries the IPMI client and publishes the data to the MQTT broker. |


## Environment variables from files (Docker secrets)


For production environments, it's highly recommended to use Docker Secrets or load environment variables from a file instead of hardcoding them in the command or compose file.

You can load environment variables from a file using the `--env-file` argument in the CLI or Compose.


Example (CLI):


```bash

--env-file ./secrets.env

```


The file (secrets.env) would contain key-value pairs like:


```bash

MQTT_PASS=very_secret_password

IPMI_PASS=another_secret_pass

```


## License


This project is released under the MIT License.
