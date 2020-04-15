#################################################################################
# Title:       Implementation of an RL algortihm for UC2, 5G-MEDIA project
# Author:      Morteza Kheirkhah
# Institution: University College London (UCL), UK
# Email:       m.kheirkhah@ucl.ac.uk
# Homepage:    http://www.uclmail.net/users/m.kheirkhah/
# Note:        Original code has been written for the Pensieve paper (SIGCOMM'17)
#################################################################################

import math
import os
import logging
import numpy as np
import multiprocessing as mp
import tensorflow as tf
import env_cno_mks
import a3c_cno_mks
import load_trace
import argparse
# os.environ["TF_CPP_MIN_LOG_LEVEL"]="2"

S_INFO = 3  # states
S_LEN = 8   # past history of states
TRAIN_SEQ_LEN = 100  # take as a train batch
MODEL_SAVE_INTERVAL = 100


M_IN_K = 1000.0
BITS_IN_MEGA = 1000000.0
SMOOTH_PENALTY = 1
DEFAULT_QUALITY = 1  # default video quality without agent

RAND_RANGE = 1000
SUMMARY_DIR = './results'
LOG_FILE = './results/cno_log_alt'
TEST_LOG_FOLDER = './test_results/'
TRAIN_TRACES = './cooked_traces/'

#NN_MODEL = './results/nn_model_ep_10800_m4_bg51_v20_bg10_l500_sm1.ckpt' #(Dry-run)
#NN_MODEL = './trained_models/nn_model_ep_79000_m4_bg51_v20_bg10_l500_sm1.ckpt' #[<][rg]
NN_MODEL = None

# def testing(epoch, nn_model, log_file):
#     # clean up the test results folder
#     os.system('rm -r ' + TEST_LOG_FOLDER)
#     os.system('mkdir ' + TEST_LOG_FOLDER)
    
#     # run test script
#     os.system('python rl_test_cno_alt.py ' + nn_model)
    
#     # append test performance to the log
#     rewards = []
#     test_log_files = os.listdir(TEST_LOG_FOLDER)
#     for test_log_file in test_log_files:
#         reward = []
#         with open(TEST_LOG_FOLDER + test_log_file, 'rb') as f:
#             for line in f:
#                 parse = line.split()
#                 try:
#                     reward.append(float(parse[-1]))
#                 except IndexError:
#                     break
#         rewards.append(np.sum(reward[1:]))

#     rewards = np.array(rewards)

#     rewards_min = np.min(rewards)
#     rewards_5per = np.percentile(rewards, 5)
#     rewards_mean = np.mean(rewards)
#     rewards_median = np.percentile(rewards, 50)
#     rewards_95per = np.percentile(rewards, 95)
#     rewards_max = np.max(rewards)

#     log_file.write(str(epoch) + '\t' +
#                    str(rewards_min) + '\t' +
#                    str(rewards_5per) + '\t' +
#                    str(rewards_mean) + '\t' +
#                    str(rewards_median) + '\t' +
#                    str(rewards_95per) + '\t' +
#                    str(rewards_max) + '\n')
#     log_file.flush()

