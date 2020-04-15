###########################################################################
# Title:       Implementation of RL algortihm for UC2, 5G-MEDIA project
# Author:      Morteza Kheirkhah
# Institution: University College London (UCL), UK
# Email:       m.kheirkhah@ucl.ac.uk
# Homepage:    http://www.uclmail.net/users/m.kheirkhah/
# Note:        Original code has been written for the Pensieve paper (SIGCOMM'17)
###########################################################################

import numpy as np

MBPS = 1000000.0
BITS_IN_BYTE = 8.0
RANDOM_SEED = 42
BITRATE_LEVELS = 10

TOTAL_VIDEO_CHUNCK = 48 # 48 #100 #20
FRAME_INTERVAL = 1 #50  # frame
#VIDEO_SIZE_FILE = './video_size_'

#VIDEO_BIT_RATE     = [3000, 5000, 8000, 12000, 15000, 20000, 25000, 30000, 40000, 50000]
#VIDEO_BIT_RATE_AVG = [3129, 5216, 8349, 12505, 15630, 20841, 26055, 31294, 41727, 52156]

#VIDEO_BIT_RATE     = [5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 15000, 20000]
#VIDEO_BIT_RATE_AVG  = [5216, 6500, 7400, 8349, 9400, 10440, 11420, 12630, 15630, 20841] # dry-run

#VIDEO_BIT_RATE     = [4000, 8000, 12000, 20000, 40000, 45000]  #Kbps
#VIDEO_BIT_RATE_AVG = [3855, 7551, 11244, 18740, 37480, 42000]  #Kbps


BACKGROUND_TRAFFIC_1  = [0, 30] #Mbps
BACKGROUND_TRAFFIC_2  = [0, 5,  10, 15, 20, 25, 30, 35, 30, 25, 20, 15, 10, 5, 0]
BACKGROUND_TRAFFIC_3  = [0, 10, 20, 30, 20, 10, 0]

BACKGROUND_TRAFFIC_4  = [0,  2,  4,  6,  8,  10, 12, 14, 16, 18, 20, 22,
                         24, 26, 28, 30, 32, 34, 36, 38, 40, 38, 36, 34,
                         32, 28, 26, 24, 22, 20, 18, 16, 14, 12, 10, 8, 6, 4, 2]

BACKGROUND_TRAFFIC_5    = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 40, 35, 30, 25, 20, 15, 10, 5, 0]
BACKGROUND_TRAFFIC_5_1  = [0, 2, 4, 6, 8, 10, 12, 14, 15, 14, 12, 10, 8, 6, 4, 2, 0] # dry-run
#BACKGROUND_TRAFFIC_5_1  = [0, 2, 4, 6, 8, 10, 12, 13, 10, 8, 6, 4, 2, 0]

BACKGROUND_TRAFFIC_6  = [0, 0, 0, 0, 0, 0, 0, 0, 10, 10, 10, 10, 10, 10, 10, 10]
BACKGROUND_TRAFFIC_7  = [0, 0, 0, 0, 0, 0, 0, 0, 20, 20, 20, 20, 20, 20, 20, 20] 
BACKGROUND_TRAFFIC_8  = [0, 0, 0, 0, 0, 0, 0, 0, 30, 30, 30, 30, 30, 30, 30, 30]
BACKGROUND_TRAFFIC_9  = [0, 0, 0, 0, 0, 0, 0, 0, 35, 35, 35, 35, 35, 35, 35, 35]
BACKGROUND_TRAFFIC_10 = [0, 0, 0, 0, 0, 0, 0, 0, 40, 40, 40, 40, 40, 40, 40, 40]


BACKGROUND_TRAFFIC_0  = [BACKGROUND_TRAFFIC_1, BACKGROUND_TRAFFIC_2,
                         BACKGROUND_TRAFFIC_3, BACKGROUND_TRAFFIC_4,
                         BACKGROUND_TRAFFIC_5, BACKGROUND_TRAFFIC_6,
                         BACKGROUND_TRAFFIC_7, BACKGROUND_TRAFFIC_8,
                         BACKGROUND_TRAFFIC_9, BACKGROUND_TRAFFIC_10]

# CNO_RAND_MAX = 50000000 / 8.0  #Mbytes/s
# CNO_RAND_MIN = 1000000 / 8.0  #Mbytes/s

# ALGO = {0: "REAL", 1: "UNIFORM", 2: "NORMAL", 3: "SAWTHOOTH", 4: "NORM_BIT"}
# TRAFFIC_MODEL = ALGO[0]

