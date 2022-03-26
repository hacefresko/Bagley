import time, re, random, string, shutil, subprocess, os
from urllib.parse import urljoin

from lib.entities import *
import lib.controller
from lib.modules.module import Module

class Static_Analyzer (Module):
    def __init__(self, stop, crawler):
        super().__init__(['linkfinder'], stop)
        self.crawler = crawler

    def __searchKeys(self, element):
        # https://github.com/m4ll0k/SecretFinder pattern list + https://github.com/hahwul/dalfox greeping list
        patterns = {
            'rsa-key':                          r'-----BEGIN RSA PRIVATE KEY-----|-----END RSA PRIVATE KEY-----',
            'priv-key':                         r'-----BEGIN PRIVATE KEY-----|-----END PRIVATE KEY-----',
            'ssh_dsa_private_key' :             r'-----BEGIN DSA PRIVATE KEY-----',
            'ssh_dc_private_key' :              r'-----BEGIN EC PRIVATE KEY-----',
            'pgp_private_block' :               r'-----BEGIN PGP PRIVATE KEY BLOCK-----',
            'aws-s3':                           r's3\\.amazonaws.com[/]+|[a-zA-Z0-9_-]*\\.s3\\.amazonaws.com',
            'aws-appsync-graphql':              r'da2-[a-z0-9]{26}',
            'slack-webhook1':                   r'https://hooks.slack.com/services/T[a-zA-Z0-9_]{8}/B[a-zA-Z0-9_]{8}/[a-zA-Z0-9_]{24}',
            'slack-webhook2':                   r'https://hooks.slack.com/services/T[a-zA-Z0-9_]{8,10}/B[a-zA-Z0-9_]{8,10}/[a-zA-Z0-9_]{24}',
            'slack-token':                      r'(xox[p|b|o|a]-[0-9]{12}-[0-9]{12}-[0-9]{12}-[a-z0-9]{32})',
            'facebook-oauth':                   r"[f|F][a|A][c|C][e|E][b|B][o|O][o|O][k|K].{0,30}['\"\\s][0-9a-f]{32}['\"\\s]",
            'twitter-oauth':                    r"[t|T][w|W][i|I][t|T][t|T][e|E][r|R].{0,30}['\"\\s][0-9a-zA-Z]{35,44}['\"\\s]",
            'heroku-api':                       r'[h|H][e|E][r|R][o|O][k|K][u|U].{0,30}[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}',
            'mailgun-api':                      r'key-[0-9a-zA-Z]{32}',
            'mailchamp-api':                    r'[0-9a-f]{32}-us[0-9]{1,2}',
            'picatic-api':                      r'sk_live_[0-9a-z]{32}',
            'google-oauth':                     r'ya29\\.[0-9A-Za-z\\-_]+',
            'aws-access-key':                   r'AKIA[0-9A-Z]{16}',
            'amazon-mws-auth-token':            r'amzn\\.mws\\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            'facebook-access-token':            r'EAACEdEose0cBA[0-9A-Za-z]+',
            'github-access-token':              r'[a-zA-Z0-9_-]*:[a-zA-Z0-9_\\-]+@github\\.com*',
            'azure-storage':                    r'[a-zA-Z0-9_-]*\\.file.core.windows.net',
            'telegram-bot-api-key':             r'[0-9]+:AA[0-9A-Za-z\\-_]{33}',
            'square-access-token':              r'sq0atp-[0-9A-Za-z\\-_]{22}',
            'square-oauth-secret':              r'sq0csp-[0-9A-Za-z\\-_]{43}',
            'twilio-api-key':                   r'SK[0-9a-fA-F]{32}',
            'braintree-token':                  r'access_token\\$production\\$[0-9a-z]{16}\\$[0-9a-f]{32}',
            'stripe-api-key':                   r'sk_live_[0-9a-zA-Z]{24}',
            'stripe-restricted-key':            r'rk_live_[0-9a-zA-Z]{24}',
            'json_web_token' :                  r'ey[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$',
            'paypal_braintree_access_token' :   r'access_token\$production\$[0-9a-z]{16}\$[0-9a-f]{32}'
        }

        if isinstance(element, Script):
            script_locations = []
            for p in element.getPaths():
                script_locations.append(str(p))

            for response in element.getResponses():
                for request in response.getRequests():
                    script_locations.append(str(request.path))

            lib.controller.Controller.send_msg("Looking for API keys in script %d in %s" % (element.id, ",".join(script_locations)), "static-analyzer")
            text = element.content
        elif isinstance(element, Response):
            lib.controller.Controller.send_msg("Looking for API keys in response from %s" % ", ".join([str(r.path) for r in element.getRequests()]), "static-analyzer")
            text = element.body
        else:
            return

        for name, pattern in patterns.items():
            for value in re.findall(pattern, text):
                if isinstance(element, Script):
                    lib.controller.Controller.send_vuln_msg("KEYS FOUND: %s at script %d in %s\n%s" % (name, element.id, ",".join(script_locations), value), "static-analyzer")
                    Vulnerability.insert('Key Leak', name + ":" + value, ",".join(script_locations))

                elif isinstance(element, Response):
                    for r in element.getRequests():
                        paths += str(r.path) + ', '
                        Vulnerability.insert('Key Leak', name + ":" + value, str(r.path))
                    paths = paths[:-2]
                    lib.controller.Controller.send_vuln_msg("KEYS FOUND: %s at %s\n%s" % (name, paths, value), "static-analyzer")

    def __findLinks(self, script):
        command = [shutil.which('linkfinder'), '-i', script.filename, '-o', 'cli']

        script_locations = []
        for p in script.getPaths():
            script_locations.append(str(p))

        for response in script.getResponses():
            for request in response.getRequests():
                script_locations.append(str(request.path))

        lib.controller.Controller.send_msg("Looking for links in script %d in %s" % (script.id, ", ".join(script_locations)), "static-analyzer")

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        line = process.stdout.readline().decode('utf-8', errors='ignore')
        while line:
            try:
                for path in script_locations:
                    discovered = urljoin(path, line.rstrip())
                    if self.crawler.isCrawlable(discovered):
                        lib.controller.Controller.send_msg("PATH FOUND: Queued %s to crawler" % discovered, "static-analyzer")
                        self.crawler.addToQueue(discovered)
            except:
                pass
            finally:
                line = process.stdout.readline().decode('utf-8', errors='ignore')

    def __findVulns(self, script):
        pass

    def run(self):
        scripts = Script.yieldAll()
        responses = Response.yieldAll()
        while not self.stop.is_set():
            try:
                script = next(scripts)
                if script and script.content:
                    self.__findLinks(script)
                    self.__findVulns(script)

                    # Scripts embedded in html file are analyzed with the whole response body
                    if len(script.getPaths()) > 0:
                        self.__searchKeys(script)
                else:
                    response = next(responses)
                    if response and response.body and response.code == 200:
                        self.__searchKeys(response)
                    else:
                        time.sleep(5)
                        continue
            except:
                lib.controller.Controller.send_error_msg(utils.getExceptionString(), "static-analyzer")