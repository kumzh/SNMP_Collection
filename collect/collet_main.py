import threading,logging
import os,sys
import time
import inspect
import ctypes
from monitor.collect.setting import Settings
from monitor.collect.db_connect import connect_db
from pysnmp.hlapi.asyncore import *
import queue
import operator
logging.basicConfig(filename='collect_log.txt',level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

db,cur = connect_db()
bmc_setting = Settings()


class Monitor():
    def __init__(self):
        self.f_data = []
        self.myq = queue.Queue()
    # 回调函数。在有数据返回时触发
    def add(self, snmpEngine, sendRequestHandle, errorIndication, errorStatus, errorIndex, varBinds, cbCtx):
        self.myq.put(varBinds)

    def get_info(self, host, oids, community):
        # 添加任务
        snmpEngine = SnmpEngine()
        for oid in oids:
            getCmd(snmpEngine,
                   CommunityData(community),  # 1表示V2c
                   UdpTransportTarget((host, 161), timeout=3, retries=0, ),  # 传输目标
                   ContextData(),
                   ObjectType(ObjectIdentity(oid)),
                   cbFun=self.add
                   )
        # 执行异步获取snmp
        snmpEngine.transportDispatcher.runDispatcher()
        return self.myq

    def change(self,data_obj,oids):
        oid_temp = []
        while True:
            try:
                info = data_obj.get(block=False)
                per_oid = info[0][0]
                oid_temp.append(str(per_oid))
                per_info = info[0][1]
                self.f_data.append(str(per_info))
            except queue.Empty:
                break
        if operator.ne(oids,oid_temp):
            return None
        else:
            return self.f_data


def data_in(hostid, value):
    memfree, freecpupercent, usetime, system = value
    seconds = int(usetime)/100
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    usetime = str("%02d:%02d:%02d" % (h, m, s))
    time_now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    insert_sql = """insert into monitor_monitor(ip_add, mem_free, free_cpu_percent, use_time,in_time) 
                                            values(%s, %s, %s, %s, %s)"""
    cur.execute(insert_sql, (hostid,  memfree, freecpupercent, usetime, time_now))
    db.commit()

def sel_oids(system):
    if system.lower() == "linux":
        return bmc_setting.linux_oids
    elif system.lower() == "windows":
        return None
    else:
        logging.error("Devices are not supported!")
        return None

def monitor_main(host_id, system, community):
    # try:
    monit = Monitor()
    print(host_id)
    oids = sel_oids(system)
    if oids == None:
        value = None
    else:
        myq = monit.get_info(host_id, oids, community)
        value = monit.change(myq, oids)
    if value == None:
        pass
    else:
        data_in(host_id, value)


    # except Exception as e:
    #     logging.error("snmp error")
    #     print(e)

#创建线程
def select():
    select_sql = """select ip,system,community from bmc_admin_host"""
    cur.execute(select_sql)
    results = cur.fetchall()
    results = list(results)
    bmc_setting.host_info = results

def roll_polling(hostid,system,community,sec = 60):
    while True:
        monitor_main(hostid,system,community)
        time.sleep(sec)



def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")

def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)

def create_thread():
    while True:
        select()
        thread_list = []
        for i in range(len(bmc_setting.host_info)):
            host_id = bmc_setting.host_info[i][0]
            community = bmc_setting.host_info[i][2]
            system = bmc_setting.host_info[i][1]
            thread = threading.Thread(target=roll_polling,args=(host_id,system,community,bmc_setting.collect_time))
            thread_list.append(thread)
            logging.info("create thread")
            thread.start()
        for i in thread_list:
            time.sleep(bmc_setting.reload_time)
            print("main thread sleep finish")
            stop_thread(i)

        continue



if __name__ == "__main__":
    logging.info("collect start")
    create_thread()
