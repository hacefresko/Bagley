import os, signal, datetime, getopt, sys, time

# Called when Ctrl+C
def sigint_handler(sig, frame):
    print('\n\n[x] SIGINT: Exiting...')

    domains_file.close()

    quit()
signal.signal(signal.SIGINT, sigint_handler)

if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'D:')

        for opt, arg in opts:
            if opt == '-D':
                domains_file_name = arg
                domains_found = True

        if not domains_found or domains_file_name == '':
            raise Exception
            
    except Exception:
        print(os.path.basename(__file__) + ' -D <domains file>')
        exit()

    print("[+] Starting time: %s" % datetime.datetime.now())
    print("[+] PID: %d" % os.getpid())
    print("[+] Domains file: %s" % domains_file_name)

    try:
        domains_file = open(domains_file_name, 'r')
    except FileNotFoundError:
        print('[x] Domains file not found')
        exit()

    while True:
        domain = domains_file.readline()
        if not domain:
            time.sleep(5)
            continue
        
        print(domain)
