#################################################################################
# Author:      Morteza Kheirkhah
# Institution: University College London (UCL), UK
# Email:       m.kheirkhah@ucl.ac.uk
# Homepage:    http://www.uclmail.net/users/m.kheirkhah/
#################################################################################
from math import floor
import argparse
from time import sleep
from datetime import datetime
from rl_uc2 import generate_timestamp
from rl_uc2 import VIDEO_BIT_RATE, VCE
from uc2_daemon import get_kafka_producer, \
    write_kafka_uc2_vce, \
    write_kafka_uc2_cno, \
    write_kafka_uc2_tm, \
    write_kafka_uc2_exec

CA_HIGH = 0.3    # 30% 
CA_LOW  = 0.1    # 10%
CA_LOWEST = 0.01 # 1%

TS_VCE_1 = 0.0
TS_VCE_2 = 0.0
PROFILE = ["low", "standard", "high"]
RESET_THRESH = 500 # 30 * 4 = 120 seconds
BITS_IN_MB = 1000000.0
BITS_IN_KB = 1000.0

LOW_BR = 10 #kb
BW_REQ = True
BW_REQ_COUNT = 0
BW_REQ_THRESH = 0 #24 # 6 * 4
# BW_REQ_RESET = 80 # 20*4 = 80 seconds
bw_REQ_SAVE_COUNTER = 0
# BW_EXTRA = 20   #Mbps
BW_CAP = 100    #Mbps
BW_CURRENT = 0.0
BW_DEFAULT = 0.0

BW_REDUCE_FRAC = 0.4
BW_REDUCE_REQ = True
BW_REDUCE_REQ_COUNT = 0
BW_REDUCE_REQ_THRESH = 4 #24
# BW_REDUCE_OFFSET = 5 * BITS_IN_MB # larger the soon to reset bw
# BW_REDUCE_RESET = 5

TS_NOW = 0.0
TS_OLD = 0.0

COUNTER = 0
CAL_RES_COUNT = 0
SLEEP_INTERVAL = 1.0

# vce[0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity]
def calculate_effective_capacity(vce_1, vce_2, capacity, ava_ca):
    if (capacity == 0):
        print("No active stream -> effective capacity is zero")
        return 0

    br_1 = 0 if vce_1[7] == '0.0' else VIDEO_BIT_RATE[int(vce_1[2])] * BITS_IN_KB
    br_2 = 0 if vce_2[7] == '0.0' else VIDEO_BIT_RATE[int(vce_2[2])] * BITS_IN_KB

    capacity = capacity * BITS_IN_MB
    tmp_ca = capacity - br_1 - br_2
    bg_traffic = abs(tmp_ca - ava_ca)
    effective_ca = capacity - bg_traffic
    print("cal_effec_ca() -> ca[{0}] ava_ca[{1}] br1[{2}] "
          "br2[{3}] bg[{4}] eff_ca[{5}]".format(capacity/BITS_IN_MB,
                                                round(ava_ca/BITS_IN_MB, 2),
                                                br_1/BITS_IN_MB,
                                                br_2/BITS_IN_MB,
                                                round(bg_traffic/BITS_IN_MB, 2),
                                                round(effective_ca/BITS_IN_MB, 2)))
    return effective_ca

def find_optimal_br_single(split_ca):
    br = -1
    for i in range(len(VIDEO_BIT_RATE)):
        if (VIDEO_BIT_RATE[i]*BITS_IN_KB > split_ca):
            index = 0 if i-1 < 0 else i-1
            br = index
            #
        if (i == len(VIDEO_BIT_RATE) - 1 and br == -1):
            br = i
    return br

def find_optimal_br(split_ca):
    br_pair = (-1, -1)
    for i in range(len(VIDEO_BIT_RATE)):
        if (VIDEO_BIT_RATE[i]*BITS_IN_KB > split_ca[0] and br_pair[0] == -1):
            index = 0 if i-1 < 0 else i-1
            br_pair = (index, br_pair[1])
        if (VIDEO_BIT_RATE[i]*BITS_IN_KB> split_ca[1] and br_pair[1] == -1):
            index = 0 if i-1 < 0 else i-1
            br_pair = (br_pair[0], index)

        if (i == len(VIDEO_BIT_RATE) - 1 and br_pair[0] == -1):
            print("find_optimal_br -> ava_ca is higher than max bitrate for vce-1")
            br_pair = (i, br_pair[1])
        if (i == len(VIDEO_BIT_RATE) - 1 and br_pair[1] == -1):
            br_pair = (br_pair[0], i)
            print("find_optimal_br -> ava_ca is higher than max bitrate for vce-2")

    return br_pair

