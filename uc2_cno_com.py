#################################################################################
# The O-CNO arbitrator algorithm for the UC2 multi-session scenario
# Author:      Morteza Kheirkhah
# Institution: University College London (UCL), UK
# Email:       m.kheirkhah@ucl.ac.uk
# Homepage:    http://www.uclmail.net/users/m.kheirkhah/
#################################################################################
import os
import sys
import json
from kafka import KafkaConsumer, KafkaProducer
from uc2_settings import KAFKA_SERVER, \
    KAFKA_CLIENT_ID, \
    KAFKA_API_VERSION, \
    KAFKA_MONITORING_TOPICS, \
    KAFKA_EXECUTION_TOPIC
from uc2_daemon import get_kafka_producer, write_kafka_uc2_cno

import csv
from pathlib import Path
from uc2_daemon import *

KAFKA_TOPIC = "uc2_cno"
DEFAULT_BW = 20

def reset_tc(default_bw):
    print("reset tc rate to the default ---> {0}mbps".format(default_bw))
    msg_egress = "sudo tc qdisc replace dev ens4 root tbf rate " + str(default_bw) + "mbit burst 32kbit latency 400ms"
    os.system(msg_egress)
    # msg_1 = "sudo tc qdisc replace dev ens3 root tbf rate " + str(default_bw) + "mbit burst 32kbit latency 400ms"
    # msg_2 = "sudo tc qdisc replace dev ifb0 root tbf rate " + str(default_bw) + "mbit burst 32kbit latency 400ms"
    # os.system(msg_1)
    # os.system(msg_2)

    
def change_tm_bw(bw):
    print("change_tm_bw ---> {0}mbps".format(bw))
    msg_egress = "sudo tc qdisc replace dev ens4 root tbf rate " + str(bw) + "mbit burst 32kbit latency 400ms"
    os.system(msg_egress)
    # msg_1 = "sudo tc qdisc replace dev ens3 root tbf rate " + str(bw) + "mbit burst 32kbit latency 400ms"
    # msg_2 = "sudo tc qdisc replace dev ifb0 root tbf rate " + str(bw) + "mbit burst 32kbit latency 400ms"
    # os.system(msg_1)
    # os.system(msg_2)
    return bw

def main():
    try:
        default_bw = sys.argv[1]
    except Exception as ex:
        print (ex, "\nNo input from cmd, we use the default rate '{0}'".format(DEFAULT_BW))
        default_bw = DEFAULT_BW

    reset_tc(default_bw)
    consumer = get_kafka_consumer(KAFKA_TOPIC)
    producer = get_kafka_producer()
    print("Listening to kafka topic", KAFKA_MONITORING_TOPICS[KAFKA_TOPIC])
    bw = 0
    last_bw = bw
    for msg in consumer:
        if (msg.value["sender"] == 'UC_2' and msg.value["receiver"] == 'O-CNO' and msg.value["option"] == 'request'):
            print (msg.value)
            bw = msg.value["resource"]["bw"]
            if (last_bw != bw):
                last_bw = change_tm_bw(bw)
                write_kafka_uc2_cno(producer, "respond", last_bw)
                bw = 0
                f = open('uc2_cno_com.log', 'a')
                f.write(str(msg))
                f.write('\n')
                f.close()
                    
if __name__ == '__main__':
    main()
