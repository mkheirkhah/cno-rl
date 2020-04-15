from os import path, pardir

PROJECT_ROOT = '/opt/sim'
# =================================
# WHITE LIST OF MONITORING METRICS
# =================================
METRICS_WHITE_LIST = {
    "openstack": ['memory', 'memory.usage', 'memory.resident', 'memory.bandwidth.total', 'memory.bandwidth.local',
                  'memory.swap.in', 'memory.swap.out', 'cpu', 'cpu_util', 'cpu.delta', 'vcpus', 'cpu_l3_cache',
                  'network.incoming.bytes', 'network.incoming.bytes.rate', 'network.outgoing.bytes',
                  'network.outgoing.bytes.rate', 'network.incoming.packets', 'network.incoming.packets.rate',
                  'network.outgoing.packets', 'network.outgoing.packets.rate', 'network.incoming.packets.drop',
                  'network.outgoing.packets.drop', 'network.incoming.packets.error', 'network.outgoing.packets.error'],
    "vmware": ['', ],
    "opennebula": ['', ],
    "unikernels": ['', ],
    "kubernetes": ['', ],
    "elk": ['', ],
}

# =================================
# KAFKA SETTINGS
# =================================
#KAFKA_SERVER = 217.172.11.188:9092'
#KAFKA_CLIENT_ID = 'monitoring-data-translator'
KAFKA_SERVER = '217.172.11.173:9092'
KAFKA_CLIENT_ID = 'CNO_UC2_UCL'

KAFKA_API_VERSION = (0, 10, 1)
KAFKA_PREFIX_TOPIC = "devstack"  # "devstack.*"
#KAFKA_MONITORING_TOPICS = {"openstack": "nvfi.eng.openstack", "vmware": "vmware", }
KAFKA_MONITORING_TOPICS = {"uc2_tm":"trafficmanager.uc2.metrics",\
                           "uc2_qoe":"app.uc2.qoe",\
                           "uc2_vce":"nfvi.tid-onlife.opennebula",\
                           'uc3_load':'ns.instances.trans',\
                           "uc2_mon_exec":'ns.instances.exec',\
                           "uc2_mon_conf":'ns.instances.conf',\
                           "uc2_mon_vce":'app.vce.metrics',\
                           "uc2_cno":'cno'}

KAFKA_TRANSLATION_TOPIC_SUFFIX = "trans"
KAFKA_EXECUTION_TOPIC = {"uc2_exec":'ns.instances.exec',\
                         "uc2_conf":'ns.instances.conf',\
                         "uc2_vce":'app.vce.metrics',\
                         "uc2_cno":'cno',\
                         "uc2_tm":"trafficmanager.uc2.metrics"}

# =================================
# OSM SETTINGS
# =================================
OSM_IP = "192.168.1.171"
OSM_ADMIN_CREDENTIALS = {"username": "admin", "password": "admin"}
OSM_COMPONENTS = {"UI": 'https://{}:8443'.format(OSM_IP),
                  "SO-API": 'https://{}:8008'.format(OSM_IP),
                  "RO-API": 'http://{}:9090'.format(OSM_IP)}

# =================================
# TEMPLATE OF MONITORING METRIC
# =================================
METRIC_TEMPLATE = {
    "vim": {
        "name": "dev-openstack",
        "type": "openstack"
    },
    "mano": {
        "vdu": {
            "id": "da6849d7-663f-4520-8ce0-78eaacf74f08",
            "flavor": {
                "name": "ubuntuvnf_vnfd-VM-flv",
                "ram": 4096,
                "id": "c46aecab-c6a9-4775-bde2-070377b8111f",
                "vcpus": 1,
                "disk": 10,
                "swap": 0,
                "ephemeral": 0
            },
            "image_id": "a46178eb-9f69-4e44-9058-c5eb5ded0aa3",
            "status": "running"
        },
        "vnf": {
            "id": "00fa217e-cf90-447a-975f-6d838e7c20ed",
            "nvfd_id": None
        },
        "ns": {
            "id": "abf07959-053a-4443-a96f-78164913277b",
            "nsd_id": None
        },
        "metric": {
            "name": "network.incoming.packets.rate",
            "value": None,
            "timestamp": None,
            "type": "gauge",
            "unit": "Mbps"
        }
    }
}

METRIC_TEMPELATE_UC2 = {
    "mano": {
        "vdu": {
            "ip_address": "str",
            "name": "vdu_name",
            "mgmt-interface": "null",
            "image_id": "null",
            "status": "ACTIVE",
            "flavor": {
                "disk": "null",
                "ram": "null",
                "vcpus": "null"
            },
            "id": "integer"
        },
        "ns": {
            "name": "uuid",
            "nsd_name": "str",
            "nsd_id": "null",
            "id": "uuid"
        },
        "vim": {
            "type": "opennebula",
            "uuid": "uuid",
            "name": "str",
            "url": "ip",
            "tag": "kubernetes"
        },
        "vnf": {
            "name": "null",
            "vnfd_name": "str",
            "vnfd_id": "1uuid",
            "short_name": "null",
            "id": "uuid"
        }
    },
    "metric": {
        "timestamp": "2019-02-13T15:45:54.553000Z",
        "type": "counter",
        "name": "diskrdbytes",
        "value": "349236528",
        "unit": "bytes"
    },
    # "metric": {
    #     "timestamp": "2019-03-28T10:20:05.000000Z",
    #     "vdu_uuid": 1203,
    #     "value": "349236528",
    #     "type": "diskrdbytes",
    #     "unit": "bytes"
    # },
    "analysis": {
        "action": "true"
    },
    "execution": {
        "planning": "set_vce_bitrate",
        "value": "number"
    }
}

