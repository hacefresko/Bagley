# Bagley

<img src="/git%20resources/logo.png" width="350">

Bagley is a tool made for bug bounty environments to automate the finding of vulnerabilities in web applications

## Deployment

* Clone this repository
* Configure discord connection in docker-compose.yml
* Run `docker-compose up`

## Available commands:

    help           Print this message
    start          Start execution
    stop           Stop execution
    restart        Restart execution
    add            Add a new domain (add help for more info)
    rm             Removes a domain
    getDomains     Print all domains
    getPaths       Print all paths for a domain
    getScript      Get script information
    getTechnology  Get technolofy information
    query          Query directly to database
    getRPS         Print current requests per second
    setRPS         Set requests per second
    getActive      Print active modules

## Available modules

Each modules runs in a different thread

*   Crawler: Crawls all resources rendering JavaScript (including dynamic requests made to APIs, other domains inside the scope, etc.).

*   Finder: Looks for resources and subdomains in the server and sends discovered assets to the crawler:

    *   Searches for subdomains with [Subfinder](https://github.com/projectdiscovery/subfinder) and paths with [Gau](https://github.com/lc/gau)
    
    *   Fuzzes subdomains and resources with [Gobuster](https://github.com/OJ/gobuster) and wordlists from [SecLists](https://github.com/danielmiessler/SecLists)

*   Injector: Tests different injection vectors:

    *   SQLi with [Sqlmap](https://github.com/sqlmapproject/sqlmap)

    *   XSS with [DalFox](https://github.com/hahwul/dalfox)

*   Static Analyzer: Performs local analysis among obtained data, without generating network traffic:

    *   Searches for API keys with a pattern list mainly obtained from [dora](https://github.com/sdushantha/dora)

    *   Searches for links inside the scope with [linkfinder](https://github.com/GerbenJavado/LinkFinder)

    *   Looks for vulnerabilities with static analysis with [CodeQL](https://codeql.github.com/)

*   Dynamic Analyzer: Performs lightweighted analysis among discovered assets, generating network traffic:

    *   Gets technologies used by the application with [Wappalyzer](https://github.com/AliasIO/wappalyzer)

    *   Check know vulnerabilities of technologies used in the [NVD](https://nvd.nist.gov/) via its [API](https://nvd.nist.gov/developers/products)

    *   Subdomain Takeover with [Subjack](https://github.com/haccer/subjack)

    *   Tries to bypass 403 responses by tampering headers


## External dependencies

*   [Mariadb](https://mariadb.com/)
*   [Chrome](https://www.google.com/chrome/)
*   [ChromeDriver](https://chromedriver.chromium.org/downloads)
*   [Gobuster](https://github.com/OJ/gobuster)
*   [Subfinder](https://github.com/projectdiscovery/subfinder)
*   [SecLists](https://github.com/danielmiessler/SecLists)
*   [Sqlmap](https://github.com/sqlmapproject/sqlmap)
*   [DalFox](https://github.com/hahwul/dalfox)
*   [CRLFuzz](https://github.com/dwisiswant0/crlfuzz)
*   [Tplmap](https://github.com/epinna/tplmap)
*   [Wappalyzer](https://github.com/AliasIO/wappalyzer)
*   [Subjack](https://github.com/haccer/subjack)
*   [Gau](https://github.com/lc/gau)
*   [linkfinder](https://github.com/GerbenJavado/LinkFinder)
*   [CodeQL](https://codeql.github.com/)

## Useful documentation

*   [MDN HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP)
*   [Selenium](https://selenium-python.readthedocs.io/)
*   [Selenium Wire](https://github.com/wkeeling/selenium-wire)
*   [Discord API](https://discordpy.readthedocs.io/en/latest/api.html)
*   [CodeQL docs](https://codeql.github.com/docs/)
