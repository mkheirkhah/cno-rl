
# CNO for the Remote and Smart Production Use Case

This repository includes the following components:
- A simulation platform for training a neural network (NN) model with the A3C algorithm. A trained NN model is used to dynamically adjust the bitrate of a live video content. Our simulator permits you to train a NN model with real and syntactically generated traffic traces for both video and background traffic.
- The SS-CNO arbitrator algorithm for the 5G-MEDIA UC2 multi-session scenario (rl_uc2.py).
- The O-CNO arbitrator algorithm for the 5G-MEDIA UC2 multi-session scenario (uc2_cno_com.py).


## Installation of the CNO RL training

1. Install git and gnuplot

```
brew install git gnuplot (Mac users)
sudo apt install -y git gnuplot (Linux users)
```

2. Install a version of python if you do not have one. CNO should work
   with all python versions (I’ve tested it with v3.5, v3.6, v2.7)
   
```
[Mac users only]
brew install python3 [Python 3.7.4] OR brew install python@2 [Python 2.7]

[Linux users only]
sudo apt-get install zlib1g-dev
wget https://www.python.org/ftp/python/3.6.7/Python-3.6.7.tar.xz [Choose a release for Linux from https://www.python.org/downloads/source/]
tar -xvf Python-3.6.7.tar
cd Python-3.6.3
./configure
make
make install
python3.6 -V -> Python3.67rc1 [/usr/bin/local/python3.6]
```

3. Installs the following python packages afterwards via pip

``` 
pip install virtualenv virtualenvwrapper
```

4. Create a new virtualenv (e.g. for python3.5). Note that if do not
   want to use virtualenv, continue from item #6

``` 
which python3.5 -> e.g. /usr/bin/python3.5 that is related to the default python that comes with Ubuntu16.4
virtualenv --python=/usr/bin/python3.5 ~/virtualenv/py3.5 [Linux/Mac users only]
conda create -n py3.5 python=3.5 anaconda [Windows users only]
``` 

5. Activate your new python environment

``` 
source ~/virtualenv/py3.5 [Mac/Linux users only]
conda activate py3.5 [Windows users only]
``` 

6. Finally install essential packages for CNO

``` 
pip install tflearn tensorflow matplotlib [Mac/Linux/Windows]
```

7. Finally, clone the CNO source code from my GitHub. Make sure you
   are using "deployed" branch.

```
git clone -b deployed https://github.com/mkheirkhah/5gmedia.git
git branch [* deployed]
```


## Execution of the CNO RL training at your laptop

* Executing code with default settings

``` 
python multi_agent_cno_mks.py
```

* To explore available parameters to change

``` 
python multi_agent_cno_mks.py --help
```

* To monitor parameters (e.g. loss, reward, entropy) during a training
session

```
tensorboard --logdir ./results
```

* For plotting mean loss-rate and mean video-bit-rate after a training
session is completed

```
python plot.py
```

## Authors
- Morteza Kheirkhah <m.kheirkhah@ucl.ac.uk>

## Acknowledgements
This project has received funding from the European Union’s Horizon 2020 research and innovation 
programme under grant agreement *No 761699*. The dissemination of results herein reflects only 
the author’s view and the European Commission is not responsible for any use that may be made 
of the information it contains.

## License
[MIT](LICENSE)
