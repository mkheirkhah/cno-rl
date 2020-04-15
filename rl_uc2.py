#################################################################################
# The SS-CNO arbitrator algorithm for the UC2 multi-session scenario
# Author:      Morteza Kheirkhah
# Institution: University College London (UCL), UK
# Email:       m.kheirkhah@ucl.ac.uk
# Homepage:    http://www.uclmail.net/users/m.kheirkhah/
#################################################################################
import sys
import os
import time
import calendar
from time import sleep
import numpy as np
import tensorflow as tf
import rl_a3c
from uc2_daemon import get_kafka_producer, write_kafka_uc2_exec
import argparse
from datetime import datetime
from math import floor

S_INFO = 3  # bit_rate, bytes_sent, loss_rate
S_LEN = 8  # take how many frames in the past
A_DIM = 10
ACTOR_LR_RATE = 0.0001
VIDEO_BIT_RATE = [5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000, 45000, 50000]

M_IN_K = 1000.0
BITS_IN_MB = 1000000.0
DEFAULT_QUALITY = 1 # 1 was orignal
RANDOM_SEED = 42
RAND_RANGE = 1000
VCE = {1 : "06:00:cc:74:72:95", 2 : "06:00:cc:74:72:99"}

#rtmp://192.168.83.30/live/qoe
NN_MODEL = './trained_models/NN_BR_50_ALPHA_100_257800.ckpt'

INTERVAL = 1.0
MBPS = 1000000.0
# CAPACITY = 20000000.0

def extract_ts(line):
    extract = line[line.find("T") + 1:line.find("Z")]
    ts_list = extract.split(":")
    return ts_list


def compare_ts(ts_new, ts_cur):
    if ts_new[0] > ts_cur[0]:
        return True
    elif ts_new[0] == ts_cur[0] and ts_new[1] > ts_cur[1]:
        return True
    elif ts_new[0] == ts_cur[0] and ts_new[1] == ts_cur[1] and ts_new[2] > ts_cur[2]:
        return True
    else:
        return False

def get_ts_dur(ts_new, ts_cur):
    hour   = float(ts_new[0]) - float(ts_cur[0])
    minite = float(ts_new[1]) - float(ts_cur[1])
    second = float(ts_new[2]) - float(ts_cur[2])
    total_seconds = hour*60*60 + minite*60 + second
    #print ("get_ts_dur() -> new_ts_dur[{0}]".format(total_seconds))
    return total_seconds

def cal_lr(ca_tx, ca_rx, ca_free, capacity):
    # when there is capacity, loss_rate is 0.0
    if (ca_free > 0.0 or ca_rx == 0.0):
        return 0.0
    
    lr = ca_rx - capacity
    lr = 0.0 if lr < 0.0 else lr
    lr_frac = lr / float(ca_rx)
    return lr_frac


def cal_ca(new_bytes_sent, last_bytes_sent, ts_dur):
    #ts_dur = get_ts_dur(ext_new_ts, ext_last_ts)
    diff_bs = float(new_bytes_sent) - float(last_bytes_sent)
    ca = float(diff_bs * 8) / ts_dur  # bps
    return ca

def get_last_kafka_msg():
    bs = 0.0
    ts = "T00:00:00.000000Z"
    br = 0.0
    lr = 0.0
    try:
        with open("uc2_read_from_kafka.log", "r") as ff:
            for line in ff:
                col = line.split()
                bs = col[0]
                ts = col[1]
                br = col[2]
                lr = 0.0
                print("get_last_kafka_msg() -> bs [{0}] br [{1}] ts [{2}] lr [{3}]"
                      .format(bs,
                              br,
                              ts,
                              lr))
    except Exception as ex:
        print(ex)
        print("The reader script that creates this file is not yet activated...!")
        f = open('uc2_read_from_kafka.log', 'w')
        f.close()
    return float(bs), ts, float(br), float(lr)