def simple_analysis(vce_1, vce_2):
    if (float(vce_1[7]) == 0.0 and float(vce_2[7]) == 0.0):
        return "NO_STREAM"
    elif (float(vce_1[7]) == 0.0 and float(vce_2[7]) != 0.0):
        return "ONE_STREAM_VCE_2"
    elif (float(vce_1[7]) != 0.0 and float(vce_2[7]) == 0.0):
        return "ONE_STREAM_VCE_1"
    elif (float(vce_1[7]) != 0.0 and float(vce_2[7]) != 0.0):
        return "TWO_STREAMS"
    else:
        print("simple_analysis() - > **UNKNOWN**")
        return "UNKNOWN"
    
def update_real_split_ca(real_split_ca, capacity, ava_ca):
    freed_ca = 0
    total_ca = real_split_ca[0]+real_split_ca[1]
    max_br = VIDEO_BIT_RATE[len(VIDEO_BIT_RATE)-1] * BITS_IN_KB
    min_br = VIDEO_BIT_RATE[0] * BITS_IN_KB
    # check vce-1 
    if (real_split_ca[0] > max_br):
        freed_ca += real_split_ca[0] - max_br
        real_split_ca = (max_br, real_split_ca[1])
    # check vce-2
    if (real_split_ca[1] > max_br):
        freed_ca += real_split_ca[1] - max_br
        real_split_ca = (real_split_ca[0], max_br)
    #
    if (real_split_ca[0] < max_br): # (new, old)
        real_split_ca = (real_split_ca[0]+freed_ca, real_split_ca[1])
        print("update_real_split_ca() -> vce-1 [{0}]".format(real_split_ca))
    elif (real_split_ca[1] < max_br): # (old, new)
        real_split_ca = (real_split_ca[0], real_split_ca[1]+freed_ca)
        print("update_real_split_ca() -> vce-2 [{0}]".format(real_split_ca))
    
    return real_split_ca