class Environment:
    def __init__(self, all_cooked_time, all_cooked_bw, random_seed=RANDOM_SEED):
        np.random.seed(random_seed)

        self.video_chunk_counter = 0
        # self.video_size = {}  # in bytes
        # for bitrate in range(BITRATE_LEVELS):
        #     self.video_size[bitrate] = []
        #     with open(VIDEO_SIZE_FILE + str(bitrate)) as f:
        #         for line in f:
        #             self.video_size[bitrate].append(
        #                 (int(line.split()[0]), float(line.split()[1])))

    # def get_video_size(self, quality):
    #     video_chunk_size = self.video_size[quality][self.video_chunk_counter][0] # equal to frame's size
    #     video_chunk_br = self.video_size[quality][self.video_chunk_counter][1]   # equal to frame's bit_rate
    #     self.video_chunk_counter += 1  # to keep track of chunks/frames globally
    #     return video_chunk_size, \
    #         video_chunk_br

    def get_video(self, quality, video_bit_rates):
        video = video_bit_rates[quality] * 1000  #bps
        video = np.random.normal(video, video / 20.0)
        return video

    def get_background_0(self, video_count):
        outer_index = video_count % len(BACKGROUND_TRAFFIC_0)
        inner_index = self.video_chunk_counter % len(BACKGROUND_TRAFFIC_0[outer_index])
        
        background = BACKGROUND_TRAFFIC_0[outer_index][inner_index] * MBPS #bps
        background = np.random.normal(background, background / 10.0)
        return background
    
    def get_background(self, rand1, rand2, bg_traffic_pattern, bg_traffic_dist):
        if (bg_traffic_dist == 'normal'):
            index = self.video_chunk_counter % len(bg_traffic_pattern)
            background = bg_traffic_pattern[index] * MBPS #bps
            background = np.random.normal(background, background / 10.0)
            return background
        if (bg_traffic_dist == 'uniform'):
            index = self.video_chunk_counter % len(bg_traffic_pattern)
            background = bg_traffic_pattern[index] * MBPS #bps
            delta = background/10.0
            background = np.random.uniform(background-delta, background+delta)
            return background
        
        # index = self.video_chunk_counter % len(BACKGROUND_TRAFFIC_5_1)
        # background = BACKGROUND_TRAFFIC_5_1[index] * MBPS #bps
        # background = np.random.normal(background, background / 10.0)
        # return background

        # background = 0.0
        # if (TRAFFIC_MODEL) == "UNIFORM":
        #     background = np.random.randint(CNO_RAND_MIN, CNO_RAND_MAX)
        # elif (TRAFFIC_MODEL == "NORMAL"):
        #     background = np.random.normal(CNO_RAND_MAX, CNO_RAND_MAX / 10.0)
        # elif (TRAFFIC_MODEL == "REAL"):
        #     background *= rand1
        # elif (TRAFFIC_MODEL == "NORM_BIT"):
        #     bitrate = (VIDEO_BIT_RATE_AVG[rand2] * 1000) / 8.0
        #     background = np.random.normal(bitrate, bitrate / 10.0)
        # return background

    def get_video_chunk(self, quality, video_count, bg_traffic_pattern, bg_traffic_dist ,lc, video_bit_rates):
        # print("\n********** get_video_chunk **********")
        # print(bg_traffic_pattern, bg_traffic_dist, video_bit_rates,lc)
        self.video_chunk_counter += 1  # to keep track of chunks/frames globally
        #video_chunk_size, video_chunk_br = self.get_video_size(quality)
        
        loss_rate_list = []
        ava_ca_list = []
        loss_rate_frac_list = []
        ava_ca_frac_list = []
        frame_counter = 1
        
        rand1 = np.random.randint(1, 15)
        rand2 = np.random.randint(1, len(video_bit_rates))

        capacity = lc
        #background = 0.0
        loss_rate = 0.0
        video = 0.0

        while True:  # download video frames            
            background = self.get_background(rand1, rand2, bg_traffic_pattern, bg_traffic_dist)  #bps
            #background = self.get_background_0(video_count)  #bps
            
            # if (video_count < 5000):
            #     background = 0.0
            # else:
            #     background = 30 * MBPS

            video = self.get_video(quality, video_bit_rates)

            ava_ca = capacity - video - background  #bps
            ava_ca = 0.0 if ava_ca < 0 else ava_ca
            ava_ca_frac = ava_ca / capacity

            loss_rate = (video + background) - capacity
            loss_rate = 0 if loss_rate < 0 else loss_rate
            loss_rate_frac = loss_rate / float(video + background)
            ########
            # print("bg [{0}] video[{1}] ava_ca [{2}] ava_ca_frac [{3}] loss_rate [{4}] loss_rate_frac [{5}]"
            #       .format(background/MBPS, video/MBPS, ava_ca/MBPS, ava_ca_frac, loss_rate, loss_rate_frac))

            # print (capacity,"\t", video,"\t", background)
            ava_ca_frac_list.append(ava_ca_frac) # bytes/s
            loss_rate_frac_list.append(loss_rate_frac)
            loss_rate_list.append(loss_rate)
            ava_ca_list.append(ava_ca)
            
            if (frame_counter < FRAME_INTERVAL):
                frame_counter += 1  # a frame ends so start another one
                # if (self.video_chunk_counter >= TOTAL_VIDEO_CHUNCK):  # a chunk with several frames ends
                #     break
                # video_chunk_size, video_chunk_br = self.get_video_size(quality)
                # continue
            else:
                break

        # exit while loop
        mean_loss_rate_frac = np.mean(loss_rate_frac_list)
        mean_ava_ca_frac = np.mean(ava_ca_frac_list)
        mean_loss_rate = np.mean(loss_rate_list) #bps
        mean_ava_ca = np.mean(ava_ca_list) #bps
        
        assert(len(ava_ca_frac_list) == 1)
        
        end_of_video = False
        if self.video_chunk_counter >= TOTAL_VIDEO_CHUNCK:
            end_of_video = True
            self.video_chunk_counter = 0
            #print("\n***** end of video ******")

        return end_of_video, \
            mean_loss_rate_frac, \
            mean_ava_ca_frac, \
            mean_loss_rate, \
            mean_ava_ca