def read_kafka(last_bytes_sent, last_bytes_rcvd, last_lr, last_ts, last_ca, capacity):
    with open("uc2_read_from_kafka.log", "r") as ff:
        for line in ff:
            col = line.split()
            bs = col[0]
            ts = col[1]
            br = col[2]
            lr = 0.0

            if last_bytes_sent == 0.0 and last_bytes_rcvd == 0.0 \
               and last_lr == 0.0 and last_ts == "T00:00:00.000000Z":
                last_bytes_sent = bs
                last_ts = ts
                last_bytes_rcvd = br
                last_lr = lr
                print("read_kafka() -> 1st msg from Kafka: bs[{0}] br[{1}] ts[{2}] lr[{3}] last_ca[{4}]Mbps"
                      .format(last_bytes_sent, last_bytes_rcvd, last_ts, last_lr, last_ca / MBPS))

            ext_new_ts = extract_ts(line)
            ext_last_ts = extract_ts(last_ts)
            result = compare_ts(ext_new_ts, ext_last_ts)
            # print(result, ext_new_ts, ext_last_ts)
            
            if (result):
                ts_dur = get_ts_dur(ext_new_ts, ext_last_ts)
                #print("read_kafka() -> ts_dur [{0}]".format(ts_dur))
                
                ca_tx = cal_ca(bs, last_bytes_sent, ts_dur) #bps
                ca_rx = cal_ca(br, last_bytes_rcvd, ts_dur) #bps

                ca_free = capacity - max(ca_rx, ca_tx)
                ca_free = 0.0 if ca_free < 0.0 else ca_free

                lr = cal_lr(ca_tx, ca_rx, ca_free, capacity) # 0 < lr < 1

                print("-> ca[{5}]Mbps ca_free[{0}]Mbps | loss_rate[{1}] | rx[{2}]Mbps | tx[{3}]Mbps | dur[{4}]s"
                      .format(round(ca_free/MBPS,3),
                              round(lr,6),
                              round(ca_rx/MBPS, 3),
                              round(ca_tx/MBPS, 3),
                              ts_dur,
                              capacity/MBPS))
                return bs, br, lr, ts, ca_free, 1, ts_dur

        #return last metrics
        #print("read_kafka() -> there is no messages in the Kafka to read...")
        return last_bytes_sent, last_bytes_rcvd, last_lr, last_ts, last_ca, 0, 0

# res_x:[vce, ts, br_min, br_max, capacity]
def read_resources(resource_update):
    try:
        with open("uc2_resource_dist.log", "r") as ff:
            for line in ff:
                col = line.split()
                # right vce instance
                if int(col[0]) == int(resource_update[0]):
                    # ts > last_ts
                    if int(col[1]) > (int(resource_update[1])):
                        resource_update = col
    except Exception as ex:
        # f = open('uc2_resource_dist.log', 'w')
        # f.close()
        print(ex)
    return resource_update

# res[vce, ts, br_min, br_max, capacity]
def bitrate_checker(resource_update, vce, bit_rate, br_min, br_max, profile, priority):
    assert (br_min == int(resource_update[2]))
    assert (int(resource_update[3]) <= br_max)
    
    if (bit_rate < int(resource_update[2])):
        return int(resource_update[2])
    elif (bit_rate > int(resource_update[3])):
        return int(resource_update[3])

    # ensure br is never smaller than the br_min
    if bit_rate < int(resource_update[2]):
        bit_rate = int(resource_update[2])

    return bit_rate
    # return int(resource_update[3])

