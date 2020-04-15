from uc2_settings import METRIC_TEMPLATE, METRIC_TEMPLATE_UC2_EXEC, METRIC_TEMPLATE_UC2_CONF

def generate_metric_uc2_exec(metric_value, timestamp, tmp, vce_id):
    #metric = METRIC_TEMPLATE_UC2_EXEC
    metric = tmp
    metric['execution']['value'] = metric_value
    metric['execution']['mac'] = vce_id
    #metric['metric']['timestamp'] = timestamp
    return metric


def generate_metric_uc2_conf(metric_value, timestamp, tmp, vce_id):
    metric_bitrate = {"bitrate": metric_value}
    #metric = METRIC_TEMPLATE_UC2_CONF
    metric = tmp
    metric['vce']['mac'] = vce_id
    metric['vce']['action'] = metric_bitrate
    #metric['vce']['timestamp'] = timestamp
    return metric

def generate_metric_uc2_tm(bw, tp, metric_tmp, metric_type, unit):
    metric = metric_tmp
    metric['unit'] = str(unit)
    metric['vdu_uuid'] = 677
    metric['value'] = bw
    metric['type'] = str(metric_type)
    metric['timestamp'] = tp
    return metric

def generate_metric_uc2_vce(metric_value, timestamp, tmp, vce_id, video_bit_rates, profile):
    metric = tmp
    metric['id'] = vce_id #str
    metric['utc_time'] = timestamp #int
    metric['metric_x'] = video_bit_rates[int(metric_value[2])] #int
    metric['metric_y'] = video_bit_rates[int(metric_value[3])] #int
    metric['metric_z'] = profile
    return metric

def generate_metric_uc2_cno(bandwidth, timestamp, tmp_metric, msg_type):
    metric = tmp_metric
    if (msg_type == "request"):
        metric['sender'] = "UC_2"
        metric['receiver'] = "O-CNO"
        metric['timestamp'] = timestamp
        metric['resource']['bw'] = bandwidth
        metric['option'] = msg_type
    elif (msg_type == "respond"):
        metric['sender'] = "O-CNO"
        metric['receiver'] = "UC_2"
        metric['timestamp'] = timestamp
        metric['resource']['bw'] = bandwidth
        metric['option'] = msg_type
    return metric
