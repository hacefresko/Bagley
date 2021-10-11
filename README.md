# Bagley

<img src="/git%20resources/logo.png" width="350">

Bagley is a tool made for bug bounty enviroments to analize whole domains looking for vulnerabilities. It may be deployed as a bot in a server, where targets can be specified via the scope file

## Usage

In order to configure the database, create a new database and a new user both named bagley and execute:

    mysql -u bagley -p bagley < sql/bagley.sql
    
If you want to use another name for the database, it must be changed in database.py

File specifying the scope must be provided with parameter -S. It must contain one target per line, in JSON format. The application will iterate over the targets inside the scope file and will scan all of them one by one. Once it's done, it will wait for the user to write more targets into the file.

This way, the application can be launched as a daemon waiting for targets to be scanned.

Example of usage:

    python3 bagley.py -S scope.txt

Scope options:

*   domain \[required\]: Adds a domain or group of subdomains (i.e .example.com) to the scope. Only domains inside the scope will be scanned. If a group of subdomains is specified, the scan will start with the parent domain specified and all referenced subdomains inside the specified group will be scanned (i.e if .example.com is specified, scan will start with example.com and any path with a domain such as api.example.com will be scanned).

*   excluded: Explicitely specifies a list of domain to be out of scope. This way, a group of subdomains can be specified with some of its subdomains being out of scope. It's only valid when specifying a group of subdomains.

*   headers: Specifies the key and value of the headers that will be added to all requests when crawling the specified target.

*   cookies: Specifies the name, value and domain of the cookies that will be sent with every request to the target. '/' will be used as path, everything else will be None.

*   queue: Specifies URL to start crawling from. Domain must be already added.

### Example of scope file
    {"domain":".example.com", "excluded": ["test.example.com"]}
    {"domain":"api.example.com", "headers": {"Referer": "google.com", "Accept-Encoding": "gzip, deflate, br"}, "cookies": [{"name":"user_session", "value": "1234567890", "domain": "example.com"}, {"name": "logged_in", "value": "yes", "domain": ".example.com"}]}
    {"queue": "https://www.example.com/example?e=1337"}

## Available modules
*   Crawler: Crawler capable of rendering JavaScript and following redirects and dynamic requests to APIs, other domains... as long as they are inside the scope.

*   Discoverer: Search for subdomains with [subfinder](https://github.com/projectdiscovery/subfinder) and fuzzes subdomains and content inside the scope with [gobuster](https://github.com/OJ/gobuster). Sends discovered elements to the crawler.

*   Injector: Tests SQLi and XSS on GET and POST parameters. Wrapper for [sqlmap](https://github.com/sqlmapproject/sqlmap) and [DalFox](https://github.com/hahwul/dalfox)

## External requirements
#### All of these requirements must be available in one of the PATH directories so Bagley can call them wherever it's executed
*   [Mariadb](https://mariadb.com/)
*   [Chrome](https://www.google.com/chrome/)
*   [ChromeDriver](https://chromedriver.chromium.org/downloads)
*   [Gobuster](https://github.com/OJ/gobuster)
*   [Subfinder](https://github.com/projectdiscovery/subfinder)
*   [Sqlmap](https://github.com/sqlmapproject/sqlmap)
*   [DalFox](https://github.com/hahwul/dalfox)

## Useful documentation
*   [MDN HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP)
*   [Selenium](https://selenium-python.readthedocs.io/)
*   [Selenium Wire](https://github.com/wkeeling/selenium-wire)
