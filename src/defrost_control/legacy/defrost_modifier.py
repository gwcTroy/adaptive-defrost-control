# -*- coding: utf-8 -*-
"""
Created on Tue Nov 23 15:10:21 2021

@author: D300
"""

import json, csv, time, statistics
import mqtt_publish as mqttPub
from datetime import datetime, timedelta

#Group_ID用於測試特定冷櫃用，在測試成功後會移除此參數
Group_ID = []
payload_pth        = "payload.json"
group_config_pth   = "group_config.json"
schedule_event_pth = "schedule_event.csv"
group_config       = {}
payload_data       = []
defrost_delta      = 6 #除霜時間差(測試中)

def read_json_file(pth):
    try:
        with open(pth, 'r', newline='') as jsonfile:
            data = json.load(jsonfile)
            return  data
    except Exception as e:
        print(e)
        time.sleep(30)
        print('#####', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '#####')
        data = read_json_file(pth)
        return data

def write_json_file(pth, data):
    with open(pth, 'w') as f:
        json.dump(data, f)
    return

def write_csv(pth, event):
    with open(pth, 'a+', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(event)
    return

def defrostSkipCheck(item):
    recover_time = datetime.strptime(group_config[item]["Skip_time"],'%Y-%m-%d %H:%M:%S')
    data = list(map(lambda x:int(x[:2]),group_config[item]["DefrostTime"])) #將時間的分鐘取出
    average = statistics.mean(data[-11:-1]) #取最後10次除霜時間平均
    
    if datetime.now() < (recover_time + timedelta(days=1)):#排程更動須與上次更動間隔一天以上(避免頻繁的更動排程)
        print (item, "Do not perform skip! ")
    elif data[-1] < average - defrost_delta:# 最近一次除霜時間低於平均時間x分鐘則跳過下次除霜排程
        print (item, "skip next defrost!")
        Execution_type("skip",item)
    else:
        print (item, "does not need to skip! ")

def defrostRecoverCheck(item):
    recover_time = datetime.strptime(group_config[item]["Skip_time"],'%Y-%m-%d %H:%M:%S')
    # recover 判斷是否寫回
    if datetime.now() > recover_time:
        print (item, "recover defrost schedule!")
        Execution_type("recover",item)
    else:
        print (item, "does not recover yet!")

def Execution_type(status,group):
    if status == "skip":
        parameter=144
        Ld_next = "Ld1"
        t = datetime.now()
        time_now = t.hour * 6 + t.minute // 10 # 轉換為與溫控器時間格式相同
        
        # 判斷下次排程
        for param in ['Ld1','Ld2','Ld3','Ld4','Ld5','Ld6']:
            Ld_check = group_config[group][param]
            if Ld_check == 144:
                continue
            if time_now < Ld_check:
                Ld_next = param
                break
        
        recover_time = datetime.now().replace(hour=group_config[group][Ld_next]//6, minute=group_config[group][Ld_next]%6,second=0, microsecond=0)
        if (recover_time < datetime.now()):
            recover_time = recover_time + timedelta(days=1)

        Ld = param
        #紀錄原始資料
        group_config[group]["Skip_status"] = True
        group_config[group]["Skip_Ld"] = Ld_next
        group_config[group]["Recover_shedule"] = group_config[group][param]
        group_config[group]["Skip_time"] = recover_time.strftime('%Y-%m-%d %H:%M:%S')
        #print(group_config[group]["Skip_status"], group_config[group]["Skip_Ld"], group_config[group]["Recover_shedule"], group_config[group]["Skip_time"])    

    elif status == "recover":
        #回復排程
        Ld = group_config[group]['Skip_Ld']
        parameter = group_config[group]['Recover_shedule']
        #紀錄資料
        group_config[group]["Skip_status"]=False
    else:
        print ("status value error!")
        return
    
    #儲存排程更動事件
    write_csv(schedule_event_pth, [group, status, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    #儲存排程狀態
    write_json_file(group_config_pth, group_config)
    #MQTT訊息
    msg(group, Ld, parameter, TC=0)
        
def msg(group, Ld, param, TC=0):
    if TC == 0:
        Thermostat = group_config[group]['Thermostat']
        DeviceID = '_'.join(Thermostat)
        payload = {"GroupID":group, "DeviceIDs":DeviceID}
        for thermostat in Thermostat:
            Ld_param = thermostat+'_'+Ld
            payload[Ld_param] = param
    else:
        DeviceID = TC
        Ld_param =TC+'_'+Ld
        payload = {"GroupID":group, "DeviceIDs":DeviceID, Ld_param:param}

    print(payload)
    mqttPub.publish(payload)
    payload_data.append(payload)

if __name__ == '__main__':

    print('#####', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '#####')
    
    # 1: 讀取資料
    group_config = read_json_file(group_config_pth)
    
    # 2: 對每個Group依序判斷執行的類型 
    for key in Group_ID:
        skip_status = group_config[key]["Skip_status"]
        if skip_status:
            defrostRecoverCheck(key)
        else:
            defrostSkipCheck(key)
    
    #3: 儲存payload用以檢查排程修改確認
    with open('payload.json', 'w') as f:
        json.dump(payload_data, f, separators=(',',':'))    