# Kafka toptic:  ns.instances.exec
METRIC_TEMPLATE_UC2_EXEC = {
    "analysis": {
        "action": "true"
    },
    "execution": {
        "mac": "vce_id (str)",
        "planning": "set_vce_bitrate",
        "value": "the value of the bitrate"
    }
    # the rest needs to be completed
}

# Kafka topic: app.vce.metrics
METRIC_TEMPLATE_UC2_VCE = {
    "id": "mac_address|string",
    "utc_time": 1580915872858,
    "metric_x": "float or int",
    "metric_y": "float or int",
    "metric_z": "float or int"
}

# Kafka topic: trafficmanager.uc2.metrics
METRIC_TEMPLATE_UC2_TM = {
    "unit": "string",
    "vdu_uuid": "vm_id",
    "value": "float",
    "type": "metric_name",
    "timestamp": "2020-03-03T10:50:00.000000Z"
}

METRIC_TEMPLATE_UC2_CNO_REQUEST = {
    "sender": "UC_2",
    "receiver": "O-CNO",
    "timestamp": 1580915872858,
    "resource":
    {
        "GPU": 0,
        "CPU": 0,
        "RAM": None,
        "disk": None,
        "bw": +20
    },
    "option": "request"
}
METRIC_TEMPLATE_UC2_CNO_RESPOND = {
    "sender": "O-CNO",
    "receiver": "UC_2",
    "timstamp": 1580915872858,
    "resource":
    {
        "GPU": 0,
        "CPU": 0,
        "RAM": None,
        "disk": None,
        "bw": +20
    },
    "option": "granted"
}


# Kafka topic: ns.instances.conf
METRIC_TEMPLATE_UC2_CONF = {
    "vce": {
        "mac": "string",
        #"vdu_uuid": "string (VM id)",
        "action": {"bitrate": "integer|kbps"}
    }
}

# Kafka toptic:  ns.instances.exec 
METRIC_TEMPLATE_UC3_EXEC = {
    "analysis": {
        "action": "true"
    },
    "execution": {
        "planning": 'vnf_scale_out',
        "value": "null"
    },
    "mano": {
        "ns": {
            "id": "13987ea3-054a-459b-a24d-f4c76679edaf",
            "name": "ns_takis",
            "nsd_name": "cirros_2vnf_ns",
            "nsd_id": "d5c99561-ec46-4480-8377-b5b218b8b1e5"
        },
        "vnf": {
            "id": "abd00f09-dff1-40f1-be83-637a456ed400",
            "short_name": "null",
            "vnfd_name": "cirros_vnfd",
            "name": "null",
            "vnfd_id": "16c40d2e-7a1b-4f22-9e50-3f7ede3e9fc4"
        },
        "vdu": {
            "id": "99f76771-3a39-42ae-a09c-2f79f459a9c9",
            "image_id": "a46178eb-9f69-4e44-9058-c5eb5ded0aa3",
            "ip_address": "192.168.207.2",
            "flavor": {
                "id": "c46aecab-c6a9-4775-bde2-070377b8111f",
                "disk": 10,
                "swap": 0,
                "vcpus": 1,
                "ram": 4096,
                "name": "ubuntuvnf_vnfd-VM-flv",
                "ephemeral": 0
            },
            "mgmt-interface": "null",
            "name": "instance-00000009",
            "status": "running"
        },
        "vim": {
            "uuid": "48eb5bd0-feaa-48ed-b0d7-6d2b8ad0385e",
            "type": "openstack",
            "tag": "openstack",
            "name": "devstack-ocata",
            "url": "http://192.168.1.147/identity/v3"
        }
    }
}

# ==================================
# LOGGING SETTINGS
# ==================================
# See more: https://docs.python.org/3.5/library/logging.config.html
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'detailed': {
            'class': 'logging.Formatter',
            'format': "[%(asctime)s] - [%(name)s:%(lineno)s] - [%(levelname)s] %(message)s",
        },
        'simple': {
            'class': 'logging.Formatter',
            'format': '%(name)-15s %(levelname)-8s %(processName)-10s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'simple',
        },
        'translator': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': "{}/logs/translator.log".format(PROJECT_ROOT),
            'mode': 'w',
            'formatter': 'detailed',
            'level': 'DEBUG',
            'maxBytes': 2024 * 2024,
            'backupCount': 5,
        },
        'soapi': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': "{}/logs/soapi.log".format(PROJECT_ROOT),
            'mode': 'w',
            'formatter': 'detailed',
            'level': 'DEBUG',
            'maxBytes': 2024 * 2024,
            'backupCount': 5,
        },
        'errors': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': "{}/logs/error.log".format(PROJECT_ROOT),
            'mode': 'w',
            'level': 'ERROR',
            'formatter': 'detailed',
            'maxBytes': 2024 * 2024,
            'backupCount': 5,
        },
    },
    'loggers': {
        'translator': {
            'handlers': ['translator']
        },
        'soapi': {
            'handlers': ['soapi']
        },
        'errors': {
            'handlers': ['errors']
        }
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console']
    },
}