def init_cmd_params():
    parser = argparse.ArgumentParser(description='Parameters setting for use case 2 (UC2) of the 5G-MEDIA project.',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     prog='rl_uc2',
                                     epilog="If you have any questions please contact "
                                     "Morteza Kheirkhah <m.kheirkhah@ucl.ac.uk>")
    parser.add_argument("--vce",      type=int,   default=1,     choices=[1, 2])
    parser.add_argument("--br_min",   type=int,   default=0,     choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    parser.add_argument("--br_max",   type=int,   default=9,     choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    parser.add_argument("--profile",  type=str,   default='standard', choices=['low', 'standard', 'high'])
    parser.add_argument("--priority", type=int,   default=0,     choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    parser.add_argument("--ava_ca",   type=float, default=0.0)
    parser.add_argument("--ca",       type=float, default=50.0)
    parser.add_argument("--seed",     type=int, default=42)
    args = parser.parse_args()

    # init parameters
    vce      = args.vce
    br_min   = args.br_min
    br_max   = args.br_max
    profile  = args.profile
    priority = args.priority
    ava_ca   = args.ava_ca
    capacity = args.ca * BITS_IN_MB
    seed     = args.seed
    return vce, br_min, br_max, profile, priority, ava_ca, capacity, seed

def generate_timestamp():
    # now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    # now = datetime.now().timestamp()
    now = calendar.timegm(time.gmtime())
    return now

def write_current_state(vce, br, br_min, br_max, profile, priority, ava_ca, capacity, loss_rate, ts_dur):
    ts = generate_timestamp()
    #str(list(VCE.keys())[list(VCE.values()).index(vce)]) + \
    message = str(vce) + \
        "\t" + str(ts) + "\t" + str(br) + "\t" + str(br_min) + \
        "\t" + str(br_max) + "\t" + profile + "\t" + \
        str(floor(ava_ca)) + "\t" + str(capacity/BITS_IN_MB) + "\t" + \
        str(float(loss_rate)) + "\t" + str(ts_dur) + "\n"
    try:
        with open("uc2_current_state.log", "a") as ff:
            ff.write(message)
    except Exception as ex:
        print(ex)

# res[vce, ts, br_min, br_max, capacity]
def update_capacity(resource_update, capacity):
    new_capacity = float(resource_update[4]) * BITS_IN_MB
    if capacity != new_capacity:
        print("capacity [{0}] new_capacity[{1}]".format(capacity, new_capacity))
        return new_capacity
    return capacity

def main():

    vce, br_min, br_max, profile, priority, ava_ca, capacity, seed = init_cmd_params()
    print ("\n******************************************************************************"
           "\nvce [{0}]"
           "\nbr_min [{1}]"
           "\nbr_max [{2}]"
           "\nprofile [{3}]"
           "\npriority [{4}]"
           "\nava_ca [{5}]"
           "\ncapacity [{6}]"
           "\nseed [{7}]"
           "\n******************************************************************************"
           .format(vce, br_min, br_max, profile, priority, ava_ca, capacity, seed))

    # As session start up we need to inform the arbitator about this session's details
    # write_current_state (vce, DEFAULT_QUALITY, br_min, br_max, profile, priority, ava_ca, capacity)

    np.random.seed(seed)

    assert len(VIDEO_BIT_RATE) == A_DIM

    with tf.Session() as sess:

        actor = rl_a3c.ActorNetwork(
            sess,
            state_dim=[S_INFO, S_LEN],
            action_dim=A_DIM,
            learning_rate=ACTOR_LR_RATE)

        sess.run(tf.global_variables_initializer())
        saver = tf.train.Saver()  # save neural net parameters

        # restore neural net parameters
        nn_model = NN_MODEL
        if nn_model is not None:  # nn_model is the path to file
            saver.restore(sess, nn_model)
            print("\nThe offline trained model [{0}] is restored...".format(nn_model))

        bit_rate = DEFAULT_QUALITY
        last_bit_rate = bit_rate

        action_vec = np.zeros(A_DIM)
        action_vec[bit_rate] = 1

        s_batch = [np.zeros((S_INFO, S_LEN))]

        producer = get_kafka_producer()

        bytes_sent = 0.0
        bytes_rcvd = 0.0
        loss_rate = 0.0
        ts = "T00:00:00.000000Z"
        # only for the inital bitrate
        resource_update = [str(vce), str(0), str(br_min), str(br_max), str(capacity/BITS_IN_MB)]
        print ("\nresource_update -> ", resource_update)

        # It is better to wait after getting the first sample from monitoring systems
        # write_current_state (vce, bit_rate, br_min, br_max, profile, priority, ava_ca, capacity)
        
        # ava_ca = 0.0
        # br_min = 0
        # br_max = 5
        # profile = "standard"
        # priority = 1
        # vce = 0

        bytes_sent, ts, bytes_rcvd, loss_rate, = get_last_kafka_msg()

        counter = 0
        while True:  # serve video forever
            counter += 1
            print("\n**** [{0}] ****".format(counter))

            while True:
                # read resource_update and update capacity
                resource_update = read_resources(resource_update)
                capacity = update_capacity(resource_update, capacity)
                # read kafka
                bytes_sent, bytes_rcvd, loss_rate, ts, ava_ca, result, ts_dur = \
                    read_kafka(bytes_sent, bytes_rcvd, loss_rate, ts, ava_ca, capacity)
                if (result):
                    break
                else:
                    sleep(INTERVAL)

            print("-> last_bit_rate[{0}]Mbps".format(VIDEO_BIT_RATE[last_bit_rate] / 1000.0))
            # print("new_bytes_sent[{0}] new_lr[{1}] new_ts[{2}] new_ava_ca[{3}]Mbps, last_bit_rate[{4}]"
            #       .format(bytes_sent,
            #               loss_rate,
            #               ts,
            #               ava_ca/MBPS,
            #               VIDEO_BIT_RATE[last_bit_rate]))

            # retrieve previous state
            if len(s_batch) == 0:
                state = [np.zeros((S_INFO, S_LEN))]
            else:
                state = np.array(s_batch[-1], copy=True)

            # dequeue history record
            state = np.roll(state, -1, axis=1)

            # last chunk bit rate (number)
            state[0, -1] = VIDEO_BIT_RATE[bit_rate] / float(np.max(VIDEO_BIT_RATE))  # last quality
            # past chunk throughput (array) # video_chunk_size is measured in byte
            state[1, -1] = float(ava_ca / capacity)  # bits/s -> megabytes/s
            # loss rate (array)
            state[2, -1] = float(loss_rate)  # loss_rate

            # print("states: bit_rate [{0}] ava_ca [{1}] loss_rate [{2}]"
            #       .format(state[0, -1], state[1, -1], state[2, -1]))

            action_prob = actor.predict(np.reshape(state, (1, S_INFO, S_LEN)))
            action_cumsum = np.cumsum(action_prob)
            bit_rate = (
                action_cumsum >
                np.random.randint(1, RAND_RANGE) / float(RAND_RANGE)).argmax()

            s_batch.append(state)

            # for first bitrate stick to DEFAULT_QUALITY
            if (counter <= 1):
                bit_rate = br_min
                # bit_rate = 0
                write_current_state (vce, bit_rate, br_min, br_max, profile, priority, ava_ca, capacity, loss_rate, ts_dur)
                sleep(1.5)

            # write new bit-rate to Kafka to be delivered to vCompression
            #if (last_bit_rate != bit_rate):
            print("-> new_bit_rate [{0}]Mbps"#" - last_bit_rate [{1}]Mbps"
                  .format(VIDEO_BIT_RATE[bit_rate]/1000.0,))
            #VIDEO_BIT_RATE[last_bit_rate]/1000.0))

            # update resource allocations
            resource_update = read_resources(resource_update)
            print ("-> resource_update {0} - bitrate is between [{1},{2}]"
                   " - priority [{3}]".format(resource_update,
                                                        VIDEO_BIT_RATE[int(resource_update[2])],
                                                        VIDEO_BIT_RATE[int(resource_update[3])],
                                                        profile))
            
            # Now time to check whether the decided bitrate is within our video quality profile
            new_bit_rate = bitrate_checker(resource_update, vce, bit_rate, br_min, br_max, profile, priority)

            if (new_bit_rate != bit_rate):
                print ("old br [{0}] -> new br by arbitrator [{1}]".format(VIDEO_BIT_RATE[bit_rate],
                                                                           VIDEO_BIT_RATE[new_bit_rate]))
                bit_rate = new_bit_rate
            
            last_bit_rate = bit_rate
            write_kafka_uc2_exec(producer, VIDEO_BIT_RATE[bit_rate], VCE[vce])

            # update capacity if needed
            capacity = update_capacity(resource_update, capacity)

            write_current_state (vce, bit_rate, br_min, br_max, profile, priority, ava_ca, capacity, loss_rate, ts_dur)
            
            # sleep for an INTERVAL before begin reading from Kafka again
            sleep(INTERVAL)

if __name__ == '__main__':
    main()
