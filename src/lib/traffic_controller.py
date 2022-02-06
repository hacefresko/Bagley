import subprocess

class TrafficController:
    def __init__(self, req_per_sec):
        self.req_per_sec = req_per_sec
        init_commands = [
            "iptables -F OUTPUT",
            "iptables -A OUTPUT -p tcp -d 162.159.136.234 -j ACCEPT",
            "iptables -A OUTPUT -p tcp -m multiport --dports 80,443 -m state --state NEW -m limit --limit %d/s --limit-burst %d -j ACCEPT" % (req_per_sec, req_per_sec),
            "iptables -A OUTPUT -p tcp -m multiport --dports 80,443 -m state --state NEW -j DROP"
        ]

        for c in init_commands:
            p = subprocess.Popen(c)
            if p.wait() != 0:
                return None

    def set(self, req_per_sec):
        change_command = "iptables -R OUTPUT 2 -m multiport --dports 80,443 -m state --state NEW -m limit --limit %d/s --limit-burst %d -j ACCEPT" % (req_per_sec, req_per_sec)

        p = subprocess.Popen(change_command)
        if p.wait() != 0:
            return False

        return True

    def get_rps(self):
        return self.req_per_sec