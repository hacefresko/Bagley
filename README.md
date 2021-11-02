# Bagley

<img src="/git%20resources/logo.png" width="350">

Bagley is a tool made for bug bounty enviroments to analize whole domains looking for vulnerabilities. It may be deployed as a bot in a server, where targets can be specified via the scope file

## Usage

File config.py defines some global variables that you may have to change, such as path for the directory fuzzing wordlist or the DNS fuzzing wordlist

File specifying the scope must be provided with parameter -S. It must contain one target per line, in JSON format. The application will iterate over the targets inside the scope file and will scan all of them one by one. Once it's done, it will wait for the user to write more targets into the file.

This way, the application can be launched as a daemon waiting for targets to be scanned.

Example of usage:

    python3 bagley.py -S scope.txt

Scope options:

*   domain \[required\]: Adds a domain or group of subdomains (i.e .example.com) to the scope. Only domains inside the scope will be scanned. If a group of subdomains is specified, the scan will start with the parent domain specified and all referenced subdomains inside the specified group will be scanned (i.e if .example.com is specified, scan will start with example.com and any path with a domain such as api.example.com will be scanned).

*   excluded: Explicitely specifies a list of domain to be out of scope. This way, a group of subdomains can be specified with some of its subdomains being out of scope. It's only valid when specifying a group of subdomains.

*   headers: Specifies the key and value of the headers that will be added to all requests when crawling the specified target.

*   cookies: Specifies the name, value and domain of the cookies that will be sent with every request to the target. '/' will be used as path, everything else will be None.

*   queue: Specifies list of URLs to start crawling from. Domain must be already added.

### Example of scope file

    {"domain":".example.com", "excluded": ["test.example.com"], "queue": ["https://www.example.com/example?e=1337"]}
    {"domain":"api.example.com", "headers": {"Referer": "google.com", "Accept-Encoding": "gzip, deflate, br"}, "cookies": [{"name":"user_session", "value": "1234567890", "domain": "example.com"}, {"name": "logged_in", "value": "yes", "domain": ".example.com"}]}

## Available modules

*   Crawler: Crawls all resources rendering JavaScript (including dynamic requests made to APIs, other domains inside the scope, etc.).

*   Discoverer: Searches for subdomains with [Subfinder](https://github.com/projectdiscovery/subfinder) and fuzzes subdomains and resources with [Gobuster](https://github.com/OJ/gobuster). When a subdomain is found, it checks if it's vulnerable to Subdomain Takeover with [Subjack](https://github.com/haccer/subjack). Every discover asset is sent to the crawler.

*   Injector: Tests SQLi with [Sqlmap](https://github.com/sqlmapproject/sqlmap), XSS with [DalFox](https://github.com/hahwul/dalfox), CRLFi with [CRLFuzz](https://github.com/dwisiswant0/crlfuzz) and SSTI with [Tplmap](https://github.com/epinna/tplmap) on GET and POST parameters.

*   Searcher: Gets the technologies used by the application with [Wappalyzer](https://github.com/AliasIO/wappalyzer)

## External requirements
#### All of these requirements must be available in one of the PATH directories so Bagley can call them wherever it's executed
*   [Mariadb](https://mariadb.com/)
*   [Chrome](https://www.google.com/chrome/)
*   [ChromeDriver](https://chromedriver.chromium.org/downloads)
*   [Gobuster](https://github.com/OJ/gobuster)
*   [Subfinder](https://github.com/projectdiscovery/subfinder)
*   [Subjack](https://github.com/haccer/subjack)
*   [Sqlmap](https://github.com/sqlmapproject/sqlmap)
*   [DalFox](https://github.com/hahwul/dalfox)
*   [CRLFuzz](https://github.com/dwisiswant0/crlfuzz)
*   [Tplmap](https://github.com/epinna/tplmap)
*   [Wappalyzer](https://github.com/AliasIO/wappalyzer)

## Useful documentation
*   [MDN HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP)
*   [Selenium](https://selenium-python.readthedocs.io/)
*   [Selenium Wire](https://github.com/wkeeling/selenium-wire)
