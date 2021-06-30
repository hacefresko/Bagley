PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

DROP TABLE domains;
DROP TABLE out_of_scope;
DROP TABLE paths;
DROP TABLE requests;
DROP TABLE responses;
DROP TABLE headers;
DROP TABLE cookies;
DROP TABLE scripts;
DROP TABLE request_headers;
DROP TABLE request_cookies;
DROP TABLE response_headers;
DROP TABLE response_cookies;
DROP TABLE response_scripts;

CREATE TABLE domains (
    name TEXT PRIMARY KEY
);

CREATE TABLE out_of_scope (
    name TEXT PRIMARY KEY
);

-- Element 0 means it's empty. Parent 0 means it's the first element, so first will be (domain, 0, 0)
CREATE TABLE paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    element TEXT NOT NULL, 
    parent INTEGER NOT NULL, 
    domain TEXT NOT NULL,
    FOREIGN KEY (domain) REFERENCES domains(name), 
    FOREIGN KEY (parent) REFERENCES paths(id)
);



CREATE TABLE requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol TEXT NOT NULL,
    path INTEGER NOT NULL,
    params TEXT NOT NULL,
    method TEXT NOT NULL,
    data TEXT NOT NULL,
    response TEXT,
    FOREIGN KEY (path) REFERENCES paths(id)
    FOREIGN KEY (response) REFERENCES responses(hash)
);

CREATE TABLE responses (
    hash TEXT PRIMARY KEY,
    code INTEGER NOT NULL,
    content TEXT
);



CREATE TABLE headers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    value TEXT NOT NULL
);

CREATE TABLE cookies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    hash TEXT PRIMARY KEY,
    path INTEGER NOT NULL,
    content TEXT NOT NULL,
    FOREIGN KEY (path) REFERENCES paths(id)
);



CREATE TABLE request_headers (
    request INTEGER NOT NULL,
    header INTEGER NOT NULL,
    FOREIGN KEY (request) REFERENCES requests(id),
    FOREIGN KEY (header) REFERENCES headers(id)
);

CREATE TABLE request_cookies (
    request INTEGER NOT NULL,
    cookie INTEGER NOT NULL,
    FOREIGN KEY (request) REFERENCES requests(id),
    FOREIGN KEY (cookie) REFERENCES cookies(id)
);



CREATE TABLE response_headers (
    response TEXT NOT NULL,
    header INTEGER NOT NULL,
    FOREIGN KEY (response) REFERENCES responses(hash),
    FOREIGN KEY (header) REFERENCES headers(id)
);

-- Cookies sent by response in Set-Cookie headers
CREATE TABLE response_cookies (
    response TEXT NOT NULL,
    cookie INTEGER NOT NULL,
    FOREIGN KEY (response) REFERENCES responses(hash),
    FOREIGN KEY (cookie) REFERENCES cookies(id)
);

CREATE TABLE response_scripts (
    response TEXT NOT NULL,
    script TEXT NOT NULL,
    FOREIGN KEY (response) REFERENCES responses(hash),
    FOREIGN KEY (script) REFERENCES scripts(hash)
);

COMMIT;