import pymysql
import logging
from monitor.collect.setting import Settings
logging.basicConfig(filename='collect_log.txt',level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')

def connect_db():
    bmc_setting = Settings()
    db = pymysql.connect(user=bmc_setting.data_user,
                         passwd=bmc_setting.data_passwd,
                         db=bmc_setting.data_base,
                         host=bmc_setting.data_host
                                 )
    db.autocommit(True)
    logging.info("database connect")
    cur = db.cursor()
    return db ,cur


# insert_sql = """select into test(host_id,mem_total, mem_free, free_cpu_percent, use_time,in_time)
#                                             values(%s, %s, %s, %s, %s, %s)"""
#     cur.execute(insert_sql, (hostid, memtotal, memfree, freecpupercent, usetime, time_now))
