import subprocess

class TrafficController:
    def __init__(self, req_per_sec):
        self.req_per_sec = req_per_sec
        init_commands = [
            ["iptables", "-F", "OUTPUT"],
            ["iptables", "-A", "OUTPUT", "-p", "tcp", "-d", "162.159.136.234", "-j", "ACCEPT"],
            ["iptables", "-A", "OUTPUT", "-p", "tcp", "-m", "multiport", "--dports", "80,443", "-m", "state", "--state", "NEW", "-m", "limit", "--limit", str(req_per_sec) + "/s",  "--limit-burst", str(req_per_sec), "-j", "ACCEPT"],
            ["iptables", "-A", "OUTPUT", "-p", "tcp", "-m", "multiport", "--dports", "80,443", "-m", "state", "--state", "NEW", "-j", "DROP"]
        ]

        for c in init_commands:
            p = subprocess.run(c, capture_output=True)
            if p.returncode != 0:
                msg = 'iptables [%d]: %s' % (p.returncode, p.stderr.decode())
                raise Exception(msg)

    def set(self, req_per_sec):
        change_command = ["iptables", "-R", "OUTPUT", "2", "-p", "tcp", "-m", "multiport", "--dports", "80,443", "-m", "state", "--state", "NEW", "-m", "limit", "--limit", str(req_per_sec) + "/s",  "--limit-burst", str(req_per_sec), "-j", "ACCEPT"]

        p = subprocess.run(change_command, capture_output=True)
        if p.returncode != 0:
            return False

        return True

    def get_rps(self):
        return self.req_per_sec