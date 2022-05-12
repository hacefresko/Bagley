import time, re, rure, shutil, subprocess, requests, os, shutil, random, string, jsbeautifier, traceback
from urllib.parse import urljoin

from lib.entities import *
from lib.modules.module import Module

class Static_Analyzer (Module):
    def __init__(self, controller, stop, crawler):
        super().__init__(['linkfinder', 'unwebpack_sourcemap', 'codeql'], controller, stop, submodules=["searchKeys", "linkfinder", "codeql"])
        self.crawler = crawler

    def _searchKeys(self, element):
        # Taken from https://github.com/sdushantha/dora/blob/main/dora/db/data.json
        patterns = {
            #"Google API Key": "AIza[0-9A-Za-z-_]{35}",
            "Mailgun Private Key": "key-[0-9a-zA-Z]{32}",
            "Heroku API key": "[h|H][e|E][r|R][o|O][k|K][u|U].{0,30}[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}",
            "Slack API token": "(xox[p|b|o|a]-[0-9]{12}-[0-9]{12}-[0-9]{12}-[a-z0-9]{32})",
            "Slack Webhook": "https://hooks.slack.com/services/T[a-zA-Z0-9_]{8}/B[a-zA-Z0-9_]{8}/[a-zA-Z0-9_]{24}",
            "MailChimp API Key": "[0-9a-f]{32}-us[0-9]{1,2}",
            "Facebook Access Token": "EAACEdEose0cBA[0-9A-Za-z]+",
            "Facebook Secret Key": "(?i)(facebook|fb)(.{1,20})?(?-i)['\"][0-9a-f]{32}['\"]",
            "Twitter Secret Key": "(?i)twitter(.{1,20})?['\"][0-9a-z]{35,44}['\"]",
            "Github Personal Access Token": "ghp_[0-9a-zA-Z]{36}",
            "Github OAuth Access Token": "gho_[0-9a-zA-Z]{36}",
            "Github App Token": "(ghu|ghs)_[0-9a-zA-Z]{36}",
            "Github Refresh Token": "ghr_[0-9a-zA-Z]{76}",
            "LinkedIn Secret Key": "(?i)linkedin(.{0,20})?[0-9a-z]{16}",
            "Stripe Restricted API Token": "rk_live_[0-9a-zA-Z]{24}",
            "Stripe Standard API Token": "sk_live_[0-9a-zA-Z]{24}",
            "Square Access Token": "sqOatp-[0-9A-Za-z\\-_]{22}",
            "Square OAuth Secret": "sq0csp-[ 0-9A-Za-z\\-_]{43}",
            "PayPal/Braintree Access Token": "access_token\\$production\\$[0-9a-z]{16}\\$[0-9a-f]{32}",
            "Amazon MWS Auth Token": "amzn\\.mws\\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "Picatic API Key": "sk_[live|test]_[0-9a-z]{32}",
            "Google OAuth Access Key": "ya29\\.[0-9A-Za-z\\-_]+",
            "StackHawk API Key": "hawk\\.[0-9A-Za-z\\-_]{20}\\.[0-9A-Za-z\\-_]{20}",
            "NuGet API Key": "oy2[a-z0-9]{43}",
            "SendGrid Token": "SG\\.[0-9A-Za-z\\-_]{22}\\.[0-9A-Za-z-_]{43}",
            "AWS Access Key": "(A3T[A-Z0-9]|AKIA|AGPA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
            "AWS Secret Key": "(?i)aws(.{0,20})?(?-i)['\"][0-9a-zA-Z/+]{40}['\"]",
            "Google Cloud Platform API Key": "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            "Zoho Webhook Token": "https://creator\\.zoho\\.com/api/[A-Za-z0-9/\\-_\\.]+\\?authtoken=[A-Za-z0-9]+",
            "Zapier Webhook": "https://(?:www.)?hooks\\.zapier\\.com/hooks/catch/[A-Za-z0-9]+/[A-Za-z0-9]+/",
            "New Relic Admin API Key": "NRAA-[a-f0-9]{27}",
            "New Relic Insights Key": "NRI(?:I|Q)-[A-Za-z0-9\\-_]{32}",
            "New Relic REST API Key": "NRRA-[a-f0-9]{42}",
            "New Relic Synthetics Location Key": "NRSP-[a-z]{2}[0-9]{2}[a-f0-9]{31}",
            "Microsoft Teams Webhook": "https://outlook\\.office\\.com/webhook/[A-Za-z0-9\\-@]+/IncomingWebhook/[A-Za-z0-9\\-]+/[A-Za-z0-9\\-]+",
            "Google FCM Server Key": "AAAA[a-zA-Z0-9_-]{7}:[a-zA-Z0-9_-]{140}",
            "Google Calendar URI": "https://www\\.google\\.com/calendar/embed\\?src=[A-Za-z0-9%@&;=\\-_\\./]+",
            "Discord Webhook": "https://discordapp\\.com/api/webhooks/[0-9]+/[A-Za-z0-9-_]+",
            "Cloudinary Credentials": "cloudinary://[0-9]+:[A-Za-z0-9-_.]+@[A-Za-z0-9-_.]+",
            "Bitly Secret Key": "R_[0-9a-f]{32}",
            "Amazon SNS Topic": "arn:aws:sns:[a-z0-9-]+:[0-9]+:[A-Za-z0-9-_]+",
            "PyPI Upload Token": "pypi-AgEIcHlwaS5vcmc[A-Za-z0-9-_]{50,1000}",
            "Shopify Private App Access Token": "shppa_[a-fA-F0-9]{32}",
            "Shopify Custom App Access Token": "shpca_[a-fA-F0-9]{32}",
            "Shopify Access Token": "shpat_[a-fA-F0-9]{32}",
            "Shopify Shared Secret": "shpss_[a-fA-F0-9]{32}",
            "Dynatrace Token": "dt0[a-zA-Z]{1}[0-9]{2}\\.[A-Z0-9]{24}\\.[A-Z0-9]{64}",
            "Twilio API Key": "(?i)twilio(.{0,20})?SK[0-9a-f]{32}",
            "MongoDB Cloud Connection String": "mongodb\\+srv://(.*)",
            "Riot Games Developer API Key": "RGAPI-[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}"
        }

        if isinstance(element, Script):
            script_locations = []
            for p in element.getPaths():
                script_locations.append(str(p))

            for response in element.getResponses():
                for request in response.getRequests():
                    script_locations.append(str(request.path))

            paths = ",".join(script_locations)

            self.send_msg("Looking for API keys in script %d in %s" % (element.id, paths), "static-analyzer")
            text = element.content
        elif isinstance(element, Response):
            paths = ", ".join([str(r.path) for r in element.getRequests()])
            self.send_msg("Looking for API keys in response from %s" % paths, "static-analyzer")
            text = element.body
        else:
            return

        for name, pattern in patterns.items():
            result = rure.search(pattern, text)
            if result is not None:
                value = result.group()
                if isinstance(element, Script):
                    self.send_vuln_msg("KEYS FOUND: %s at script %d in %s\n\n%s" % (name, element.id, paths, value), "static-analyzer")
                    Vulnerability.insert('Key Leak', name + ": " + value, paths)

                elif isinstance(element, Response):
                    self.send_vuln_msg("KEYS FOUND: %s at %s\n%s" % (name, paths, value), "static-analyzer")

    def __findPaths(self, script):
        command = [shutil.which('linkfinder'), '-i', script.file, '-o', 'cli']

        script_locations = []
        for response in script.getResponses():
            for request in response.getRequests():
                script_locations.append(str(request.path))

        self.send_msg("Looking for paths in script %d" % (script.id), "static-analyzer")

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        line = process.stdout.readline().decode('utf-8', errors='ignore')
        while line:
            try:
                for path in script_locations:
                    discovered = urljoin(path, line.rstrip())
                    if self.crawler.isQueueable(discovered):
                        code = requests.get(discovered, verify=False, allow_redirects=False).status_code
                        if (code != 404) and (code != 400) and (code != 500):
                            self.send_msg("PATH FOUND: Queued %s to crawler" % discovered, "static-analyzer")
                            self.crawler.addToQueue(discovered)
            except:
                pass
            finally:
                line = process.stdout.readline().decode('utf-8', errors='ignore')

        self.send_msg(process.stderr.read().decode('utf-8', errors='ignore'), "static-analyzer")

    def __analyzeCodeQL(self, script):

        tmp_dir = config.FILES_FOLDER + ''.join(random.choices(string.ascii_lowercase, k=10)) + '/'
        os.mkdir(tmp_dir)

        script_locations = []
        for p in script.getPaths():
            script_locations.append(str(p))

        for response in script.getResponses():
            for request in response.getRequests():
                script_locations.append(str(request.path))
        script_locations_str = ", ".join(script_locations)

        # Check if there is a source map available
        sourcemap_url = None
        last_line = script.content.rstrip().split("\n")[-1]
        regex = "\\/\\/#\s*sourceMappingURL=(.*)$"
        matches = re.search(regex, last_line)
        if matches:
            sourcemap = matches.groups(0)[0].strip()
            for path in script.getPaths():
                sourcemap_url = urljoin(str(path), sourcemap)
                ok = requests.get(sourcemap_url, verify=False).ok
                if ok:
                    break
        
        if sourcemap_url is not None:
            # Unpack webpack bundle
            self.send_msg("Found source map for script %d in %s" % (script.id, script_locations_str), "static-analyzer")

            script_dir = config.SCRIPTS_FOLDER + str(script.id) + '/'
            os.mkdir(script_dir)
            command = [shutil.which('unwebpack_sourcemap'), '--disable-ssl-verification', sourcemap_url, script_dir]
            result = subprocess.run(command, capture_output=True, encoding='utf-8')
            if result.returncode != 0:
                self.send_error_msg(result.stderr, "static-analyzer")
                shutil.rmtree(tmp_dir)
                return

            self.send_msg("Succesfully unpacked script %d in %s" % (script.id, script_locations_str), "static-analyzer")

            shutil.copytree(script_dir, tmp_dir + str(script.id))

        else:
            # Just beautify
            result = jsbeautifier.beautify_file(script.file)
            f = open(script.file, "w")
            f.write(result)
            f.close()
            
            shutil.copy(script.file, tmp_dir)

        self.send_msg("Analyzing script %d in %s" % (script.id, script_locations_str), "static-analyzer")

        # Create codeql database
        codeql_db = config.FILES_FOLDER + 'codeql'
        command = [shutil.which('codeql'), 'database', 'create', codeql_db, '--overwrite', '--language=javascript', "--source-root="+tmp_dir]
        result = subprocess.run(command, capture_output=True, encoding='utf-8')
        if result.returncode != 0:
            shutil.rmtree(tmp_dir)
            return

        # Analyze codeql database
        output_file = tmp_dir + 'codeql_results.csv'
        cache_dir = config.FILES_FOLDER + 'codeql_cache'
        command = [shutil.which('codeql'), 'database', 'analyze', codeql_db, config.CODEQL_SUITE, '--format=csv', '--output='+output_file, '--compilation-cache='+cache_dir]
        result = subprocess.run(command, capture_output=True, encoding='utf-8')
        if (result.returncode != 0) or (not os.path.isfile(output_file)):
            shutil.rmtree(tmp_dir)
            return

        # Read results
        fd = open(output_file)
        for line in fd.readlines():
            self.send_vuln_msg("VULN FOUND at script %d in %s:\n\n%s" % (script.id, script_locations_str, line), "static-analyzer")
            Vulnerability.insert('JS Vulnerability', line, "script %d in %s" % (script.id, script_locations_str))
        fd.close()

        shutil.rmtree(tmp_dir)

    def run(self):
        scripts = Script.yieldAll()
        responses = Response.yieldAll()
        while not self.stop.is_set():
            try:
                script = next(scripts)
                if script and script.content:
                    self.__findPaths(script)
                    self.__analyzeCodeQL(script)

                    # Scripts embedded in html file are analyzed with the whole response body
                    if len(script.getPaths()) > 0:
                        self._searchKeys(script)
                else:
                    response = next(responses)
                    if response and response.body and response.code == 200:
                        self._searchKeys(response)
                    else:
                        time.sleep(5)
                        continue
            except:
                self.send_error_msg(traceback.format_exc(), "static-analyzer")