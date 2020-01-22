#!/usr/bin/env python
import ujson
import decimal
import datetime as datewtz
from datetime import datetime as tzdate
import errno
import fcntl
import sys
import pykafka
from pykafka import KafkaClient
import time
import threading
import coloredlogs, logging
import copy
import os
import string
import signal
import base64
from os import environ
import sqlalchemy as sa
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, create_engine, text, inspect
from geoalchemy2 import Geometry
from sqlalchemy.exc import StatementError
from shapely.wkb import loads
from shapely.geometry import MultiPolygon, mapping
from pykafka.exceptions import ConsumerStoppedException
import consul

CONSUL_SERVER=os.environ['CONSUL_SERVER'].replace('"', '').replace("'", '')
CONSUL_PORT=int(os.environ['CONSUL_PORT'].replace('"', '').replace("'", ''))
DBSOURCE=os.environ['DBSOURCE'].replace('"', '').replace("'", '')

c = consul.Consul(host=CONSUL_SERVER, port=CONSUL_PORT)

index, data = c.kv.get(DBSOURCE+'/STAGING_TABLES', index=None)
STAGING_TABLES=data['Value'].decode() if data['Value'] is not None else ''
index, data = c.kv.get(DBSOURCE+'/SAVETIME', index=None)
SAVETIME=int(data['Value'].decode()) if data['Value'] is not None else ''
index, data = c.kv.get(DBSOURCE+'/CONSUMER_GROUP', index=None)
CONSUMER_GROUP=data['Value'].decode() if data['Value'] is not None else '' 
index, data = c.kv.get(DBSOURCE+'/EXCEPTIONS', index=None)
EXCEPTIONS=data['Value'].decode() if data['Value'] is not None else ''  
index, data = c.kv.get(DBSOURCE+'/PAUSED', index=None)
PAUSED=data['Value'].decode() if data['Value'] is not None else ''  
index, data = c.kv.get(DBSOURCE+'/INITIAL', index=None)
INITIAL=data['Value'].decode() if data['Value'] is not None else ''
index, data = c.kv.get(DBSOURCE+'/TOPIC', index=None)
TOPIC=data['Value'].decode() if data['Value'] is not None else ''
index, data = c.kv.get(DBSOURCE+'/KAFKA_SERVER', index=None)
KAFKA_SERVER=data['Value'].decode() if data['Value'] is not None else ''
index, data = c.kv.get(DBSOURCE+'/DBNAME', index=None)
DBNAME=data['Value'].decode() if data['Value'] is not None else ''
index, data = c.kv.get(DBSOURCE+'/USER', index=None)
USER=data['Value'].decode() if data['Value'] is not None else ''
index, data = c.kv.get(DBSOURCE+'/PASS', index=None)
PASS=data['Value'].decode() if data['Value'] is not None else ''
index, data = c.kv.get(DBSOURCE+'/DBSERVER', index=None)
DBSERVER=data['Value'].decode() if data['Value'] is not None else ''
index, data = c.kv.get(DBSOURCE+'/DBPORT', index=None)
DBPORT=int(data['Value'].decode()) if data['Value'] is not None else ''
index, data = c.kv.get(DBSOURCE+'/DATABASE', index=None)
DATABASE=data['Value'].decode() if data['Value'] is not None else ''
index, data = c.kv.get(DBSOURCE+'/EXCLUDE', index=None)
EXCLUDE=data['Value'].decode() if data['Value'] is not None else ''
index, data = c.kv.get(DBSOURCE+'/COLOREDLOGS_LEVEL_STYLES', index=None)
index, data = c.kv.get(DBSOURCE+'/BULK', index=None)
BULK=int(data['Value'].decode()) if data['Value'] is not None else ''
os.environ["COLOREDLOGS_LEVEL_STYLES"] = data['Value'].decode() if data['Value'] is not None else ''
index, data = c.kv.get(DBSOURCE+'/COLOREDLOGS_LOG_FORMAT', index=None)
os.environ["COLOREDLOGS_LOG_FORMAT"] = data['Value'].decode() if data['Value'] is not None else ''
db_string="postgres://%s:%s@%s:%d/%s" % (USER,PASS,DBSERVER,DBPORT,DBNAME)
db=create_engine(db_string)
conn=db.connect()
meta=MetaData()
meta.reflect(bind=db)
inspector = inspect(db)
reads = []
readthreadID=1
sql_dict={}