# vce_1:   [0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity]
# res_1:   [vce, ts, br_min, br_max, capacity]
def update_real_split_br_max(vce_1, vce_2, ava_ca, real_split_br_max):
    if (TS_VCE_1 != 0.0 and TS_VCE_2 != 0.0):
        assert (1!=1)
        return real_split_br_max

    carry_on = simple_analysis(vce_1, vce_2) != "NO_STREAM"
    ca_frac_high = BW_CURRENT * BITS_IN_MB * CA_HIGH
    ca_frac_low = BW_CURRENT * BITS_IN_MB * CA_LOW
    ca_frac_mid = (ca_frac_high + ca_frac_low) / 2.0
    loss_rate = max(float(vce_1[8]), float(vce_2[8])) * 100.0
    #
    # operating between LOW and HIGH (%) of the capacity
    #
    if (ca_frac_low < ava_ca <= ca_frac_high and carry_on):
        print("*********************************************************************************************")
        print("available capacity is smaller than [{0}]% of the maximum capacity -> "
              "ava_ca[{1}] ca_frac_high[{2}] loss_rate[{3}]".format(CA_HIGH*100.0,
                                                                    round(ava_ca/BITS_IN_MB,1),
                                                                    ca_frac_high/BITS_IN_MB,
                                                                    loss_rate))
        #
        # when profiles are different
        if (str(vce_1[5]) != str(vce_2[5])):
            # find the low quiality profile first
            if (get_profile(vce_1[5]) < get_profile(vce_2[5])):
                # vce_1 has lower priority, reduce its bitrate to br_min
                real_split_br_max_0 = int(vce_1[3])
                real_split_br_max = (real_split_br_max_0, real_split_br_max[1])
                print("bw presure reset a low priority stream to br_min (vce_1)", real_split_br_max)
                # if there is a loss or..., reduce also the bitrate for the high prioirty (vce_2).
                if  ((loss_rate > 0.0 or ava_ca < ca_frac_mid) and TS_VCE_2 == 0.0):
                    # real_split_br_max_1 = real_split_br_max[1] - 1 if real_split_br_max[1] > 0 else real_split_br_max[1]
                    br_tmp = min(int(vce_2[2]), real_split_br_max[1]) # min (actual, new)
                    real_split_br_max_1 = br_tmp - 1 if br_tmp > 0 else br_tmp
                    real_split_br_max = (real_split_br_max[0], real_split_br_max_1)
                    print("available capacity is smaller than [{0}]% of the maximum capacity -> "
                          "ava_ca[{1}] ca_frac_mid[{2}] loss_rate[{3}]".format(((CA_HIGH+CA_LOW)/2.0)*100.0,
                                                                               round(ava_ca/BITS_IN_MB,1),
                                                                               ca_frac_mid/BITS_IN_MB,
                                                                               loss_rate))
                    print("so decrease from a high priority (vce_2).", real_split_br_max)
            else:
                # vce_2 has lower priority, reduce its bitrate by one
                real_split_br_max_1 = int(vce_2[3])
                real_split_br_max = (real_split_br_max[0], real_split_br_max_1)
                print("bw pressure reset a low priority stream to br_min (vce_2)", real_split_br_max)
                # if there is a loss or..., reduce also the bitrate for the high prioirty (vce_1).
                if ((loss_rate > 0.0 or ava_ca < ca_frac_mid) and TS_VCE_1 == 0.0):
                    # real_split_br_max_0 = real_split_br_max[0] - 1 if real_split_br_max[0] > 0 else real_split_br_max[0]
                    br_tmp = min(int(vce_1[2]), real_split_br_max[0]) # min (actual, new)
                    real_split_br_max_1 = br_tmp - 1 if br_tmp > 0 else br_tmp
                    real_split_br_max = (real_split_br_max_0, real_split_br_max[1])
                    print("available capacity is smaller than [{0}]% of the maximum capacity -> "
                          "ava_ca[{1}] ca_frac_mid[{2}] loss_rate[{3}]".format(((CA_HIGH+CA_LOW)/2.0)*100.0,
                                                                               round(ava_ca/BITS_IN_MB,1),
                                                                               ca_frac_mid/BITS_IN_MB,
                                                                               loss_rate))
                    print("so decrease from a high priority (vce_1).", real_split_br_max)
        #
        # when profiles are identical
        else:
            if (loss_rate > 0.0): # reduce aggresively from all streams
                real_split_br_max = (int(vce_1[3]), int(vce_2[3]))
                print("reset all streams to their br_min due to losses", real_split_br_max)
            else: # reduce slightly from all streams
                real_split_br_max_0 = real_split_br_max[0] - 1 if real_split_br_max[0] > 0 else real_split_br_max[0]
                real_split_br_max_1 = real_split_br_max[1] - 1 if real_split_br_max[1] > 0 else real_split_br_max[1]
                real_split_br_max = (real_split_br_max_0, real_split_br_max_1)
                print("decrease from all streams since they have similar priority", real_split_br_max)
        print("*********************************************************************************************")
    #
    # operating below LOW (%) of the capacity
    #
    elif (ava_ca <= ca_frac_low and carry_on):
        real_split_br_max = (int(vce_1[3]), int(vce_2[3]))
        print("*********************************************************************************************")
        print("available capacity is smaller than [{0}]% of the maximum capacity -> "
              "ava_ca[{1}] ca_frac_low[{2}] real_split_br_max[{3}] loss_rate[{4}]".format(CA_LOW*100.0,
                                                                                          round(ava_ca/BITS_IN_MB, 1),
                                                                                          ca_frac_low/BITS_IN_MB,
                                                                                          real_split_br_max,
                                                                                          loss_rate))
        print("reset all streams to their br_min", real_split_br_max)
        print("*********************************************************************************************")
    return real_split_br_max