def central_agent(net_params_queues, exp_queues,
                  alpha, alr, clr, lc, name_nn_model, parallel_agents, dimension, video_bit_rates):

    assert len(net_params_queues) == parallel_agents
    assert len(exp_queues) == parallel_agents

    logging.basicConfig(filename=LOG_FILE + '_central',
                        filemode='w',
                        level=logging.INFO)

    with tf.Session() as sess, open(LOG_FILE + '_test', 'wb') as test_log_file:
        test_log_file.flush # only to silent the python-check
        
        # create actor and critic objects
        actor = a3c_cno_mks.ActorNetwork(sess,
                                         state_dim=[S_INFO, S_LEN], action_dim=dimension,
                                         learning_rate=alr)
        critic = a3c_cno_mks.CriticNetwork(sess,
                                           state_dim=[S_INFO, S_LEN],
                                           learning_rate=clr)

        summary_ops, summary_vars = a3c_cno_mks.build_summaries()

        sess.run(tf.global_variables_initializer())

        # write tf$summary$scalar ops into a file for tensorboard to virtualise
        writer = tf.summary.FileWriter(SUMMARY_DIR, sess.graph)  # training monitor
        saver = tf.train.Saver()  # save neural net parameters

        # restore neural net parameters
        nn_model = NN_MODEL
        if nn_model is not None:  # nn_model is the path to file
            saver.restore(sess, nn_model)
            print("Model restored.")

        epoch = 0

        # assemble experiences from agents, compute the gradients
        while True:
            # synchronize the network parameters of work agent
            actor_net_params = actor.get_network_params()
            critic_net_params = critic.get_network_params()
            for i in range(parallel_agents):
                net_params_queues[i].put([actor_net_params, critic_net_params])
                # Note: this is synchronous version of the parallel training,
                # which is easier to understand and probe. The framework can be
                # fairly easily modified to support asynchronous training.
                # Some practices of asynchronous training (lock-free SGD at
                # its core) are nicely explained in the following two papers:
                # https://arxiv.org/abs/1602.01783
                # https://arxiv.org/abs/1106.5730
                
            # record average reward and td loss change in the experiences from the agents
            total_batch_len = 0.0
            total_reward = 0.0
            total_td_loss = 0.0
            total_entropy = 0.0
            total_agents = 0.0 

            # assemble experiences from the agents
            actor_gradient_batch = []
            critic_gradient_batch = []

            for i in range(parallel_agents):
                s_batch, a_batch, r_batch, terminal, info = exp_queues[i].get()

                actor_gradient, critic_gradient, td_batch = \
                    a3c_cno_mks.compute_gradients(
                        s_batch=np.stack(s_batch, axis=0),
                        a_batch=np.vstack(a_batch),
                        r_batch=np.vstack(r_batch),
                        terminal=terminal, actor=actor, critic=critic)

                actor_gradient_batch.append(actor_gradient)
                critic_gradient_batch.append(critic_gradient)

                total_reward += np.sum(r_batch)
                total_td_loss += np.sum(td_batch)
                total_batch_len += len(r_batch)
                total_agents += 1.0
                total_entropy += np.sum(info['entropy'])

            # compute aggregated gradient
            assert parallel_agents == len(actor_gradient_batch)
            assert len(actor_gradient_batch) == len(critic_gradient_batch)

            for i in range(len(actor_gradient_batch)):
                actor.apply_gradients(actor_gradient_batch[i])
                critic.apply_gradients(critic_gradient_batch[i])

            # log training information
            epoch += 1
            avg_reward = total_reward  / total_agents
            avg_td_loss = total_td_loss / total_batch_len
            avg_entropy = total_entropy / total_batch_len

            logging.info('Epoch: ' + str(epoch) +
                         ' TD_loss: ' + str(avg_td_loss) +
                         ' Avg_reward: ' + str(avg_reward) +
                         ' Avg_entropy: ' + str(avg_entropy))

            summary_str = sess.run(summary_ops, feed_dict={
                summary_vars[0]: avg_td_loss,
                summary_vars[1]: avg_reward,
                summary_vars[2]: avg_entropy
            })

            writer.add_summary(summary_str, epoch)
            writer.flush()

            if epoch % MODEL_SAVE_INTERVAL == 0:
                # Save the neural net parameters to disk.
                save_path = saver.save(sess, SUMMARY_DIR + "/" + name_nn_model + "_" + str(epoch) + ".ckpt")
                logging.info("Model saved in file: " + save_path)
                # testing(epoch, SUMMARY_DIR + "/"+ name_nn_model +"_" + str(epoch) + ".ckpt", test_log_file)

