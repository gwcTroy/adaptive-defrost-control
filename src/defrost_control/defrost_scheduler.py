import statistics
from datetime import datetime, timedelta
import io_utils
from .paths import (
    GROUP_CONFIG_JSON,
    SCHEDULE_EVENT_CSV,
    PAYLOAD_JSON,
    ECO_STATUS_URL
)


# Group_ID用於測試特定冷櫃用，在測試成功後會移除此參數
# Group_set = ["Group001", "Group002", "Group003", "Group004", "Group005", "Group006", "Group007", "Group008", "Group009", "Group010", "Group011", "Group012"]
group_config_pth = GROUP_CONFIG_JSON
payload_pth = PAYLOAD_JSON
schedule_event_pth = SCHEDULE_EVENT_CSV

DEFROST_DELTA_MIN = 5  # 除霜時間差
NA = 144
LD_NAMES = ['Ld1', 'Ld2', 'Ld3', 'Ld4', 'Ld5', 'Ld6']
# groups       = {}
payload_data = []


# return schedule
def split_schedule_by_day(sch, now_h):
    reschedule = [[], [], []]
    for ld in sch:
        day = ld // NA        # 0,1,2...
        t = ld % NA           # 0~143

        if day == 0:
            reschedule[0].append(t)
        elif day == 1:
            # 如果排程時間點在「現在之前」，放回今天(0)，否則放明天(1)
            (reschedule[0] if t < now_h else reschedule[1]).append(t)
        elif day == 2:
            (reschedule[1] if t < now_h else reschedule[2]).append(t)
    return reschedule


def reSchedule(group_id, LdList):
    plist = [[24, 36, 48],                          # 原始除霜間隔
             [30, 48, 60],                          # 智慧除霜間隔
             [4, 3, 4]]                             # 排程調整次數
    # LdList = [12, 48, 84, 120]
    period = LdList[1]-LdList[0]
    new_period = plist[1][plist[0].index(period)]   # 調整排程後的除霜間隔
    num = plist[2][plist[0].index(period)]          # 調整排程後的除霜次數
    now_h = datetime.now().hour * 6 + datetime.now().minute // 10
    # now_h = 12
    LdList.append(now_h)
    LdList.sort()
    start_s = LdList[LdList.index(now_h)-1]         # 當下時間之前的最後一次除霜排程
    newLdList = [start_s + n * new_period for n in range(1, num+1)]
    newLdList.append(newLdList[-1] + period)
    reschedule = split_schedule_by_day(newLdList, now_h)      # 將排程分成兩天設定
    for i in range(3):
        if reschedule[i]:
            return reschedule[i], reschedule[i+1]
        else:
            return reschedule[i+1], reschedule[i+2]


def getSchedule(id, reschedule):
    schedule = [NA, NA, NA, NA, NA, NA]
    for n in range(len(reschedule)):
        schedule[n] = reschedule[n]
    schedule = {LD_NAMES[i]: schedule[i] for i in range(6)}
    return schedule


def defrost_calculation(history):
    data = list(map(lambda x: int(x[:2]), history))  # 取除霜執行時間(例如：30:00 -> 30)
    average = statistics.mean(data[-31:-1])         # 取最後30次除霜時間平均
    print("最後除霜時間: ", data[-1], "，除霜平均時間: ", average)
    return data[-1], average


def msg(groupID, Thermostat, skip_status, LdParameter, time):
    try:
        # Thermostat = groups[groupID]['Thermostat']
        DeviceID = '_'.join(Thermostat)
        payload = {"GroupID": groupID, "DeviceIDs": DeviceID}
        for thermostat in Thermostat:
            for Ld_key, Ld_value in LdParameter.items():
                Ld_param = thermostat+'_'+Ld_key
                payload[Ld_param] = Ld_value

        print(payload)
        payload_data.append(payload)

        io_utils.write_csv(schedule_event_pth, [groupID, skip_status, time])

        io_utils.publish(payload)

    except Exception as e:
        print('<<', time, '=> ', groupID + 'msg error>>')
        print('<<', e, '>>\n')
    return