# profile: ["low", "standard", "high"]
# vce_1:   [0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity]
# res_1:   [vce, ts, br_min, br_max, capacity]
def calculate_resources(vce_1, vce_2, bw_dist, producer):
    global CAL_RES_COUNT, TS_NOW, TS_OLD
    CAL_RES_COUNT += 1
    TS_NOW = generate_timestamp()
    ts_delay = TS_NOW - TS_OLD
    TS_OLD = TS_NOW
    print ("\n======================== cal_res ({0}) ({1}) ========================".format(COUNTER, CAL_RES_COUNT))
    # TEMP #
    print("TS_VCE_1[{0}] TS_VCE_2[{1}] TS_DELAY[{2}]".format(TS_VCE_1, TS_VCE_2, ts_delay))

    ts = generate_timestamp()
    active_1 = "NOT ACTIVE" if vce_1[7] == '0.0' else "ACTIVE"
    active_2 = "NOT ACTIVE" if vce_2[7] == '0.0' else "ACTIVE"
    
    print ("vce_1 -> {0} [{1}]\nvce_2 -> {2} [{3}]".format(vce_1, active_1, vce_2, active_2))

    # init profile to 0 if there is no streams else to actual video profile
    profile_1 = '0' if vce_1[7] == '0.0' else vce_1[5]
    profile_2 = '0' if vce_2[7] == '0.0' else vce_2[5]

    capacity = BW_CURRENT
    print("max capacity -> {0}Mbps".format(capacity))
    # print("max capacity -> {0}Mbps br_vce_1[{1}]Kbps  br_vce_2[{2}]Kbps".format(capacity,
    #                                                                             VIDEO_BIT_RATE[int(vce_1[2])],
    #                                                                             VIDEO_BIT_RATE[int(vce_2[2])]))
    ava_ca = max(float(vce_1[6]), float(vce_2[6]))
    print("available capacity -> {0}Mbps".format(round(ava_ca/BITS_IN_MB, 2)))

    if (ava_ca > BW_CURRENT * BITS_IN_MB):
        print("capacity has been reduced recently, no need to recalcualte... "
              "ava_ca[{0}] BW_CURRENT[{1}]".format(ava_ca, BW_CURRENT * BITS_IN_MB))
        res_1 = [1, ts, vce_1[3], vce_1[4], capacity]
        res_2 = [2, ts, vce_2[3], vce_2[4], capacity]
        return res_1, res_2

    # If a vce doesn't have a stream we shouldn't consider it in our resource allocations
    dist = bw_dist[(profile_1, profile_2)] # this should be based on max capacity - background traffic
    print("available capacity to share (%) -> vce-1({0}%) |-| vce-2({1}%)".format(dist[0], dist[1]))

    effective_ca = calculate_effective_capacity(vce_1, vce_2, capacity, ava_ca)
    br_1 = 0 if vce_1[7] == '0.0' else VIDEO_BIT_RATE[int(vce_1[2])] * BITS_IN_KB
    br_2 = 0 if vce_2[7] == '0.0' else VIDEO_BIT_RATE[int(vce_2[2])] * BITS_IN_KB
    real_usable_ca = effective_ca - br_1 - br_2

    real_split_ca = (br_1 + dist[0]*real_usable_ca/100.0, br_2+ dist[1]*real_usable_ca/100.0)
    print ("real_split_ca -> vce-1({0}) |-| vce-2({1})".format(real_split_ca[0], real_split_ca[1]))

    # This is to fix a rare bug #
    if (real_usable_ca < 0.0):
        # real_split_ca = (VIDEO_BIT_RATE[int(vce_1[3])], VIDEO_BIT_RATE[int(vce_2[3])])
        print ("---->>>> real_split_ca -> vce-1({0}) |-| vce-2({1}) ----<<<<".format(real_split_ca[0], real_split_ca[1]))

    # if possible give more to low quality stream
    if (simple_analysis(vce_1, vce_2) == "TWO_STREAMS"):
        real_split_ca = update_real_split_ca(real_split_ca, capacity, ava_ca)
    
    real_split_br_max = find_optimal_br(real_split_ca)
    print("real_split_br_max -> vce-1({0}) |-| vce-2({1})".format(VIDEO_BIT_RATE[real_split_br_max[0]],
                                                                  VIDEO_BIT_RATE[real_split_br_max[1]]))

    # effective_ca is negative reset all streams to their min_br
    if (effective_ca < 0.0 and simple_analysis(vce_1, vce_2) != "NO_STREAM"):
        real_split_br_max = (int(vce_1[3]), int(vce_2[3]))
        print("\neffective_ca is small reset all bitrates to their minimum -> {0}\n".format(real_split_br_max))
         
    # CA_LOW <= ava_ca <= CA_HIGH % of maximum capacity
    real_split_br_max = update_real_split_br_max(vce_1, vce_2, ava_ca, real_split_br_max)
    
    # br_max should not be larger than br_max
    vce_1_br_max = real_split_br_max[0] if real_split_br_max[0] <= int(vce_1[4]) else int(vce_1[4])
    real_split_br_max = (vce_1_br_max, real_split_br_max[1])
    vce_2_br_max = real_split_br_max[1] if real_split_br_max[1] <= int(vce_2[4]) else int(vce_2[4])
    real_split_br_max = (real_split_br_max[0], vce_2_br_max)
    
    # br_max should not be smaller than br_min
    vce_1_br_max = real_split_br_max[0] if real_split_br_max[0] >= int(vce_1[3]) else int(vce_1[3])
    real_split_br_max = (vce_1_br_max, real_split_br_max[1])
    vce_2_br_max = real_split_br_max[1] if real_split_br_max[1] >= int(vce_2[3]) else int(vce_2[3])
    real_split_br_max = (real_split_br_max[0], vce_2_br_max)
    
    res_1 = [1, ts, vce_1[3], str(vce_1_br_max), capacity] # vce_1[7] -> capacity
    res_2 = [2, ts, vce_2[3], str(vce_2_br_max), capacity] # vce_2[7] -> capacity

    return res_1, res_2