def write_database(retval, sql_dict, start_time, table):
    
    db_name, schema_name, table_name = table.split('.')
    if len(retval[1]) > 0:
        row_str = '[' + ','.join(retval[1]) + ']'
        row_str = row_str.replace("[b'{",'[{').replace("}']",'}]').replace("}',b'{",'}, {')
        w_cmd = sql_dict[table.rsplit('.', 1)[1]]['insert']
        w_cmd = w_cmd % (row_str)
        w_cmd = w_cmd.replace("%", '%%')        
        rt = execute_sql(w_cmd)
        if rt == -1:
            return 1
    duration = time.time() - start_time
    logging.info("%s - Last Commited offset: %d, Last tx time: %s, Duration batch: %f, Counted: %d" % (table, retval[5], retval[4], duration, retval[6] ))
    return 0

def db_section(sdict):

    try:
        global sql_dict
        db_name, schema_name, table_name = sdict.split('.')
        t = Table(table_name, meta, autoload_with=db, schema=schema_name)
        primary_keys = [key.name for key in inspect(t).primary_key]
        exceptions = ujson.loads(EXCEPTIONS)
        if len(primary_keys) == 0:
            aopk = exceptions[sdict]['Primary_keys'].split(',')
            res = [primary_keys.append(x) for x in aopk]
        pk_set = ','.join(primary_keys)
        nm = list(x['name'] for x in inspector.get_columns(table_name))
        nm.append('koffset')
        nm.append('kafka_part')
        nm.append('kafka_lsn')
        nm.append('kafka_op')
        name_list = ['"' + x + '"' for x in nm]
        column_set = ','.join(name_list)
        type_list = list(x['type'] for x in inspector.get_columns(table_name))
        type_list.append('BIGINT')
        type_list.append('INT')
        type_list.append('BIGINT')  
        type_list.append('VARCHAR')  
        check_type = "SELECT 1 FROM pg_type WHERE typname = 't_{}'".format(table_name)
        cursor = conn.execute(check_type)
        if cursor.rowcount != 1:
            drop_type = 'DROP TYPE IF EXISTS t_{}'.format(table_name)
            conn.execute(drop_type)
            create_type = 'CREATE TYPE t_{} AS ('
            for i in range(0,len(nm)):
                create_type += nm[i] + ' ' + str(type_list[i]) + ','
            create_type = create_type[:-1] + ')'
            create_type = create_type.format(table_name)
            conn.execute(create_type)
        check_table = "SELECT 1 FROM   information_schema.tables WHERE  table_schema = 'staging' AND    table_name = '{}'".format(table_name)
        cursor = conn.execute(check_table)
        if cursor.rowcount != 1:        
            drop_table = 'DROP TABLE IF EXISTS staging.{}'.format(table_name)
            conn.execute(drop_table)
            create_table = 'CREATE TABLE staging.{} ( id_seq bigserial not null primary key, '
            for i in range(0,len(nm)):
                create_table += nm[i] + ' ' + str(type_list[i]) + ','
            create_table = create_table[:-1] + ')'
            create_table = create_table.format(table_name)
            conn.execute(create_table)
        check_table = "SELECT 1 FROM   information_schema.tables WHERE  table_schema = 'staging' AND    table_name = 'temp_{}'".format(table_name)
        cursor = conn.execute(check_table)
        if cursor.rowcount != 1:        
            drop_table = 'DROP TABLE IF EXISTS staging.temp_{}'.format(table_name)
            conn.execute(drop_table)
            create_table = 'CREATE TABLE staging.temp_{} ( ins_date date not null default CURRENT_DATE, id_seq bigint, '
            for i in range(0,len(nm)):
                create_table += nm[i] + ' ' + str(type_list[i]) + ','
            create_table = create_table[:-1] + ')'
            create_table = create_table.format(table_name)
            conn.execute(create_table)
            create_index = 'CREATE INDEX temp_{}_pkey ON staging.temp_{} USING btree ({})'
            create_index = create_index.format(table_name, table_name,pk_set)
            conn.execute(create_index)
            create_index = 'CREATE INDEX temp_{}_idseq ON staging.temp_{} USING btree (id_seq)'
            create_index = create_index.format(table_name, table_name)
            conn.execute(create_index)
            create_index = 'CREATE INDEX temp_{}_cdate ON staging.temp_{} USING btree (ins_date)'
            create_index = create_index.format(table_name, table_name)
            conn.execute(create_index)
        sql_dict[table_name] = {}
        sql_dict[table_name]['insert'] = "INSERT INTO staging.{} ({}) select * from json_populate_recordset(null::t_{}, E'%s')".format(table_name,column_set,table_name)
    except:
        logging.warning('Error in created table: %s ' % (sdict))
        
        
