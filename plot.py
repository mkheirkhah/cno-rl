import matplotlib.pyplot as plt
import numpy as np

filename = './results/cno_log_alt_agent_0_alt'
video_count, mean_video_br, mean_loss_rate, mean_actual_lr = np.loadtxt(filename, unpack=True)
    
plt.plot(video_count, mean_video_br,  ls='--', c='r', lw=0.5, label='MeanVideoBitRate')
plt.plot(video_count, mean_actual_lr, ls='--', c='g', lw=0.5, label='MeanLossRate')
x1,x2,y1,y2 = plt.axis()
# plt.axis([0, x2, 0, y2])
plt.xlabel('Videos (#)')
plt.ylabel('Rates (Kbps)')
plt.title('BitRate and LossRate', fontsize=14, color='black')
# plt.yscale('log')
plt.grid(True)
plt.legend()
plt.show()
