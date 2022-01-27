import threading, time, re, logging

from lib.entities import *
import lib.bot

class Static_Analyzer (threading.Thread):
    def __init__(self, stop):
        threading.Thread.__init__(self)
        self.stop = stop

    @staticmethod
    def __searchKeys(text):
        result = []
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

        for name, pattern in patterns.items():
            for f in re.findall(pattern, text):
                result.append({'name': name, 'value': f})

        return result

    def run(self):
        try:
            scripts = Script.yieldAll()
            responses = Response.yieldAll()
            while not self.stop.is_set():
                script = next(scripts)
                if script and script.path and script.content:
                    for r in self.__searchKeys(script.content):
                        lib.bot.send_vuln_msg("KEYS FOUND: %s at script %s\n\n%s\n\n" % (r.get('name'), str(script.path), r.get('value')), "static analyzer")
                        Vulnerability.insert('Key Leak', r["name"] + ":" + r["f"], str(script.path))
                else:
                    response = next(responses)
                    if response and response.body:
                        for r in self.__searchKeys(response.body):
                            for r in response.getRequests():
                                paths += str(r.path) + ', '
                                Vulnerability.insert('Key Leak', r["name"] + ":" + r["f"], str(r.path))
                            paths = paths[:-2]
                            lib.bot.send_vuln_msg("KEYS FOUND: %s at %s\n\n%s\n\n" % (r["name"], paths, r["f"]), "static analyzer")
                    else:
                        time.sleep(5)
                        continue
        except Exception as e:
            lib.bot.send_error_msg("Exception occured", "static analyzer", e.message if hasattr(e, 'message') else e)