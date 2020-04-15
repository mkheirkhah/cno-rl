#################################################################################
# Author:      Morteza Kheirkhah
# Institution: University College London (UCL), UK
# Email:       m.kheirkhah@ucl.ac.uk
# Homepage:    http://www.uclmail.net/users/m.kheirkhah/
#################################################################################
import argparse
from time import sleep
from uc2_daemon import *
from uc2_metric_generator import *
from datetime import *
import sys
import numpy as np

VIDEO_BIT_RATE = [3855, 7551, 11244, 18740, 37480, 56220] # kbps
VCE_LIST = {1 : "06:00:cc:74:72:95", 2 : "06:00:cc:74:72:99"}

def init_cmd_params():
    parser = argparse.ArgumentParser(description='',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     prog='uc2_vce',
                                     epilog="If you have any questions please contact "
                                     "Morteza Kheirkhah <m.kheirkhah@ucl.ac.uk>")
    parser.add_argument("--vce", type=int, default=1, choices=[1, 2]) # vce_id (1, 2)
    parser.add_argument("--br", type=int, default=5000) # bitrate (kbps)
    parser.add_argument("--topic", type=str, default="uc2_exec")
    args = parser.parse_args()

    # init parameters
    vce_id = args.vce
    bitrate = args.br
    topic = args.topic
    return vce_id, bitrate, topic

def main():
    vce_id, bitrate, topic = init_cmd_params()
    if (topic == "uc2_exec"):
        try:
            now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
            tmp_metric = METRIC_TEMPLATE_UC2_EXEC
            metric = generate_metric_uc2_exec(bitrate, now, tmp_metric, VCE_LIST[vce_id])
            print("@@@@", metric)
            #print(metric["execution"])
            producer = get_kafka_producer()
            t = producer.send(KAFKA_EXECUTION_TOPIC["uc2_exec"], metric)
            print(KAFKA_EXECUTION_TOPIC["uc2_exec"])
            result = t.get(timeout=60)
        except Exception as ex:
            print (ex)
    elif (topic == "uc2_conf"):
        try:
            now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
            tmp_metric = METRIC_TEMPLATE_UC2_CONF
            metric = generate_metric_uc2_conf(bitrate, now, tmp_metric, VCE_LIST[vce_id])
            print("@@@@", metric)
            #print(metric["execution"])
            producer = get_kafka_producer()
            t = producer.send(KAFKA_EXECUTION_TOPIC["uc2_conf"], metric)
            print(KAFKA_EXECUTION_TOPIC["uc2_conf"])
            result = t.get(timeout=60)
        except Exception as ex:
            print (ex)

def extract_ts(line):
    extract = line[line.find("T") + 1:line.find("Z")]
    ts_list = extract.split(":")
    return ts_list, extract

def compare_timestamps(ts_new, ts_cur):
    if ts_new[0] > ts_cur[0]:
        return True
    elif ts_new[0] == ts_cur[0] and ts_new[1] > ts_cur[1]:
        return True
    elif ts_new[0] == ts_cur[0] and ts_new[1] == ts_cur[
            1] and ts_new[2] > ts_cur[2]:
        return True
    else:
        return False

if __name__ == '__main__':
    main()