class readThread (threading.Thread):

    def __init__(self, threadID, c, sdict, topic):

        threading.Thread.__init__(self)
        self.shutdown_flag = threading.Event()
        self.pause_flag = threading.Event()
        self.threadID = threadID
        self.sdict = sdict 
        self.c = c
        self.topic = topic
        self.consumer = topic.get_balanced_consumer(consumer_group=CONSUMER_GROUP,consumer_timeout_ms=5000, auto_commit_enable=False,use_rdkafka = True)
            
    def run(self):
        try:    
            logging.warning('Started %s Topic: %s' % (self.getName(), self.sdict))
            global PAUSED
             #self.consumer.start()
            start_time = time.time()
            retval = [ [],[],[], False, 0,0,0]
    
            while not self.shutdown_flag.is_set():
            
                if self.pause_flag.is_set():
    
                    index, data = self.c.kv.get(DBSOURCE+'/PAUSED', index=None)
                    PAUSED=data['Value'].decode() if data['Value'] is not None else ''
                    self.pause_flag.clear()
                    if self.sdict in PAUSED or PAUSED == '*':
                        logging.warning('Paused in %s Topic: %s' % (self.getName(), self.sdict))
    
                if PAUSED != '*':     
                    if self.sdict not in PAUSED:
                        retval = self.export(retval, start_time)
                        
                        duration = time.time() - start_time
                        if duration > SAVETIME or retval[3]:
                            if len(retval[1]) > 1 or len(retval[2]) > 1:
                                ret = write_database(retval, sql_dict, start_time, self.sdict)
                                if ret != 0:
                                    PAUSED += self.sdict
                                    logging.warning('PAUSED %s Topic: %s - error in data' % (self.getName(), self.sdict))
                                else:
                                    self.consumer.commit_offsets(retval[0]) 
                            else:
                                logging.warning('NO MESSAGES %s Topic: %s ' % (self.getName(), self.sdict))
                            start_time = time.time()
                            retval = [ [],[],[], False, 0,0,0]
                time.sleep(1)
            if len(retval[1]) > 0 or len(retval[2]) > 0:
                ret = write_database(retval, sql_dict, start_time, self.sdict)
                if ret == 0:
                    self.consumer.commit_offsets(retval[0]) 
        except pykafka.exceptions as e:
            logging.warning('Error in Thread %s Topic: %s , error: %s' % (self.getName(), self.sdict, e))
        finally:
            #self.consumer.stop()
            logging.warning('Stopped %s Topic: %s ' % (self.getName(), self.sdict))

    def export(self, retval, start_time):
    
        count = retval[6]
        offset_list = retval[0]
        row_list = retval[1]
        del_list = retval[2]
        ret_bulk = retval[3]
        ts = retval[4]
        offset = retval[5]
        ret_list = []
        try:
            for message in self.consumer:
                duration = time.time() - start_time
                
                if duration > SAVETIME:
                    break
                if message is not None:
                    offset = message.offset
                    if message.value is not None:
                        msg_json = ujson.loads(message.value.decode("utf-8"))
                        
                        action = msg_json["payload"]["op"]
                        
                        date = datewtz.datetime.utcfromtimestamp(msg_json["payload"]['source']["ts_ms"]/1000.0)
                        ts = date.strftime('%Y-%m-%d %H:%M:%S')
                        if action == 'u':
                            _action = "after"
                        else:
                            _action = "before"
                        #logging.warning('EXPORT %s Action %s ts %s ' % (msg_json, action, ts))
                        for r in msg_json["schema"]["fields"][0]["fields"]:
                            if 'name' in r and r["name"] == 'io.debezium.data.Json'  and msg_json["payload"][_action][r["field"]] is not None:
                                #print(json.loads(msg_json["payload"][_action][r["field"]]))
                                #print(msg_json["payload"][_action][r["field"]])
                                tmp = str(msg_json["payload"][_action][r["field"]]).replace(chr(92),'')
                                tmp = tmp.replace('""','')
                                tmp = tmp.replace('"','\'')
                                tmp = tmp.strip("'")
                                if tmp == '':
                                   tmp = '{}'
                                msg_json["payload"][_action][r["field"]]  = tmp.replace("'", '"')
                        if 'name' in r and r["name"] == 'io.debezium.time.Date' and msg_json["payload"][_action][r["field"]] is not None:
                            msg_json["payload"][_action][r["field"]] = serial_date_to_string(msg_json["payload"][_action][r["field"]])
                        if 'name' in r and r["name"] == 'io.debezium.time.ZonedTimestamp' and msg_json["payload"][_action][r["field"]] is not None:
                            if "." in msg_json["payload"][_action][r["field"]]:
                                msg_json["payload"][_action][r["field"]] = str(tzdate.strptime(msg_json["payload"][_action][r["field"]], '%Y-%m-%dT%H:%M:%S.%fZ'))
                            else:
                                msg_json["payload"][_action][r["field"]] = str(tzdate.strptime(msg_json["payload"][_action][r["field"]], '%Y-%m-%dT%H:%M:%SZ'))
                        if 'name' in r and r["name"] == 'io.debezium.time.MicroTimestamp' and msg_json["payload"][_action][r["field"]] is not None:
                            date = datewtz.datetime.utcfromtimestamp(msg_json["payload"][_action][r["field"]]/1000000.0)
                            date = date.strftime('%Y-%m-%d %H:%M:%S.%f')
                            msg_json["payload"][_action][r["field"]] = date
                        if 'name' in r and r["name"] == 'io.debezium.time.MicroTime' and msg_json["payload"][_action][r["field"]] is not None:
                            date = datewtz.datetime.utcfromtimestamp(msg_json["payload"][_action][r["field"]]/1000000.0)
                            date = date.strftime('%H:%M:%S')
                            msg_json["payload"][_action][r["field"]] = date
                        if 'name' in r and r["name"] == 'io.debezium.data.geometry.Geography' and msg_json["payload"][_action][r["field"]] is not None:
                                image_wkb =  base64.b64decode(msg_json["payload"][_action][r["field"]]["wkb"]).hex()
                                geometry = loads(image_wkb, hex = True)
                                msg_json["payload"][_action][r["field"]] = geometry.wkt
                        msg_val = msg_json["payload"][_action]
                        
                        count += 1
                        part = self.topic.partitions[message.partition_id]
                        offset_list.append(tuple((part, message.offset)))
                        msg_val['koffset'] = message.offset
                        msg_val['kafka_part'] = message.partition_id
                        msg_val['kafka_lsn'] = msg_json["payload"]['source']["lsn"]
                        msg_val['kafka_op'] = msg_json["payload"]["op"]
                        lv = str(ujson.dumps(msg_val, ensure_ascii=False).encode('utf-8'))
                        
                        if action == 'd':
                            del_list.append(lv)
                        else:
                            row_list.append(lv)
                        if count > BULK:
                            ret_bulk = True
                            break
        except pykafka.exceptions as e:
            logging.warning('Error in Thread %s Topic: %s , error: %s' % (self.getName(), self.sdict, e))
        finally:                 
            ret_list.append(offset_list)
            ret_list.append(row_list) 
            ret_list.append(del_list) 
            ret_list.append(ret_bulk) 
            ret_list.append(ts)
            ret_list.append(offset) 
            ret_list.append(count)
            return ret_list

