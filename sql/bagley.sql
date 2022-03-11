SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS domains;
DROP TABLE IF EXISTS out_of_scope;
DROP TABLE IF EXISTS paths;
DROP TABLE IF EXISTS requests;
DROP TABLE IF EXISTS responses;
DROP TABLE IF EXISTS headers;
DROP TABLE IF EXISTS cookies;
DROP TABLE IF EXISTS scripts;
DROP TABLE IF EXISTS domain_headers;
DROP TABLE IF EXISTS request_headers;
DROP TABLE IF EXISTS request_cookies;
DROP TABLE IF EXISTS response_headers;
DROP TABLE IF EXISTS response_cookies;
DROP TABLE IF EXISTS response_scripts;
DROP TABLE IF EXISTS vulnerabilities;
DROP TABLE IF EXISTS technologies;
DROP TABLE IF EXISTS path_technologies;
DROP TABLE IF EXISTS cves;

CREATE TABLE domains (
    id INT PRIMARY KEY AUTO_INCREMENT, 
    name TEXT
);

CREATE TABLE out_of_scope (
    name VARCHAR(255) PRIMARY KEY
);

-- Element 0 means it's empty. Parent 0 means it's the first element, so first will be (domain, 0, 0)
CREATE TABLE paths (
    id INT PRIMARY KEY AUTO_INCREMENT,
    protocol TEXT NOT NULL,
    element TEXT, 
    parent INT, 
    domain INT NOT NULL,
    FOREIGN KEY (domain) REFERENCES domains(id), 
    FOREIGN KEY (parent) REFERENCES paths(id)
);

CREATE TABLE responses (
    id INT UNIQUE KEY AUTO_INCREMENT,
    hash VARCHAR(255) PRIMARY KEY,
    code INT NOT NULL,
    content LONGTEXT
);

CREATE TABLE requests (
    id INT PRIMARY KEY AUTO_INCREMENT,
    path INT NOT NULL,
    params TEXT,
    method TEXT NOT NULL,
    data TEXT,
    response VARCHAR(255),
    FOREIGN KEY (path) REFERENCES paths(id),
    FOREIGN KEY (response) REFERENCES responses(hash)
);

CREATE TABLE headers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    header_key TEXT NOT NULL,
    value TEXT
);

CREATE TABLE cookies (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name TEXT NOT NULL,
    value TEXT,
    domain TEXT,
    path TEXT,      -- Neither path nor domain are foreign keys since domain can specify a range of subdomains
    expires TEXT,
    maxage TEXT,
    httponly BOOL,
    secure BOOL,
    samesite TEXT
);

CREATE TABLE scripts (
    id INT UNIQUE KEY AUTO_INCREMENT,
    hash VARCHAR(255) PRIMARY KEY,
    content LONGTEXT,
    path INT,
    FOREIGN KEY (path) REFERENCES paths(id)
);

-- Headers sent in all request made to that domain
CREATE TABLE domain_headers (
    domain INT NOT NULL,
    header INT NOT NULL,
    FOREIGN KEY (domain) REFERENCES domains(id),
    FOREIGN KEY (header) REFERENCES headers(id)
);

CREATE TABLE request_headers (
    request INT NOT NULL,
    header INT NOT NULL,
    FOREIGN KEY (request) REFERENCES requests(id),
    FOREIGN KEY (header) REFERENCES headers(id)
);

CREATE TABLE request_cookies (
    request INT NOT NULL,
    cookie INT NOT NULL,
    FOREIGN KEY (request) REFERENCES requests(id),
    FOREIGN KEY (cookie) REFERENCES cookies(id)
);

CREATE TABLE response_headers (
    response VARCHAR(255) NOT NULL,
    header INT NOT NULL,
    FOREIGN KEY (response) REFERENCES responses(hash),
    FOREIGN KEY (header) REFERENCES headers(id)
);

-- Cookies sent by response in Set-Cookie headers
CREATE TABLE response_cookies (
    response VARCHAR(255) NOT NULL,
    cookie INT NOT NULL,
    FOREIGN KEY (response) REFERENCES responses(hash),
    FOREIGN KEY (cookie) REFERENCES cookies(id)
);

CREATE TABLE response_scripts (
    response VARCHAR(255) NOT NULL,
    script VARCHAR(255) NOT NULL,
    FOREIGN KEY (response) REFERENCES responses(hash),
    FOREIGN KEY (script) REFERENCES scripts(hash)
);

CREATE TABLE vulnerabilities (
    id INT PRIMARY KEY AUTO_INCREMENT,
    type TEXT,
    description TEXT,
    element TEXT,
    command TEXT
);

CREATE TABLE technologies (
    id INT PRIMARY KEY AUTO_INCREMENT,
    cpe TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT
);

CREATE TABLE path_technologies (
    path INT NOT NULL,
    tech INT NOT NULL,
    FOREIGN KEY (path) REFERENCES paths(id),
    FOREIGN KEY (tech) REFERENCES technologies(id)
);

CREATE TABLE cves (
    id VARCHAR(50) PRIMARY KEY,
    tech INT NOT NULL,
    FOREIGN KEY (tech) REFERENCES technologies(id)
);