if __name__ == '__main__':
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '=> DefrostModifier.py')

    # 1: 讀取資料
    groups = io_utils.read_json(group_config_pth)
    ECO = io_utils.pull_request(ECO_STATUS_URL)
    ecoIDs = ECO["DeviceIDs"].split('_')

    for groupID in groups:
        if not groups[groupID]["Defrost"] == 0:
            print(groupID + " is defrosting.")
            continue
        skip_status = groups[groupID]["Skip_status"]
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        now_dt = datetime.now()
        skip_time = datetime.strptime(
            groups[groupID]["Skip_time"], '%Y-%m-%d %H:%M:%S')

    # 2: Update ItDE status
        groups[groupID]["ItDE"] = 1 if any(
            map(lambda v: v in groups[groupID]["Thermostat"], ecoIDs)) else 0
        # 比較ecoIDs裡面的溫控器存在於哪幾個group，只要有一個溫控器ID符合就把整個group的ItDE = 1，否則為0。
        # 主要是因為每個群組的除霜設定都要一樣，所以只要有其中一個溫控器設定為智慧除霜(ItDE=1)則group內所有溫控器都要開啟智慧除霜。

    # 3: 對每個Group依序判斷執行的類型
        if groups[groupID]["ItDE"] == 0:  # 在reschedule除霜排程時ItDE被設定為0，需要復原所有排程
            if not skip_status == "regular":
                LdParameter = {Ld: groups[groupID][Ld] for Ld in LD_NAMES}
                msg(groupID, groups[groupID]['Thermostat'],
                    skip_status, LdParameter, now_str)
                groups[groupID]["Skip_status"] = 'regular'
            continue
        try:
            if skip_status == 'regular':
                last, avg = defrost_calculation(groups[groupID]["DefrostTime"])
                if last < avg - DEFROST_DELTA_MIN:  # 將除霜執行時間小於平均五分鐘以上的Group進行除霜優化
                    print(now_str, ' => ', groupID,
                          " starts defrosting reschedule.")
                    current, next_day = reSchedule(
                        groupID, [groups[groupID][n] for n in LD_NAMES if groups[groupID][n] != NA])
                    if not next_day:
                        groups[groupID]["Skip_status"] = "recover"
                    else:
                        groups[groupID]["schedule_not_written"] = next_day
                        groups[groupID]["Skip_status"] = "continued"

                    schedule = getSchedule(groupID, current)
                    msg(groupID, groups[groupID]['Thermostat'],
                        skip_status, schedule, now_str)
                    groups[groupID]["Skip_time"] = now_str
                else:
                    print(now_str, ' => ', groupID,
                          " keeps in regular schedule.")

            elif skip_status == 'continued':
                if now_dt > skip_time + timedelta(days=1):

                    print(now_str, ' => ', groupID, " reschedules second day.")
                    schedule = getSchedule(
                        groupID, groups[groupID]["schedule_not_written"])
                    msg(groupID, groups[groupID]['Thermostat'],
                        skip_status, schedule, now_str)
                    groups[groupID]["Skip_time"] = now_str
                    groups[groupID]["Skip_status"] = 'recover'
                    groups[groupID]["schedule_not_written"] = []

            elif skip_status == 'recover':
                if now_dt > skip_time + timedelta(days=1):

                    print(now_str, '=>', groupID,
                          "recovers to regular defrost schedule.")
                    schedule = {Ld: groups[groupID][Ld] for Ld in LD_NAMES}
                    msg(groupID, groups[groupID]['Thermostat'],
                        skip_status, schedule, now_str)
                    groups[groupID]["Skip_status"] = 'regular'

        except Exception as e:
            print('<<', now_str, '=> ', groupID + '>>')
            print('<<', e, '>>\n')

    # 4: 儲存資料
    io_utils.write_json(group_config_pth, groups)
    print('payload_data = ', payload_data, '\n')
    io_utils.write_json(payload_pth, payload_data)