def agent(agent_id, all_cooked_time, all_cooked_bw, net_params_queue, exp_queue,
          alpha, bg_traffic_pattern, bg_traffic_dist, alr, clr, lc, name_nn_model,
          dimension, video_bit_rates, video_br_weights, r_func):

    # agent id would be used as a seed to randomize env between agents
    net_env = env_cno_mks.Environment(all_cooked_time=all_cooked_time,
                                      all_cooked_bw=all_cooked_bw,
                                      random_seed=agent_id)

    with tf.Session() as sess, open(LOG_FILE + '_agent_' + str(agent_id), 'w') as log_file, \
         open(LOG_FILE + '_agent_' + str(agent_id) + '_alt', 'w') as lf:

        # create actor and critic objects
        actor = a3c_cno_mks.ActorNetwork(sess,
                                         state_dim=[S_INFO, S_LEN], action_dim=dimension,
                                         learning_rate=alr)
        critic = a3c_cno_mks.CriticNetwork(sess,
                                           state_dim=[S_INFO, S_LEN],
                                           learning_rate=clr)

        # initial synchronization of the network parameters from the coordinator
        actor_net_params, critic_net_params = net_params_queue.get()
        actor.set_network_params(actor_net_params)
        critic.set_network_params(critic_net_params)

        last_bit_rate = DEFAULT_QUALITY
        bit_rate = DEFAULT_QUALITY

        action_vec = np.zeros(dimension)
        action_vec[bit_rate] = 1

        # state, action and reward batches
        s_batch = [np.zeros((S_INFO, S_LEN))]  # 3x8 vector filled with zeros
        a_batch = [action_vec]
        r_batch = []
        entropy_record = []
        video_count = 1 
        mean_loss_rate_list = []
        mean_lr_list = []
        video_bit_rate_list = []
        #mean_throughput_trace_list = []
        # time_stamp = 0

        # BACKGROUND_TRAFFIC = [0,5,10,15,20,25,30,35,30,25,20,15,10,5,0]  # unused
        
        while True:  # experience video streaming forever
            # index = video_count % len(BACKGROUND_TRAFFIC)  # unused
            # background = BACKGROUND_TRAFFIC[index] * 1000000.0  # unused
            
            end_of_video, mean_loss_rate, mean_free_ca, mean_lr, mean_ca = \
                net_env.get_video_chunk(bit_rate, video_count, bg_traffic_pattern, bg_traffic_dist, lc, video_bit_rates)
            
            # time_stamp += delay  # in ms
            # time_stamp += sleep_time  # in ms

            video_bit_rate_list.append(video_bit_rates[bit_rate])
            mean_loss_rate_list.append(mean_loss_rate) 
            mean_lr_list.append(mean_lr)
            #mean_throughput_trace_list.append(mean_throughput_trace) 
                        
            # REWARD FUCNTION
            r_bitrate = video_bit_rates[bit_rate] / M_IN_K
            r_alpha =  alpha * mean_loss_rate
            r_smooth = SMOOTH_PENALTY * np.abs(video_br_weights[bit_rate] - video_br_weights[last_bit_rate])
            reward = 0
            if (r_func == 'bls'):
                reward = r_bitrate - r_alpha - r_smooth
            elif(r_func == 'bl'):
                reward = r_bitrate - r_alpha
            elif (r_func == 'b'):
                reward = r_bitrate
            else:
                exit(1)
                
            # reward = video_bit_rates[bit_rate] / M_IN_K \
            #     - alpha * mean_loss_rate \
            #     - SMOOTH_PENALTY * np.abs(video_br_weights[bit_rate]
            #                               - video_br_weights[last_bit_rate])
            
            r_batch.append(reward)

            last_bit_rate = bit_rate

            # retrieve previous state
            if len(s_batch) == 0:
                state = [np.zeros((S_INFO, S_LEN))]
            else:
                state = np.array(s_batch[-1], copy=True)

            # dequeue history record
            # shift the element to the left, move the first element to the end
            # this end value will be updated with the new one, make sure we always
            # keep the information of the last 8 chunks.
            state = np.roll(state, -1, axis=1)

            # STATES
            # last chunk bit rate (number)
            state[0, -1] = video_bit_rates[bit_rate] / float(np.max(video_bit_rates))  # last quality
            # past chunk available capacity (array) # video_chunk_size is measured in byte
            state[1, -1] = float(mean_free_ca) #fraction
            # loss rate (array)
            state[2, -1] = float(mean_loss_rate) #fraction
            
            # print("states: bit_rate [{0}] capacity [{1}] loss_rate [{2}]"
            #       .format(state[0, -1], state[1, -1], state[2, -1]))

            # compute action probability vector
            action_prob = actor.predict(np.reshape(state, (1, S_INFO, S_LEN)))
            action_cumsum = np.cumsum(action_prob)
            bit_rate = (action_cumsum > np.random.randint(1, RAND_RANGE) / float(RAND_RANGE)).argmax()
            #print("new bitrate [{0}] last_bit_rate [{1}]".format(bit_rate, last_bit_rate))

            # Note: we need to discretize the probability into 1/RAND_RANGE steps,
            # because there is an intrinsic discrepancy in passing single state and batch states
            entropy_record.append(a3c_cno_mks.compute_entropy(action_prob[0]))

            # log time_stamp, bit_rate, buffer_size, reward
            log_file.write(#str(time_stamp) + '\t' +
                           str(video_bit_rates[bit_rate]) + '\t' +
                           str(reward) + '\t' +
                           str(mean_loss_rate * 8.0 / M_IN_K) + '\t' + # B/s -> b/s -> Kb/s
                           str(video_count) + '\n')
            log_file.flush()

            # report experience to the coordinator
            if len(r_batch) >= TRAIN_SEQ_LEN or end_of_video:
                exp_queue.put([s_batch[1:],  # ignore the first chuck
                               a_batch[1:],  # since we don't have the
                               r_batch[1:],  # control over it
                               end_of_video,
                               {'entropy': entropy_record}])

                # synchronize the network parameters from the coordinator
                actor_net_params, critic_net_params = net_params_queue.get()
                actor.set_network_params(actor_net_params)
                critic.set_network_params(critic_net_params)

                del s_batch[:]
                del a_batch[:]
                del r_batch[:]
                del entropy_record[:]

                log_file.write('\n')  # so that in the log we know where video ends

            # store the state and action into batches
            if end_of_video:
                # flush video bit rate and mean_loss_rate -----------------------------
                lf.write(str(video_count) + '\t'+
                         str(np.mean(video_bit_rate_list)) + '\t' + # kbps
                         str(np.mean(mean_loss_rate_list)) + '\t' + # fraction
                         str(np.mean(mean_lr_list) / M_IN_K) + '\t' + # actual loss #kbps
                         #str(np.mean(mean_throughput_trace_list) * 8.0 / M_IN_K) + '\t' +
                         '\n')
                lf.flush()
                # writer = tf.summary.FileWriter('./graphs', sess.graph)
                # # writer.add_summary(np.mean(mean_rl_list), epoch)
                # writer.flush()

                video_count += 1 
                mean_loss_rate_list = []
                video_bit_rate_list = []
                mean_lr_list = []
                #mean_throughput_trace_list = []
                assert(len(mean_loss_rate_list) == 0)
                #---------------------------------------------------------------------
                last_bit_rate = DEFAULT_QUALITY
                bit_rate = DEFAULT_QUALITY  # use the default action here

                action_vec = np.zeros(dimension)
                action_vec[bit_rate] = 1

                s_batch.append(np.zeros((S_INFO, S_LEN)))
                a_batch.append(action_vec)
            else:
                s_batch.append(state)

                action_vec = np.zeros(dimension)
                action_vec[bit_rate] = 1
                a_batch.append(action_vec)

