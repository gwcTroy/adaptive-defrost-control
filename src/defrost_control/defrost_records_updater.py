from datetime import datetime, timedelta
import io_utils
from defrost_control import paths


GroupConfigPath = paths.GROUP_CONFIG_JSON
DefrostEvenPath = paths.defrost_event_csv(datetime.now())
ManualDefrostPath = paths.MANUAL_DEFROST_CSV

params = ['Ld1', 'Ld2', 'Ld3', 'Ld4', 'Ld5', 'Ld6']  # 溫控器的時間參數
DetectionRange = timedelta(minutes=10)  # 判斷手動除霜的時間範圍


def last_defrost_event(events):
    # 資料格式[[Group,date,status,time], ... , [Group,date,status,time]]
    # 假如最後一筆資料的除霜狀態為1則代表目前還在除霜，所以取的值在往前一位
    for i in range(len(events) - 1, 0, -1):
        if events[i][2] == '0' and events[i-1][2] == '1':
            return [events[i-1], events[i]]
    return None


# 資料計算
def calc_execution_time(Last_defrost_event):
    year = datetime.now().strftime("%Y")
    # Last_defrost_event的資料格式[[Group,date,1,time], [Group,date,0,time]]
    Start = datetime.strptime('{year}{date}{time}'.format(year=year, date=str(
        Last_defrost_event[0][1]).zfill(4), time=str(Last_defrost_event[0][3]).zfill(4)), "%Y%m%d%H%M")
    End = datetime.strptime('{year}{date}{time}'.format(year=year, date=str(
        Last_defrost_event[1][1]).zfill(4), time=str(Last_defrost_event[1][3]).zfill(4)), "%Y%m%d%H%M")
    execution_time = End-Start
    if execution_time > timedelta(hours=1):
        execution_time = None
    else:
        execution_time = datetime.strptime(str(execution_time), "%H:%M:%S").strftime(
            "%M:%S")  # 將計算結果(%H:%M:%S)轉為分跟秒("%M:%S")
    return execution_time, str(Start), str(End)


# 手動除霜監測
# 目前排程更動會被視為是手動除霜
def is_manual_defrost(group_config, start_time, group):
    start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    for p in params:  # params:['Ld1', 'Ld2', 'Ld3', 'Ld4', 'Ld5', 'Ld6']
        if group_config[group][p] == 144:  # 144(Na)
            continue
        else:
            params_time = start_time.replace(
                hour=group_config[group][p]//6, minute=group_config[group][p]*10 % 60)
            if params_time < start_time - timedelta(hours=12):
                params_time += timedelta(days=1)

            # 判斷除霜開啟的時間是否在設定時間內執行
            if ((params_time - DetectionRange) <= start_time <= (params_time + DetectionRange)):
                return False
            else:
                continue
    print('<<', datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
          '=>', group, 'Manual_Defrost >>')
    io_utils.write_csv(ManualDefrostPath, [
                       group, start_time.strftime("%Y-%m-%d %H:%M:%S")])
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '=>', ManualDefrostPath)
    return True


if __name__ == '__main__':

    dirty = False
    last_update_info = None
    # step 1: read file
    group_config = io_utils.read_json(GroupConfigPath)
    defrost_event = io_utils.read_csv(DefrostEvenPath)
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
          '=> defrost_records_updater.py')

    # step 2: data processing
    for key in group_config:
        try:
            group_defrost_event = [row for row in defrost_event if (
                row[0] == key)]  # 取個別Group的除霜事件
            last_event = last_defrost_event(group_defrost_event)
            if last_event == None:
                continue

            # step 3: Data calculation
            try:
                if ((last_event[0][2] == '1') and (last_event[1][2] == '0')):
                    execution_time, start_time, end_time = calc_execution_time(
                        last_event)

                    if execution_time == None:
                        continue

                    # step 4: save data and Manual defrost detection
                    try:
                        if (end_time > group_config[key]['End_time']):  # 判斷資料是否以儲存過

                            # 偵測手動除霜
                            manual = is_manual_defrost(
                                group_config, start_time, key)
                            if not manual:
                                # Start time and End time update
                                group_config[key]['Start_time'] = start_time
                                group_config[key]['End_time'] = end_time
                                # 儲存除霜執行時間
                                group_config[key]["DefrostTime"].pop(0)
                                group_config[key]["DefrostTime"].append(
                                    execution_time)
                                dirty = True
                                last_update_info = (
                                    key, start_time, end_time, execution_time)

                        else:
                            continue

                    except Exception as e:
                        print('<<', datetime.now().strftime(
                            '%Y-%m-%d %H:%M:%S'), '=> ', key + '_Step 4 error  >>\n')
                        print('<<', e, '>>\n')

            except Exception as e:
                print('<<', datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                      '=> ', key + '_Step 3 error  >>\n')
                print('<<', e, '>>\n')

        except Exception as e:
            print('<<', datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                  '=> ', key + '_Step 2 error  >>\n')
            print('<<', e, '>>\n')

    if dirty:
        # 更新group_config.json
        io_utils.write_json(
            GroupConfigPath, group_config)
        k, st, et, ex = last_update_info

        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '=>', k, 'Start:',
              st, 'End:', et, 'executionTime:', ex)
