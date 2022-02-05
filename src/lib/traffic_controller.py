import os

def init(req_per_sec):
    delay = int(1/req_per_sec * 1000)
    command = "tc qdisc add dev eth0 root netem delay %dms" % delay
    print("Executed: " + command)
    os.system(command)