class ServiceExit(Exception):
    """
    Custom exception which is used to trigger the clean exit
    of all running threads and the main program.
    """
    pass

def addRemove_table(table_set):

    global readthreadID
    global reads
    
    for i in reads:
        if i.sdict in table_set:
            table_set.remove(i.sdict)
            i.shutdown_flag.set()
            i.join()

          
    for i in table_set:
        if i not in EXCLUDE:
            time.sleep(1)
            readt = readThread(readthreadID, c, i)
            readt.start()
            reads.append(readt)
            readthreadID += 1
      
def service_shutdown(signum, frame):
  
    if signum == 10:
        logging.info('Caught signal %d' % signum)
        for i in reads:
            i.pause_flag.set()

    if signum == 12:

        logging.info('Caught signal %d' % signum)
        index, data = c.kv.get(DBSOURCE+'/TABLE', index=None)
        TABLE = data['Value'].decode() if data['Value'] is not None else ''
        table_set = TABLE.split(',')
        addRemove_table(table_set)

    if signum == 2 or signum == 15:
        logging.info('Caught signal %d' % signum)
        raise ServiceExit

def serial_date_to_string(srl_no):
    new_date = datewtz.datetime(1970,1,1,0,0) + datewtz.timedelta(srl_no)
    return new_date.strftime("%Y-%m-%d")

