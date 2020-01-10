#!/usr/bin/env python
import json, decimal, datetime
import errno
import fcntl
import sys
import pykafka
from pykafka import KafkaClient
from pykafka.simpleconsumer import OwnedPartition, OffsetType
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
terminate = False
listcons = []
tables = []
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
stored_exception=None


def inner_str(pk):

    key_list = ['t."' + x + '"' for x in pk]
    keyvalue_list = ['v.' + x for x in pk]
    k = list(zip(key_list,keyvalue_list))
    comp_value = [' = '.join(tups) for tups in k]
    comp_list = [z + ' AND ' for z in comp_value]
    comp_str = ' '.join(comp_list).strip(' AND ')
    return comp_str 

def left_str(pk):

    key_list = ['t."' + x + '"' for x in pk]
    comp_value = [tups + ' is null ' for tups in key_list]
    comp_list = [z + ' AND ' for z in comp_value]
    comp_str = ' '.join(comp_list).strip(' AND ')
    return comp_str 


def write_database(retval, sql_dict, start_time, table):

    c_insert = 0
    c_update = 0 
    c_delete = 0       
    
    if len(retval[1]) > 0:
        row_str = '[' + ','.join(retval[1]) + ']'
        row_str = row_str.replace("[b'{",'[{').replace("}']",'}]').replace("}',b'{",'}, {')
        w_cmd = sql_dict[table.rsplit('.', 1)[1]]['update']
        w_cmd = w_cmd % (row_str)
        w_cmd = w_cmd.replace("%", '%%')
        w_del = w_cmd + ';'
#        rt = execute_sql(w_cmd)
#        if rt == -1:
#            return 1
#        c_update += rt
        w_cmd = sql_dict[table.rsplit('.', 1)[1]]['insert']
        w_cmd = w_cmd % (row_str)
        w_cmd = w_cmd.replace("%", '%%')
        w_cmd = w_del + w_cmd
        rt = execute_sql(w_cmd)
        if rt == -1:
            return 1
        c_insert += rt
    if len(retval[2]) > 0:
        del_str = '[' + ','.join(retval[2]) + ']'
        del_str = del_str.replace("[b'{",'[{').replace("}']",'}]').replace("}',b'{",'}, {')
        w_cmd = sql_dict[table.rsplit('.', 1)[1]]['delete']
        w_cmd = w_cmd % (del_str)
        w_cmd  = w_cmd.replace("%", '%%')
        rt = execute_sql(w_cmd)
        if rt == -1:
            return 1
        c_delete += rt
    duration = time.time() - start_time
    logging.info("%s, Commited: %d, Deleted: %d, Last Commited offset: %d, Last tx time: %s, Duration batch: %f, Counted: %d" % (table, c_insert, c_delete, retval[5], retval[4], duration, retval[6] ))
    return 0