def get_profile(profile):
    quality = 0
    if (profile == 'low'):
        quality = 0
    elif (profile == 'standard'):
        quality = 1
    elif (profile == 'high'):
        quality = 2
    else:
        print("Quality profile is unknown...! {0}".format)
        exit(0)
    return quality

# vce_1: [0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity]
# res_x: [vce, ts, br_min, br_max, capacity]
def write_resource_alloc(vce_1, vce_2, res_1, res_2, producer):
    m_1 = "".join(str(e) + "\t" for e in res_1) + "\n"
    m_2 = "".join(str(e) + "\t" for e in res_2) + "\n"    
    try:
        with open("uc2_resource_dist.log", "a") as ff:
            if (float(res_1[4]) != 0.0 and float(vce_1[7]) != 0.0):
                ff.write(m_1)
                write_kafka_uc2_vce(producer, res_1, VCE[res_1[0]], VIDEO_BIT_RATE, get_profile(vce_1[5])) # for vce_1
                print ("res_1 -> {0}".format(res_1))
            if (float(res_2[4]) != 0.0 and float(vce_2[7]) != 0.0):
                ff.write(m_2)
                write_kafka_uc2_vce(producer, res_2, VCE[res_2[0]], VIDEO_BIT_RATE, get_profile(vce_2[5])) # for vce_2
                print ("res_2 -> {0}".format(res_2))
    except Exception as ex:
        print(ex)

def reset_all(producer):
    global TS_VCE_1, TS_VCE_2
    print("\n**********************reset_all()**********************")
    # TEMP #
    print("reset_all() -> TS_VCE_1[{0}] TS_VCE_2[{1}] COUNTER[{2}]".format(TS_VCE_1, TS_VCE_2, COUNTER)) 
    
    f = open("uc2_current_state.log", "w")
    f.close()
    f = open("uc2_resource_dist.log", "w")
    f.close()
    f = open('uc2_read_from_kafka.log', 'w')
    f.close()

    TS_VCE_1 = 0.0
    TS_VCE_2 = 0.0
    
    vce_1 = ["1", "0", "0", "0", "0", "0", "0", "0.0", "0.0", "0.0"]
    vce_2 = ["2", "0", "0", "0", "0", "0", "0", "0.0", "0.0", "0.0"]

    deactivate_vce(producer, LOW_BR, "1")
    deactivate_vce(producer, LOW_BR, "2")
    
    write_kafka_uc2_cno(producer, "request", BW_CURRENT)
    print("*******************************************************\n")
    return vce_1, vce_2

