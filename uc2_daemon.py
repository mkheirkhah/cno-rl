import json
import calendar
import time
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer

from uc2_settings import KAFKA_SERVER, KAFKA_API_VERSION, \
    KAFKA_EXECUTION_TOPIC, KAFKA_MONITORING_TOPICS, \
    KAFKA_CLIENT_ID, KAFKA_SERVER, \
    METRIC_TEMPLATE_UC2_EXEC, \
    METRIC_TEMPLATE_UC2_VCE, \
    METRIC_TEMPLATE_UC2_CNO_REQUEST, \
    METRIC_TEMPLATE_UC2_CNO_RESPOND, \
    METRIC_TEMPLATE_UC2_TM
from uc2_metric_generator import generate_metric_uc2_exec, \
    generate_metric_uc2_vce, \
    generate_metric_uc2_cno, \
    generate_metric_uc2_tm


def get_msg_temp_uc2(topic="uc2_tm"):
    consumer = get_kafka_consumer(topic)
    print("get_message_tempplate({0})".format(topic))

    for msg in consumer:
        #print(msg.value)
        #print(msg.value.keys())
        if msg.value.get('metric')['unit'] == 'Mbps':
            if msg.value["metric"]["name"] == "bytes_sent":
                myoutput = msg.value.get('mano')['vdu']['ip_address'] + '\t' +  'timestamp' + "\t" + \
                    msg.value.get('metric')['timestamp'] + "\t" +  'value'+ "\t" + \
                    str(msg.value.get('metric')['value'])
                print(myoutput)
                return msg.value


def get_msg_temp_uc3(topic="uc3_load"):
    consumer = get_kafka_consumer(topic)
    print("get_message_tempplate({0})".format(topic))

    for msg in consumer:
        #print(msg.value)
        #print(msg.value.keys())
        if msg.value.get('metric')['unit'] == 'Mbps':
            if msg.value["metric"]["name"] == "bytes_sent":
                myoutput = msg.value.get('mano')['vdu']['ip_address'] + '\t' +  'timestamp' + "\t" + \
                    msg.value.get('metric')['timestamp'] + "\t" +  'value'+ "\t" + \
                    str(msg.value.get('metric')['value'])
                print(myoutput)
                return msg.value


def get_kafka_consumer(kafka_topic):
    consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_SERVER,
        client_id=KAFKA_CLIENT_ID,
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode('utf-8', 'ignore')),
        api_version=KAFKA_API_VERSION,
    )
    topic = KAFKA_MONITORING_TOPICS[kafka_topic]
    consumer.subscribe(pattern=topic)
    return consumer


def get_kafka_producer():
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_SERVER,
        api_version=KAFKA_API_VERSION,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'))
    return producer


def write_to_kafka(producer, value):
    try:
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        msg_temp = get_msg_temp_uc3()
        msg_temp.update(METRIC_TEMPLATE_UC2_EXEC)
        metric = generate_metric_uc2_exec(value, now, msg_temp)
        print(metric["execution"], metric["metric"]["timestamp"])
        t = producer.send(KAFKA_EXECUTION_TOPIC["exec_topic"], metric)
        result = t.get(timeout=60)
    except Exception as ex:
        print(ex)

def write_kafka_uc2_exec(producer, value, vce_id):
    try:
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        tmp_metric = METRIC_TEMPLATE_UC2_EXEC
        metric = generate_metric_uc2_exec(value, now, tmp_metric, vce_id)
        print("->", metric) #"write_kafka_uc2_exec() ->"
        t = producer.send(KAFKA_EXECUTION_TOPIC["uc2_exec"], metric)
        #print(KAFKA_EXECUTION_TOPIC["uc2_exec"])
        result = t.get(timeout=60)
    except Exception as ex:
        print (ex)

# res[vce, ts, br_min, br_max, capacity]
def write_kafka_uc2_vce(producer, res, vce_id, video_bit_rates, profile):
    try:
        # datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        now = res[1]
        tmp_metric = METRIC_TEMPLATE_UC2_VCE
        metric = generate_metric_uc2_vce(res, now, tmp_metric, vce_id, video_bit_rates, profile)
        # print("{0} <- {1}".format(KAFKA_EXECUTION_TOPIC["uc2_vce"], metric))
        t = producer.send(KAFKA_EXECUTION_TOPIC["uc2_vce"], metric)
        result = t.get(timeout=60)
    except Exception as ex:
        print (ex)


def write_kafka_uc2_cno(producer, msg_type, bw):
    try:
        now = calendar.timegm(time.gmtime())
        tmp_metric = ""
        metric = ""
        if (msg_type == "request"):
            tmp_metric = METRIC_TEMPLATE_UC2_CNO_REQUEST
            metric = generate_metric_uc2_cno(bw, now, tmp_metric, msg_type)
        elif(msg_type == "respond"):
            tmp_metric = METRIC_TEMPLATE_UC2_CNO_RESPOND
            metric = generate_metric_uc2_cno(bw, now, tmp_metric, msg_type)
            #
        assert(metric != "")
        print("{0} <- {1}".format(KAFKA_EXECUTION_TOPIC["uc2_cno"], metric))
        t = producer.send(KAFKA_EXECUTION_TOPIC["uc2_cno"], metric)
        result = t.get(timeout=60)
    except Exception as ex:
        print (ex)

def write_kafka_uc2_tm(producer, value, metric_type, unit):
    try:
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        metric_tmp = METRIC_TEMPLATE_UC2_TM
        metric = generate_metric_uc2_tm(value, now, metric_tmp, metric_type, unit)
        # print("{0} <- {1}".format(KAFKA_EXECUTION_TOPIC["uc2_tm"], metric))
        t = producer.send(KAFKA_EXECUTION_TOPIC["uc2_tm"], metric)
        result = t.get(timeout=60)
    except Exception as ex:
        print (ex)
