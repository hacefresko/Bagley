# Web Vulnerability Detection Tool

## Usage

File specifying targets must be provided with parameter -T. It must contain one target per line, in JSON format. The application will iterate over the targets inside the file and will scan all of them one by one. Once it's done, it will wait for the user to write more targets in the file.

This way, the application can be launched as a daemon waiting for targets to be scanned.

Target options:
*   domain \[required\]: Specifies the domain or group of subdomains (i.e .example.com) that will be added to the scope. All domains inside the scope will be scanned. If a path with a domain which is out of the scope is referenced, it will be ignored and won't be scanned. If a group of subdomains is specified, the scan will start with the parent domain specified and all referenced subdomains inside the specified group will be scanned (i.e if .example.com is specified, scan will start with example.com and any path with a domain such as api.example.com will be scanned)
* headers: Specifies the key and value of the headers that will be added to all requests when crawling the specified target.

### Example of targets file
    {"domain":"api.example.com", "headers": {"Referer": "google.com", "Accept-Encoding": "gzip, deflate, br"}}
    {"domain":".example.com"}

## Available modules
*   Crawler
*   Sqlmap

## External requirements
*   Sqlmap
*   Chrome
*   ChromeDriver

## Useful documentation
*   [MDN HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP)
*   [Selenium Wire](https://github.com/wkeeling/selenium-wire)
