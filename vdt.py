import os, signal, datetime

DOMAINS_FILE = "domains.txt"


# Called when Ctrl+C
def sigint_handler(sig, frame):
    print('\n\n[x] SIGINT: Exiting...')

    domains.close()

    quit()
signal.signal(signal.SIGINT, sigint_handler)

if __name__ == '__main__':
    t = datetime.datetime.now()
    print("[+] Starting time: %s-%s-%s %s:%s:%s" % (t.day, t.month, t.year, t.hour, t.minute, t.second))
    print("[+] PID: %d" % os.getpid())

    domains = open(DOMAINS_FILE, 'r')
    
    while True:
        pass
