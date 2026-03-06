from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import os

load_dotenv()

DEVICE_DATA_URL = os.getenv("DEVICE_DATA_URL")
ECO_STATUS_URL = os.getenv("ECO_STATUS_URL")

MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "device/setting/global")

REPO_ROOT = Path(__file__).resolve().parents[2]

CONFIG_DIR = REPO_ROOT / "configs"
DATA_DIR = REPO_ROOT / "data"
EVENT_DIR = DATA_DIR / "events"
PAYLOAD_DIR = DATA_DIR / "payload"
LOG_DIR = REPO_ROOT / "logs"

GROUP_CONFIG_JSON = CONFIG_DIR / "group_config.json"
PAYLOAD_JSON = PAYLOAD_DIR / "payload.json"
SCHEDULE_EVENT_CSV = EVENT_DIR / "schedule_event.csv"
MANUAL_DEFROST_CSV = EVENT_DIR / "Manual_defrost.csv"


def defrost_event_csv(dt: datetime | None = None) -> Path:
    dt = dt or datetime.now()
    return EVENT_DIR / f"{dt.year}_defrost_event.csv"
