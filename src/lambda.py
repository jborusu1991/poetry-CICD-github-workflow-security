import json
import gzip
import base64
import stomp
import os
import logging
import traceback


AMQ_CONNECTION =os.environ['AMQ_CONNECTION'] 
AMQ_QUEUE_PREFIX=os.environ['AMQ_QUEUE_PREFIX']
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
ruleid=os.environ['RULE_INIT']
RULE_EXCLUDE_LIST = os.environ['RULE_EXCLUDE_LIST'] 

logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

def handler(event, context):
    try:
     amqconnection_server = AMQ_CONNECTION.split(',')
     connectionlist=[]
     for address in  amqconnection_server:
       amqconnection_server_port = address.split(':')
       connectionlist.append((amqconnection_server_port[0],int(amqconnection_server_port[1])))
     amq_queue =  AMQ_QUEUE_PREFIX +'.'+ruleid+'events'
     amq = stomp.Connection11(connectionlist,auto_content_length=False)  
     amq.connect(wait=True)
     logger.debug("event:"+ json.dumps(event))
     encoded_zipped_data = event['awslogs']['data']
     zipped_data = base64.b64decode(encoded_zipped_data)
     data = gzip.decompress(zipped_data)
     data = json.loads(data)
     logger.debug("data unzipped and decoded :"+ json.dumps(data))
     print(data['logEvents'])
     for events in data['logEvents']:
        logger.info("message:"+ events['message'])
        messagedata = json.loads(events['message'])
        component = messagedata['component']
        logger.info("component:"+ messagedata['component'])
        logger.info("id:"+ events['id'])  
        if (component not in RULE_EXCLUDE_LIST.split(',')):  
         msgheaders = { "JMSXGroupID": messagedata['component'], "elasticId": events['id'] }
         amq.send(amq_queue,events['message'],headers=msgheaders)
    except Exception as e:
     logger.error("error in processing the events"+traceback.format_exc())