
import sys
import requests
import json
import csv
import time as t
from datetime import datetime
import paho.mqtt.client as mqtt
from pathlib import Path
from .paths import MQTT_HOST, MQTT_PORT, MQTT_TOPIC


def _p(path) -> Path:
    return path if isinstance(path, Path) else Path(path)


def pull_request(url, Counter=0):
    if Counter == 3:
        print('<< connection failed >>\n')
        sys.exit(0)
    try:
        response = requests.get(url)
        data_json = response.json()
        return data_json
    except Exception as e:
        error_publish(e, "Error when executing pull request.")
        t.sleep(30)
        data_json = pull_request(url, Counter+1)
        return data_json


def publish(payload, host=MQTT_HOST, topic=MQTT_TOPIC):
    client = mqtt.Client()
    # client.username_pw_set(user, password)
    client.connect(host, 1883, 60)
    client.publish(topic, json.dumps(payload))
    t.sleep(5)
    client.disconnect()


def read_json(path, Counter=1):
    path = _p(path)
    if Counter > 3:
        print('<< read JSON file failed, leaving... >>\n')
        sys.exit(0)
    try:
        with open(path, newline='') as file:
            data = json.load(file)
            return data
    except Exception as e:
        error_publish(e, "Error when reading JSON file ", Counter)
        t.sleep(10)
        data = read_json(path, Counter+1)
        return data


def write_json(path, data):
    path = _p(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f)


def read_csv(path, Counter=1):
    path = _p(path)
    if Counter > 3:
        print('<< read CSV file failed, leaving... >>\n')
        sys.exit(0)
    try:
        with open(path, 'r', newline='') as file:
            rows = csv.reader(file, delimiter=',')
            data = [row for row in rows]
            return data
    except Exception as e:
        error_publish(e, "Error when reading CSV file ", Counter)
        t.sleep(10)
        data = read_csv(path, Counter+1)
        return data


def write_csv(path, event):
    path = _p(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a+', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(event)


def error_publish(error, message):
    print('<<', datetime.now().strftime(
        '%Y-%m-%d %H:%M:%S'), '=>', message, ' >>')
    print('<<', error, '>>\n')
