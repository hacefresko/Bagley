# Bagley


![logo](/git%20resources/logo.png)

## Usage

In order to create the database, execute:

    sqlite3 bagley.db < sql/bagley.db
    
If you want to use another name for the database, it must be changed in database.py

File specifying targets must be provided with parameter -T. It must contain one target per line, in JSON format. The application will iterate over the targets inside the file and will scan all of them one by one. Once it's done, it will wait for the user to write more targets in the file.

This way, the application can be launched as a daemon waiting for targets to be scanned.

Target options:
*   domain \[required\]: Adds a domain or group of subdomains (i.e .example.com) to the scope. Only domains inside the scope will be scanned. If a group of subdomains is specified, the scan will start with the parent domain specified and all referenced subdomains inside the specified group will be scanned (i.e if .example.com is specified, scan will start with example.com and any path with a domain such as api.example.com will be scanned).

*   excluded: Explicitely specifies a list of domain to be out of scope. This way, a group of subdomains can be specified with some of its subdomains being out of scope. It's only valid when specifying a group of subdomains.

*   headers: Specifies the key and value of the headers that will be added to all requests when crawling the specified target.

*   cookies: Specifies the name, value and domain of the cookies that will be sent with every request to the target. '/' will be used as path, everything else will be None.

### Example of targets file
    {"domain":".example.com", "excluded": ["www.example.com", "test.example.com"]}
    {"domain":"api.example.com", "headers": {"Referer": "google.com", "Accept-Encoding": "gzip, deflate, br"}, "cookies": [{"name":"user_session", "value": "1234567890", "domain": "example.com"}, {"name": "logged_in", "value": "yes", "domain": ".example.com"}]}

## Available modules
*   Crawler: Crawler capable of following redirects, rendering JavaScript and logging dynamic requests
*   Sqlmap: Wrapper for [sqlmap](https://github.com/sqlmapproject/sqlmap)

## External requirements
*   [Sqlmap](https://github.com/sqlmapproject/sqlmap)
*   Chrome
*   ChromeDriver

## Useful documentation
*   [MDN HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP)
*   [Selenium Wire](https://github.com/wkeeling/selenium-wire)