def db_section(sdict, topic):
    try:
        global sql_dict
        db_name, schema_name, table_name = sdict.split('.')
        t = Table(table_name, meta, autoload_with=db, schema=schema_name)
        exceptions = json.loads(EXCEPTIONS)
        col_list = []
        distributed_keys = []
        primary_keys = [key.name for key in inspect(t).primary_key]
        if len(primary_keys) == 0:
            aopk = exceptions[sdict]['Primary_keys'].split(',')
            aodk = exceptions[sdict]['Distribution_keys'].split(',')
            res = [primary_keys.append(x) for x in aopk]
            res = [distributed_keys.append(x) for x in aodk]
            cte_partition_keys = [key for key in primary_keys]
        else:
            cte_partition_keys = [key.name for key in inspect(t).primary_key]
        cte_partition_set = ','.join(cte_partition_keys)
        pk_set = ','.join(primary_keys)
        nm = list(x['name'] for x in inspector.get_columns(table_name))
        cte_set = ','.join(nm)
        nm.append('koffset')
        nm.append('kafka_part')
        nm.append('kafka_lsn')
        nm.append('kafka_op')
        type_list = list(x['type'] for x in inspector.get_columns(table_name))
        type_list.append('BIGINT')
        type_list.append('INT')
        type_list.append('BIGINT')  
        type_list.append('VARCHAR') 
        col = dict(list(zip(nm,type_list)))
        col_list = list(x['name'] for x in inspector.get_columns(table_name) if x['name'] not in primary_keys and x['name'] not in distributed_keys)
        name_list = ['"' + x + '"' for x in col_list]
        column_set = ','.join(name_list)
        name_set = ','.join(nm)
        value_list = ['v.' + x for x in col_list]
        value_set = ','.join(value_list)
        c = list(zip(name_list,value_list))
        up_value = [' = '.join(tups) for tups in c]
        upd_stmt = "delete from {} t using  (with cte as (select *, ROW_NUMBER() OVER(PARTITION BY {} ORDER BY koffset desc) rn from json_populate_recordset(null::t_{}, E'%s') ) select {} from cte  where rn = 1) v where {}"
        update = upd_stmt.format(table_name,cte_partition_set,table_name,cte_set,inner_str(primary_keys))
        ins_stmt = "insert into {} select v.* from (with cte as (select *, ROW_NUMBER() OVER(PARTITION BY {} ORDER BY koffset desc ) rn from json_populate_recordset(null::t_{}, E'%s') ) select {} from cte  where rn = 1) v "        
        insert = ins_stmt.format(table_name,cte_partition_set,table_name,cte_set)
        del_stmt = "delete from {} t using (with cte as (select *, ROW_NUMBER() OVER(PARTITION BY {} ORDER BY koffset desc) rn  from from json_populate_recordset(null::t_{}, E'%s')) select {} from cte  where rn = 1) v where {}"
        delete = del_stmt.format(table_name,cte_partition_set,table_name,cte_set,inner_str(primary_keys))
        ord_col = nm      
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
        sql_dict[table_name] = {}
        sql_dict[table_name]['update'] = update
        sql_dict[table_name]['insert'] = insert
        sql_dict[table_name]['delete'] = delete
        if INITIAL == "Y":
            consumer = topic.get_simple_consumer(consumer_group=CONSUMER_GROUP,consumer_timeout_ms=5000, auto_commit_enable=False,use_rdkafka = False, auto_offset_reset=OffsetType.EARLIEST, reset_offset_on_start=True)
        else:
            consumer = topic.get_simple_consumer(consumer_group=CONSUMER_GROUP,consumer_timeout_ms=5000, auto_commit_enable=False,use_rdkafka = False)
        consumer.start()
        listcons.append(tuple((consumer, sdict)))
        logging.warning('Created DML for table: %s ' % (sdict))
        
    except:
        logging.warning('Error in created table: %s ' % (sdict))
        
            
def ReadConsumer(c, consumer, sdict):
    
    global PAUSED
        
    try:
        start_time = time.time()
        retval = [ [],[],[], False, 0,0,0]

        index, data = c.kv.get(DBSOURCE+'/PAUSED', index=None)
        PAUSED=data['Value'].decode() if data['Value'] is not None else ''
        if sdict in PAUSED or PAUSED == '*':
            logging.warning('Paused in Topic: %s' % (sdict))
    
        if PAUSED != '*':     
            if sdict not in PAUSED:
                
                retval = export(consumer, retval, start_time)
                duration = time.time() - start_time
                if duration > SAVETIME or retval[3]:
                    if len(retval[1]) > 1 or len(retval[2]) > 1:
                        ret = write_database(retval, sql_dict, start_time, sdict)
                        if ret != 0:
                            PAUSED += sdict
                            logging.warning('PAUSED Topic: %s - error in data' % (sdict))
                        else:
                            consumer.commit_offsets(retval[0]) 
                    start_time = time.time()
                    retval = [ [],[],[], False, 0,0,0]
  
            if len(retval[1]) > 0 or len(retval[2]) > 0:
                ret = write_database(retval, sql_dict, start_time, sdict)
                if ret == 0:
                    consumer.commit_offsets(retval[0]) 
    except pykafka.exceptions as e:
        logging.warning('Error in Topic: %s, error: %s' % (sdict, e))
    except e:
        logging.warning('Error: %s ' % (e))


