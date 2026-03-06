from datetime import datetime
import io_utils
from .paths import DEVICE_DATA_URL, GROUP_CONFIG_JSON, PAYLOAD_JSON, defrost_event_csv

config_pth = GROUP_CONFIG_JSON
payload_pth = PAYLOAD_JSON
params = ['IdF', 'Ld1', 'Ld2', 'Ld3', 'Ld4', 'Ld5', 'Ld6']


def to_int_if_possible(v):
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.strip().isdigit():
        return int(v.strip())
    return v


def modify_check(payload, data):
    for key in payload:
        if key in ("GroupID", "DeviceIDs"):
            continue
        if data.get(key) != payload[key]:
            io_utils.publish(payload)
            return True
    return False


def update_params(group, config, param, value, start_tag):
    config[group][param] = value
    config[group]["Start"] = start_tag
    return config


def change_status(group, de_status, dt, csv_pth, date, Stime):
    defrost_state = 'off' if de_status == '0' else 'on'
    print(dt, '=> defrost_event_collector.py')
    print(dt, '=>', group + '_Defrost', defrost_state)
    try:
        io_utils.write_csv(csv_pth, [group, date, de_status, Stime])
        print(dt, '=> Write to defrost_event.csv\n')
    except Exception as e:
        io_utils.error_publish(
            e, group + ' error when collecting defrost status.')
    return de_status


def check_payload(data, dt):
    payload_data = io_utils.read_json(payload_pth)
    payload_save = payload_data.copy() if payload_data else []
    for payload in payload_data or []:
        if modify_check(payload, data):
            print(dt, '=> payload not match\n')
        else:
            print(dt, '=> payload match\n')
            payload_save.remove(payload)
        print(dt, '=> payload:', payload)
    return payload_save


def main():
    now = datetime.now()
    request_time = now.strftime("%Y-%m-%d %H:%M:%S")
    year = now.strftime("%Y")
    date = now.strftime("%m%d")
    Stime = now.strftime("%H%M")

    csv_pth = defrost_event_csv(now)
    start_tag = f"{year}{date}_01"

    group_config = io_utils.read_json(config_pth)
    device_data = io_utils.pull_request(DEVICE_DATA_URL)

    # step 1: check Idf, Ld1~Ld6 from group_config.json
    for group in group_config:
        TherID = group_config[group]["Thermostat"][0]

        de_key = TherID + '_Defrost'
        for p in params:
            try:
                key = f"{TherID}_{p}"
                new_val = to_int_if_possible(device_data.get(key))
                if group_config[group]["Skip_status"] == "regular" and new_val is not None and group_config[group][p] != new_val:
                    print(request_time, ' => ', group + 'updates ', p)
                    group_config = update_params(
                        group, group_config, p, new_val, start_tag)
            except Exception as e:
                io_utils.error_publish(
                    e, group + ' error when updating parameters.')

    # step 2: detect defrost event change
        old_def = str(group_config[group]["Defrost"])
        new_def = str(device_data.get(de_key))
        if new_def != "None" and old_def != new_def:
            group_config[group]["Defrost"] = change_status(
                group, new_def, request_time, csv_pth, date, Stime)

    # step 3: write into group_config.json
    io_utils.write_json(config_pth, group_config)

    # setp 4: check previous payload
    payload = check_payload(device_data, request_time)
    io_utils.write_json(payload_pth, payload)


if __name__ == '__main__':
    main()