def reset_current_state(vce_1, vce_2, producer):
    # print("reset_current_state() -> TS_VCE_1[{0}] TS_VCE_2[{1}] COUNTER[{2}]".format(TS_VCE_1, TS_VCE_2, COUNTER))
    if (TS_VCE_1 > RESET_THRESH):
        vce_1[7] = "0.0"
    if (TS_VCE_2 > RESET_THRESH):
        vce_2[7] = "0.0"
    if (TS_VCE_1 > RESET_THRESH and TS_VCE_2 > RESET_THRESH):
        return reset_all(producer)
    if (TS_VCE_1 > RESET_THRESH and float(vce_2[7]) == 0.0):
        return reset_all(producer)
    if (TS_VCE_2 > RESET_THRESH and float(vce_1[7]) == 0.0):
        return reset_all(producer)
    return vce_1, vce_2

# [vce, ts, br, br_min, br_max, profile, ava_ca, capacity]
def read_current_state(vce_1, vce_2):
    global TS_VCE_1
    global TS_VCE_2
    try:
        with open("uc2_current_state.log", "r") as ff:
            for line in ff:
                col = line.split()
                if (int(col[0]) == int (vce_1[0])):   # vce_1
                    if (float(col[1]) > float(vce_1[1])):
                        vce_1 = col
                        TS_VCE_1 = 0.0
                    elif (float(col[1]) == float(vce_1[1])):
                        TS_VCE_1 += 1
                elif (int(col[0]) == int(vce_2[0])):  # vce_2
                    if (float(col[1]) > float(vce_2[1])):
                        vce_2 = col
                        TS_VCE_2 = 0.0
                    elif(float(col[1]) == float(vce_2[1])):
                        TS_VCE_2 += 1
        return vce_1, vce_2
    except Exception as ex:
        f = open('uc2_current_state.log', 'w')
        f.close()
        print(ex)
        return vce_1, vce_2

def generate_bw_dist():
    bw_dist = {}
    bw_dist[("high","high")] = (50,50)
    bw_dist[("high","standard")] = (75,25)
    bw_dist[("high","low")] = (100,0)
    bw_dist[("standard","high")] = (25,75)
    bw_dist[("standard","standard")] = (50,50)
    bw_dist[("standard","low")] = (100,0)
    bw_dist[("low","high")] = (0,100)
    bw_dist[("low","standard")] = (25,75)
    bw_dist[("low","low")] = (50,50)
    bw_dist[("high","0")] = (100, 0)
    bw_dist[("standard","0")] = (100,0)
    bw_dist[("low","0")] = (100,0)
    bw_dist[("0","high")] = (0, 100)
    bw_dist[("0","standard")] = (0, 100)
    bw_dist[("0","low")] = (0, 100)
    bw_dist[("0","0")] = (0, 0)

    return bw_dist

# deactivate vce by bringing its bitrate very low
def deactivate_vce(producer, br_value, vce_id):
    vce_id = VCE[int(vce_id)]
    write_kafka_uc2_exec(producer, br_value , vce_id)

