import sys
import json
from kafka import KafkaConsumer, KafkaProducer
from uc2_settings import KAFKA_SERVER, KAFKA_CLIENT_ID, KAFKA_API_VERSION, \
    KAFKA_MONITORING_TOPICS, KAFKA_EXECUTION_TOPIC

import csv
from pathlib import Path
from uc2_daemon import *

TOPIC_DEFAULT = "uc2_tm"

def main():

    try:
        topic = sys.argv[1]
    except Exception as ex:
        print (ex, "\nNo input from cmd, we use the default topic '{0}'".format(TOPIC_DEFAULT))
        topic = TOPIC_DEFAULT
    
    consumer = get_kafka_consumer(topic)
    
    f = open('uc2_read_from_kafka.log', 'w')
    f.close()

    print("Reading from kafka topic", KAFKA_MONITORING_TOPICS[topic])
    bytesSent = bytesRcvd = bs_ts = br_ts = " "

    for msg in consumer:
        if (topic != "uc2_tm"):
            print(msg.value)
            continue

        if (msg.value["type"] == "nettx"):
            print (msg.value)
            bytesSent = msg.value["value"]
            bs_ts = msg.value["timestamp"]

        if (msg.value["type"] == "netrx"):
            print (msg.value)
            bytesRcvd = msg.value["value"]
            br_ts = msg.value["timestamp"]

        if bytesSent != " " and bytesRcvd != " ":
            assert(bs_ts != " " and br_ts != " ")
            # assert(br_ts == bs_ts)
            if (br_ts == bs_ts):
                message = bytesSent + "\t" + bs_ts + "\t" + bytesRcvd #+ "\t"+ br_ts
                bytesSent = bytesRcvd = bs_ts = br_ts = " "
                f = open('uc2_read_from_kafka.log', 'a')
                f.write(message)
                f.write('\n')
                f.close()
            else:
                print ("\n\n************* br_ts != bs_ts*************\n\n")

if __name__ == '__main__':
    main()
