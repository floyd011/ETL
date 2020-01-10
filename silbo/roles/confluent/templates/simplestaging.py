#!/usr/bin/env python
import json, decimal, datetime
import errno
import fcntl
import sys
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
index, data = c.kv.get(DBSOURCE+'/BULK_STAGING', index=None)
BULK_STAGING=int(data['Value'].decode()) if data['Value'] is not None else ''

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

    
class readThread (threading.Thread):

    def __init__(self, threadID, sdict):

        threading.Thread.__init__(self)
        self.shutdown_flag = threading.Event()
        self.threadID = threadID
        self.sdict = sdict 
        db_name, schema_name, table_name = self.sdict.split('.')
        self.t = Table(table_name, meta, autoload_with=db, schema=schema_name)
        exceptions = json.loads(EXCEPTIONS)
        col_list = []
        distributed_keys = []
        primary_keys = [key.name for key in inspect(self.t).primary_key]
        if len(primary_keys) == 0:
            aopk = exceptions[self.sdict]['Primary_keys'].split(',')
            aodk = exceptions[self.sdict]['Distribution_keys'].split(',')
            res = [primary_keys.append(x) for x in aopk]
            res = [distributed_keys.append(x) for x in aodk]
            cte_partition_keys = [key for key in primary_keys]
        else:
            cte_partition_keys = [key.name for key in inspect(self.t).primary_key]
        cte_partition_set = ','.join(cte_partition_keys)
        pk_set = ','.join(primary_keys)
        nm = list(x['name'] for x in inspector.get_columns(table_name))
        cte_set = ','.join(nm)
        nm.append('koffset')
        type_list = list(x['type'] for x in inspector.get_columns(table_name))
        type_list.append('BIGINT')
        self.col = dict(list(zip(nm,type_list)))
        col_list = list(x['name'] for x in inspector.get_columns('temp_' + table_name, 'staging') if x['name'] != 'ins_date')
        name_list = ['"' + x + '"' for x in col_list]
        column_set = ','.join(name_list)
        value_list = ['v.' + x for x in col_list]
        value_set = ','.join(value_list)
        c = list(zip(name_list,value_list))
        ins_stmt = "insert into {} select {} from staging.temp_{} where id_seq > %d and id_seq <= %d and kafka_op != 'd'"        
        self.insert = ins_stmt.format(table_name,cte_set,table_name)
        del_stmt = "delete from {} t where exists (select {} from staging.temp_{} v  where {} and id_seq > %d and id_seq <= %d)"
        del_staging = "delete from staging.temp_{}  where id_seq > %d "
        self.del_staging = del_staging.format(table_name)
        self.delete = del_stmt.format(table_name,cte_partition_set,table_name,inner_str(primary_keys))
        self.maxid_seq = "with cte as (select id_seq from staging.{} where id_seq > %d ORDER BY id_seq LIMIT %d) select max(id_seq) maxid_seq from cte".format(table_name)
        preparecommand = "INSERT INTO staging.temp_{} ({}) select * from (with cte as (select *, ROW_NUMBER() OVER(PARTITION BY {} ORDER BY kafka_lsn desc) rn from staging.{} where id_seq > %d and id_seq <= %d), v as (select {} from cte v where rn = 1), t as (select t.id id, max(t.kafka_lsn) kafka_lsn from staging.temp_{} t inner join v on {} group by t.id) select v.* from v left outer join t on {} where {} or (v.kafka_lsn > t.kafka_lsn)) z"
        self.select = preparecommand.format(table_name,column_set,cte_partition_set,table_name,value_set,table_name,inner_str(primary_keys),inner_str(primary_keys),left_str(primary_keys))
        self.conn = conn
        self.ord_col = nm      
         
            
    def run(self):
        try:    
            logging.warning('Started %s Topic: %s' % (self.getName(), self.sdict))

            start_time = time.time()
    
            while not self.shutdown_flag.is_set():
                
                ret = self.write_database(start_time)
                start_time = time.time()

                time.sleep(1.5)

        except Exception as e:
            logging.warning('Error in %s Topic: %s , error: %s' % (self.getName(), self.sdict, e))
        finally:
            logging.warning('Stopped %s Topic: %s' % (self.getName(), self.sdict))

    def write_database(self, start_time):
    
        c_insert = 0
        c_delete = 0 
        c_select = 0      
        lsn = 0
        maxlsn = 0
        try:
            cursor = conn.execution_options(autocommit=True).execute("SELECT id_seq FROM staging.table_offsets WHERE table_name = '{}'".format(self.sdict))
            for row in cursor:
                id_seq = row['id_seq']
            if id_seq is None:
                id_seq = 0
            w_cmd = self.maxid_seq
            cursor.close()
            w_cmd = w_cmd % (id_seq,BULK_STAGING)
            cursor = conn.execution_options(autocommit=True).execute(w_cmd)
            for row in cursor:
                maxid_seq = row['maxid_seq']   
            if maxid_seq is None:
                return 0  
            cursor.close()    
            w_cmd = self.del_staging
            w_cmd = w_cmd % (id_seq)
            cursor = conn.execution_options(autocommit=True).execute(w_cmd)
            rt = cursor.rowcount
            cursor.close()
            w_cmd = self.select
            w_cmd = w_cmd % (id_seq,maxid_seq)
            cursor = conn.execution_options(autocommit=True).execute(w_cmd)
            rt = cursor.rowcount
            if rt == -1:
                return 1
            cursor.close()
            c_select += rt
            w_cmd = self.delete
            w_cmd = w_cmd % (id_seq,maxid_seq)
            cursor = conn.execution_options(autocommit=True).execute(w_cmd)
            rt = cursor.rowcount
            if rt == -1:
                return 1
            cursor.close()
            c_delete += rt
            w_cmd = self.insert
            w_cmd = w_cmd % (id_seq,maxid_seq)
            cursor = conn.execution_options(autocommit=True).execute(w_cmd)
            rt = cursor.rowcount
            if rt == -1:
                return 1
            cursor.close()
            c_insert += rt
            w_cmd = "UPDATE staging.table_offsets SET id_seq = %d WHERE table_name = '{}'".format(self.sdict)
            w_cmd = w_cmd % (maxid_seq)
            cursor = conn.execution_options(autocommit=True).execute(w_cmd)
            rt = cursor.rowcount
            if rt == -1:
                return 1
            cursor.close()
            duration = time.time() - start_time
            logging.info("%s, Selected: %d, Deleted: %d, Inserted: %d, Duration batch: %f" % (self.sdict, c_select, c_delete, c_insert,  duration ))
            return 0

        except Exception as e:
            logging.error(e)
            return 1
                   
        
class ServiceExit(Exception):
    """
    Custom exception which is used to trigger the clean exit
    of all running threads and the main program.
    """
    pass

     
def service_shutdown(signum, frame):
  
    if signum == 2 or signum == 15:
        logging.info('Caught signal %d' % signum)
        raise ServiceExit
                       
def main():        
      		
    try:
        
        signal.signal(signal.SIGTERM, service_shutdown)
        signal.signal(signal.SIGINT, service_shutdown)
        signal.signal(signal.SIGUSR1, service_shutdown)
        signal.signal(signal.SIGUSR2, service_shutdown)

        readthreadID = 1

        if TOPIC == "":
            topic_set = STAGING_TABLES.split(',')                   
        else:
            topic_set = TOPIC.split(',')

        logger = logging.getLogger(__name__)
        coloredlogs.install(level='INFO')
        
        exclude_set = EXCLUDE.split(',')
        staging_set = STAGING_TABLES.split(',')
        
        for i in topic_set:
            if i not in exclude_set and i in staging_set:
                time.sleep(1)           
                readt = readThread(readthreadID, i)
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