def export(consumer, retval, start_time):

    count = retval[6]
    offset_list = retval[0]
    row_list = retval[1]
    del_list = retval[2]
    ret_bulk = retval[3]
    ts = retval[4]
    offset = retval[5]
    ret_list = []
    try:
        for message in consumer:
            duration = time.time() - start_time
            if duration > SAVETIME:
                break
            if message is not None:
                offset = message.offset
                if message.value is not None:
                    msg_json = json.loads(message.value.decode("utf-8"))
                    action = msg_json["payload"]["op"]
                    date = datetime.datetime.utcfromtimestamp(msg_json["payload"]['source']["ts_usec"]/1000000.0)
                    ts = date.strftime('%Y-%m-%d %H:%M:%S')
                    if action == 'u':
                        _action = "after"
                    else:
                        _action = "before"
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
                        #if 'name' in r and r["name"] == 'io.debezium.time.Date' and msg_json["payload"][_action][r["field"]] is not None:
                        #    msg_json["payload"][_action][r["field"]] = serial_date_to_string(msg_json["payload"][_action][r["field"]])
                        #if 'name' in r and r["name"] == 'io.debezium.time.MicroTimestamp' and msg_json["payload"][_action][r["field"]] is not None:
                        #    date = datetime.datetime.utcfromtimestamp(msg_json["payload"][_action][r["field"]]/1000000.0)
                        #    date = date.strftime('%Y-%m-%d %H:%M:%S')
                        #    msg_json["payload"][_action][r["field"]] = date
                        #if 'name' in r and r["name"] == 'io.debezium.time.MicroTime' and msg_json["payload"][_action][r["field"]] is not None:
                        #    date = datetime.datetime.utcfromtimestamp(msg_json["payload"][_action][r["field"]]/1000000.0)
                        #    date = date.strftime('%H:%M:%S')
                        #    msg_json["payload"][_action][r["field"]] = date
                        if 'name' in r and r["name"] == 'io.debezium.data.geometry.Geography' and msg_json["payload"][_action][r["field"]] is not None:
                            image_wkb =  base64.b64decode(msg_json["payload"][_action][r["field"]]["wkb"]).hex()
                            geometry = loads(image_wkb, hex = True)
                            msg_json["payload"][_action][r["field"]] = geometry.wkt
                    msg_val = msg_json["payload"][_action]
                    count += 1
                    offset_list.append(tuple((message.partition, message.offset)))
                    msg_val['koffset'] = message.offset
                    msg_val['kafka_part'] = 0
                    msg_val['kafka_lsn'] = msg_json["payload"]['source']["lsn"]
                    msg_val['kafka_op'] = msg_json["payload"]["op"]
                    lv = str(json.dumps(msg_val, ensure_ascii=False).encode('utf-8'))
                    if action == 'd':
                        del_list.append(lv)
                    else:
                        row_list.append(lv)
                    if count > BULK:
                        ret_bulk = True
                        break
    except pykafka.exceptions as e:
        logging.warning('Error in Topic: %s , error: %s' % (sdict, e))
    except e:
        logging.warning('Error: %s ' % (e))
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
      
def service_shutdown(signum, frame):
  
    if signum == 2 or signum == 15:
        logging.info('Caught signal %d' % signum)
        global terminate                         
        terminate = True                         


def serial_date_to_string(srl_no):
    new_date = datetime.datetime(1970,1,1,0,0) + datetime.timedelta(srl_no)
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
            if i not in exclude_set and i not in staging_set:
                topic = client.topics[i.encode('UTF-8')]
                db_section(i, topic)
        
        logging.info('Started main program')
           
        while True:
            time.sleep(0.5)
            [ReadConsumer(c, x[0], x[1]) for x in listcons]
            if terminate:                                           
                break 
                        
    except KeyboardInterrupt:
        stored_exception=sys.exc_info()

    finally:
        [v[0].stop for v in listcons]
        conn.close()         
      
        logging.info('Exit main program')

if __name__ == "__main__":
    main()