def generate_bg_traffic(lc, shape="random"):
    capacity = lc/BITS_IN_MEGA #Mbps e.g. 50 Mbps
    mid_range = int(capacity/2.0)
    background_list = []
    if (shape == "sawtooth"):
        for i in range(0, mid_range, 5):
            background_list.append(i)
        for i in range (mid_range, 0, -5):
            background_list.append(i)
        return background_list
    if (shape == "random"):
        background_list = np.random.randint(0, int(capacity), dtype=int, size=20)
        return background_list
 
def generate_bit_rates_auto(dimension, lowest_br, highest_br):
    br_range = highest_br - lowest_br
    delta = br_range / float(dimension-1)
    bit_rate_list = []
    current_weight = 1.0
    bit_rate_weight_list = []
    for i in range(dimension):
        bit_rate_list.append(math.floor(lowest_br/M_IN_K)) #kbps
        lowest_br += delta
        bit_rate_weight_list.append(current_weight)
        current_weight= round(current_weight + 0.2, 2)
    return bit_rate_list, bit_rate_weight_list

def generate_bit_rates_manually(dimension, lowest_br, highest_br, delta):
    current_weight = 1.0
    bit_rate_weight_list = []
    bit_rate_list = []
    for i in range(dimension):
        bit_rate_list.append(math.floor(lowest_br/M_IN_K)) #kbps
        lowest_br += delta
        bit_rate_weight_list.append(current_weight)
        current_weight= round(current_weight + 0.2, 2)
    return bit_rate_list, bit_rate_weight_list