# vce_1:[0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity]
# res_1:[0-1, 1-ts, 2-vce_1[3], 3-str(vce_1_br_max), 4-vce_1[7]]
def analysis_notifications(vce_1, vce_2, res_1, res_2, producer):
    global BW_REQ, BW_REQ_COUNT, BW_CURRENT
    global BW_REDUCE_REQ_COUNT, BW_REDUCE_REQ

    ava_ca = max(float(vce_1[6]), float(vce_2[6]))
    all_active = False
    
    if (float(vce_1[7]) == 0.0 and float(vce_2[7]) == 0.0):
        print("analysis -> NO active stream!")
        deactivate_vce(producer, LOW_BR, vce_1[0])
        deactivate_vce(producer, LOW_BR, vce_2[0])
        return res_1, res_2
    elif (float(vce_1[7]) == 0.0 and float(vce_2[7]) != 0.0):
        deactivate_vce(producer, LOW_BR, vce_1[0])
        print("analysis -> ONE active session from vce_2...")
    elif (float(vce_1[7]) != 0.0 and float(vce_2[7]) == 0.0):
        deactivate_vce(producer, LOW_BR, vce_2[0])
        print("analysis -> ONE active session from vce_1...")
    elif (float(vce_1[7]) != 0.0 and float(vce_2[7]) != 0.0):
        all_active = True
        print("analysis -> TWO active sessions from both vce_1 and vce_2...")

    # vce_1:[0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity, 8-loss, 9-ts_dur]
    # res_1:[0-1, 1-ts, 2-vce_1[3], 3-str(vce_1_br_max), 4-vce_1[7]]
    if (all_active and int(vce_1[3]) == int(res_1[3]) and int(vce_2[3]) == int(res_2[3])):
        BW_REDUCE_REQ_COUNT = 0 # reset the counter of other condition
        ca_frac_lowest = BW_CURRENT * BITS_IN_MB * CA_LOWEST
        ava_ca = max(int(vce_1[6]), int(vce_2[6]))
        loss   = max(float(vce_1[8]), float(vce_2[8]))
        if (ava_ca <= ca_frac_lowest or loss > 0.0): # either loss or ava_ca is < 0.1% ca
            BW_REQ_COUNT += 1
            print("analysis -> session(s) operate at their minimum bitrate, "
                  "-> BW_REQ[{0}] BW_REQ_COUNT[{1}] BW_REQ_THRESH[{2}]".format(BW_REQ, BW_REQ_COUNT, BW_REQ_THRESH))
            print("analysis -> available capacity is smaller than [{0}]% of the maximum capacity -> "
                  "ava_ca[{1}] ca_frac_lowest[{2}] loss_rate[{3}]".format(CA_LOW*100.0,
                                                                          round(ava_ca/BITS_IN_MB, 1),
                                                                          ca_frac_lowest/BITS_IN_MB,
                                                                          loss))
            if (BW_REQ == True and BW_REQ_COUNT > BW_REQ_THRESH): # for now execute with no delay
                # BW_REQ = False
                BW_REQ_COUNT = 0
                bw = float(BW_CURRENT + BW_DEFAULT)

                if (bw > BW_CAP):
                    bw = BW_CAP

                print("analysis -> INCREASE CAPACITY FROM {0} -> {1}".format(BW_CURRENT, bw))
                res_1[4] = str(bw)
                res_2[4] = str(bw)
                BW_CURRENT = bw
                write_kafka_uc2_cno(producer, "request", bw)
    # elif (all_active and BW_CURRENT > BW_DEFAULT and ava_ca >= ((BW_CURRENT - BW_DEFAULT) * BITS_IN_MB)):
    elif (all_active and BW_CURRENT > BW_DEFAULT and ava_ca > (BW_DEFAULT * BITS_IN_MB * BW_REDUCE_FRAC * 2.0)):
        BW_REQ_COUNT = 0 # reset counter of the other condition
        bw = BW_CURRENT - (BW_DEFAULT * BW_REDUCE_FRAC) # reduce gently (by 40% default)

        if (bw <= BW_DEFAULT):
            bw = BW_DEFAULT

        # if((BW_CURRENT - BW_DEFAULT) >= BW_DEFAULT and ava_ca > (BW_DEFAULT * BITS_IN_MB)):
        #     bw = BW_CURRENT - BW_DEFAULT # reduce aggresively (by full default)
        #     print ("analysis -> happy to reduce BW aggresively - NEW BW[{0}]".format(bw))

        print("analysis -> More capacity is available than required -> "
              "BW_REDUCE_REQ[{0}] BW_REDUCE_REQ_COUNT[{1}]".format(BW_REDUCE_REQ, BW_REDUCE_REQ_COUNT))
        BW_REDUCE_REQ_COUNT += 1
        if (BW_REDUCE_REQ == True and BW_REDUCE_REQ_COUNT >= BW_REDUCE_REQ_THRESH):
            print("analysis -> REDUCE CAPACITY FROM {0} -> {1}".format(BW_CURRENT, BW_DEFAULT * BW_REDUCE_FRAC))
            # BW_REDUCE_REQ = False
            BW_REDUCE_REQ_COUNT = 0
            res_1[4] = str(bw) #mbps
            res_2[4] = str(bw) #mbps
            BW_CURRENT = bw
            write_kafka_uc2_cno(producer, "request", bw)
    # elif (all_active and BW_CURRENT > BW_DEFAULT and ava_ca > (BW_DEFAULT * BITS_IN_MB * 0.5)):
    #     BW_REQ_COUNT = 0 # reset counter of the other condition
    #     bw = BW_CURRENT - (BW_DEFAULT * 0.5)
    #     print("analysis -> More capacity is available than required -> "
    #           "BW_REDUCE_REQ[{0}] BW_REDUCE_REQ_COUNT[{1}]".format(BW_REDUCE_REQ, BW_REDUCE_REQ_COUNT))
    #     BW_REDUCE_REQ_COUNT += 1
    #     if (BW_REDUCE_REQ == True and BW_REDUCE_REQ_COUNT >= BW_REDUCE_REQ_THRESH):
    #         print("analysis -> REDUCE CAPACITY FROM {0} -> {1}".format(BW_CURRENT, BW_DEFAULT * 0.5))
    #         BW_REDUCE_REQ_COUNT = 0
    #         res_1[4] = str(bw) #mbps
    #         res_2[4] = str(bw) #mbps
    #         BW_CURRENT = bw
    #         write_kafka_uc2_cno(producer, "request", bw)
    else:
        BW_REDUCE_REQ_COUNT = 0
        BW_REQ_COUNT = 0
        # TEMP #
        print("analysis -> normal condition BW_REQ_COUNT[{0}] BW_REDUCE_REQ_COUNT[{1}]".format(BW_REQ_COUNT,
                                                                                               BW_REDUCE_REQ_COUNT))
    return res_1, res_2