def execute_sql(w_cmd):

    try:
        crs = conn.execution_options(autocommit=True).execute(w_cmd)
        return crs.rowcount
    except:
        logging.error(w_cmd)
        return -1
                       
def main():        
      		
    try:
        
        signal.signal(signal.SIGTERM, service_shutdown)
        signal.signal(signal.SIGINT, service_shutdown)
        signal.signal(signal.SIGUSR1, service_shutdown)
        signal.signal(signal.SIGUSR2, service_shutdown)

        readthreadID = 1

        client = KafkaClient(hosts=KAFKA_SERVER)

        if TOPIC == "":
            topic_set = set(x.decode('utf-8') for x in client.topics.keys() if DATABASE in x.decode('utf-8'))                   
        else:
            topic_set = TOPIC.split(',')
        
        exclude_set = EXCLUDE.split(',')
        staging_set = STAGING_TABLES.split(',')
        logger = logging.getLogger(__name__)
        coloredlogs.install(level='INFO')
    
        for i in topic_set:
            if i not in exclude_set and i in staging_set:
                topic = client.topics[i.encode('UTF-8')]
                time.sleep(1)
                db_section(i)
                readt = readThread(readthreadID, c, i, topic)
                readt.start()
                reads.append(readt)
                readthreadID += 1
   
        logging.info('Started main program')        
           
        while True:
            time.sleep(0.5)
            
    except ServiceExit:

        for i in reads:
            i.shutdown_flag.set()
            i.join()
            readthreadID -= 1
        conn.close()
        
    logging.info('Exit main program')

if __name__ == "__main__":
    main()