def main():

    # Parameter configuration
    parser = argparse.ArgumentParser(description='Parameters Setting for Use-Case-2 (UC2) of the 5G-MEDIA project.',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     prog='multi_agent_cno_mks',
                                     epilog="If you have any questions please contact "
                                     "Morteza Kheirkhah <m.kheirkhah@ucl.ac.uk>")
    parser.add_argument('--alpha',
                        help="Alpha is a weight factor for the loss rate parameter used in "
                        " the reward function, default=500.",
                        type=int, default=500, dest='ALPHA')
    parser.add_argument("--alr",
                        help="Actor learning rate, default=0.0001",
                        type=float, default=0.0001)
    parser.add_argument("--clr",
                        help="Critic learning rate, default=0.001",
                        type=float, default=0.001)
    parser.add_argument("--lc",
                        help="Link capacity, default=20 (Mbps)",
                        type=int, default=20)
    parser.add_argument("--nn",
                        help="Name for a (trained) neural network model with .ckpt extension. "
                        "These files are stored in the './results' folder, default=NN_MODEL",
                        type=str, default='NN_MODEL')
    parser.add_argument("--pa",
                        help="Number of parallel agents. "
                        "This can be set according to the number of CPUs available on your machine. "
                        "default=1",
                        type=int, default=1, choices=range(1, mp.cpu_count()+1))
    parser.add_argument("--dim",
                        help="Dimension parameter dictates the total number of bitrates to support, default=10",
                        type=int, default=10)
    parser.add_argument("--br_low",
                        help="Lowest bitrate that is supported, default=5 (Mbps)",
                        type=int, default=5)
    parser.add_argument("--br_inc",
                        help="Differences in value between bitrates, default=2 (Mbps)",
                        type=int, default=2)
    parser.add_argument("--br_manual",
                        help="Generate bitrates manually according to 3 parameters: "
                        "--lc, --br_low, and --dim",
                        type=bool, default=False)
    parser.add_argument("--br_auto",
                        help="Generate bitrates automatically according to 4 parameters: "
                        "--lc, --br_low, --br_inc, and --dim",
                        type=bool, default=False)
    parser.add_argument("--bg_auto",
                        help="Generate background traffic automatically, with default shape of sawtooth. "
                        "To change the shape see --bg_shape",
                        type=bool, default=False)
    parser.add_argument("--bg_shape",
                        help="Shape/pattern of background traffic, e.g., it could be sawtooth-like or with no shape (random),"
                        " default=sawtooth",
                        type=str, default='sawtooth', choices=['sawtooth', 'random'])
    parser.add_argument("--clean",
                        help="Remove all files in 'results' folder, default=1 (True), and 0 (False)",
                        type=int, default=1, choices=[0,1])
    parser.add_argument('--btp',
                        help="Background traffic pattern, "
                        "default=[0, 2, 4, 6, 8, 10, 12, 14, 15, 14, 12, 10, 8, 6, 4, 2, 0] (Mbps)",
                        default=[0, 2, 4, 6, 8, 10, 12, 14, 15, 14, 12, 10, 8, 6, 4, 2, 0],
                        type=int, nargs='+')
    parser.add_argument("--btd",
                        help="Background traffic distribution e.g. Normal or Uniform, default=normal",
                        type=str, default='normal', dest="btd", choices=['normal', 'uniform'])
    parser.add_argument("--br_weight",
                        help="Reward container holds similar number of elements as the bitrate container. "
                        "It imposes penalty if the algortihm largely change bitrates.",
                        type=int, default=[1, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8])
    parser.add_argument('--br',
                        help="List of bitrates "
                        "default=[5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 15000, 20000] (Kbps). "
                        "By changing this, make sure that --lc, --bg_auto are configured",
                        default=[5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 15000, 20000],
                        type=int, nargs='+')
    parser.add_argument('--r_func',
                        help="Reward function variants: "
                        "{bls} has bitrate, lossrate and smoothness,  "
                        "{bl} has bitrate and loss_rate, "
                        "{b} has only bitrate",
                        default='bls', type=str, choices=['bls', 'bl', 'b'])
    parser.add_argument("--seed",
                        help="A seed to allow the reprodution of a traning session",
                        type=int, default=40)
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0')
    args = parser.parse_args()
    
    br_manual = args.br_manual
    br_auto = args.br_auto
    alpha = args.ALPHA 
    actor_learning_rate = args.alr
    critic_learning_rate = args.clr
    link_capacity = args.lc * BITS_IN_MEGA
    name_nn_model = args.nn 
    parallel_agents = args.pa
    dimension = args.dim # if args.dim else 10
    clean = args.clean
    bg_traffic_pattern = args.btp
    bg_traffic_dist = args.btd 
    br_low = args.br_low * BITS_IN_MEGA
    bg_auto = args.bg_auto
    bg_shape = args.bg_shape
    seed = args.seed
    br_inc = args.br_inc * BITS_IN_MEGA
    r_func = args.r_func
    
    if (clean>0):
        os.system("rm ./results/*")
    
    # video_bit_rates = generate_bit_rates(dimension, 5000000, link_capacity)
    if (br_manual):
        video_bit_rates, video_br_weights = generate_bit_rates_manually(dimension, br_low, link_capacity, br_inc)
    elif (br_auto):
        video_bit_rates, video_br_weights = generate_bit_rates_auto(dimension, br_low, link_capacity)
    else:
        video_bit_rates = args.br
        video_br_weights = args.br_weight
        # video_bit_rates = [5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 15000, 20000]
        # video_bit_rates = video_bit_rates[:dimension]

    if (bg_auto):
        bg_traffic_pattern = generate_bg_traffic(link_capacity, bg_shape)
        
    print("\n******************************************************************************"
          "\nAlpha\t\t\t[{0}]" "\nActor Learning Rate\t[{2}]"
          "\nCritic Learning Rate\t[{3}]"
          "\nLink Capacity\t\t[{4}] (bps)"
          "\nModel Name\t\t[{5}]"
          "\nParallel Agents\t\t[{6}]"
          "\nAvaialble CPUs to use\t[{7}]"
          "\nDimension\t\t[{8}]"
          "\nLowest bitrate\t\t[{9}] (bps)"
          "\nDelat between bitrates\t[{10}] (bps)"
          "\nClean 'result' folder\t[{11}]"
          "\nBG Traffic Model\t{1} (Mbps)"
          "\nBG Traffic Dist\t\t[{12}]"
          "\nAuto bitrate selection\t[{13}]"
          "\nAuto BG traffic\t\t[{14}]"
          "\nBG shape\t\t[{15}]"
          "\nBitrates\t\t{16} (Kbps)"
          "\nVideo_Bitrates_weight\t{18}"
          "\nr-func\t\t\t[{19}]"
          "\nSeed\t\t\t[{17}]"
          "\n******************************************************************************"
          .format(alpha, bg_traffic_pattern, actor_learning_rate,critic_learning_rate,
                  link_capacity,name_nn_model,parallel_agents, mp.cpu_count(), dimension,
                  br_low,br_inc, clean, bg_traffic_dist, br_auto, bg_auto,
                  bg_shape, video_bit_rates, seed, video_br_weights, r_func))

    np.random.seed(seed)
    assert len(video_bit_rates) == dimension

    # create result directory (if not exists)
    if not os.path.exists(SUMMARY_DIR):
        os.makedirs(SUMMARY_DIR)

    # inter-process communication queues
    net_params_queues = []
    exp_queues = []
    for i in range(parallel_agents):
        net_params_queues.append(mp.Queue(1))
        exp_queues.append(mp.Queue(1))

    # create a coordinator and multiple agent processes
    # (note: threading is not desirable due to python GIL)
    coordinator = mp.Process(target=central_agent,
                             args=(net_params_queues, exp_queues,
                                   alpha,
                                   actor_learning_rate,
                                   critic_learning_rate,
                                   link_capacity,
                                   name_nn_model,
                                   parallel_agents,
                                   dimension,
                                   video_bit_rates))
    
    coordinator.start()

    all_cooked_time, all_cooked_bw, _ = load_trace.load_trace(TRAIN_TRACES)
    agents = [] # list of processes

    # create multiple processes/agents, and passing args to each
    for i in range(parallel_agents):
        agents.append(mp.Process(target=agent,
                                 args=(i, all_cooked_time, all_cooked_bw,
                                       net_params_queues[i],
                                       exp_queues[i],
                                       alpha,
                                       bg_traffic_pattern,
                                       bg_traffic_dist,
                                       actor_learning_rate,
                                       critic_learning_rate,
                                       link_capacity,
                                       name_nn_model,
                                       dimension,
                                       video_bit_rates, video_br_weights, r_func)))

    # start processes/agents in parallel
    for i in range(parallel_agents):
        agents[i].start()

    # wait unit training is done
    coordinator.join()

# confirm the code is under main function
if __name__ == '__main__':
    main()