# vce[0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity 8-loss 9-polling_interval]
def write_current_tm(producer, vce_1, vce_2):
    loss_rate = max(float(vce_1[8]), float(vce_2[8])) * 100.0
    polling_interval = max(float(vce_1[9]), float(vce_2[9]))
    write_kafka_uc2_tm(producer, BW_CURRENT, "capacity", "Mbps")
    write_kafka_uc2_tm(producer, loss_rate, "loss_rate", "%")
    write_kafka_uc2_tm(producer, polling_interval, "polling_interval", "Seconds")

def init_cmd_params():
    parser = argparse.ArgumentParser(description='Parameters setting for the arbitrator function of SS-CNO.',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     prog='uc2_arbitrator',
                                     epilog="If you have any questions please contact "
                                     "Morteza Kheirkhah <m.kheirkhah@ucl.ac.uk>")
    parser.add_argument("--ca", type=float, default=50.0)
    args = parser.parse_args()
    
    # init parameters
    capacity = args.ca
    return capacity

def main():
    global COUNTER, BW_CURRENT, BW_DEFAULT
    global TS_NOW, TS_OLD
    
    BW_CURRENT = init_cmd_params()
    BW_DEFAULT = BW_CURRENT

    TS_NOW = generate_timestamp()
    TS_OLD = TS_NOW
    
    producer = get_kafka_producer()
    vce_1, vce_2 = reset_all(producer)
    bw_dist = generate_bw_dist()
    
    while True:
        COUNTER += 1
        vce_1, vce_2 = read_current_state(vce_1, vce_2)
        # print ("vce_1 -> {0}\nvce_2 -> {1}".format(vce_1, vce_2))
        vce_1, vce_2 = reset_current_state(vce_1, vce_2, producer)
        # print ("vce_1 -> {0}\nvce_2 -> {1}".format(vce_1, vce_2))
        carry_on = False if (float(vce_1[7]) == 0.0 and float(vce_2[7]) == 0.0) else True
        if (carry_on and (TS_VCE_1 == 0.0 or TS_VCE_2 == 0.0)):
            res_1, res_2 = calculate_resources(vce_1, vce_2, bw_dist, producer)
            # print ("res_1 -> {0}\nres_2 -> {1}".format(res_1, res_2));
            #
            # res_1, res_2 = analysis_notifications(vce_1, vce_2, res_1, res_2, producer)
            #
            # print ("res_1 -> {0}\nres_2 -> {1}".format(res_1, res_2));
            write_resource_alloc(vce_1, vce_2, res_1, res_2, producer)
        write_current_tm(producer, vce_1, vce_2)

        sleep(SLEEP_INTERVAL)

if __name__ == '__main__':
    main()
