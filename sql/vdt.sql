PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

DROP TABLE domains;
DROP TABLE paths;
DROP TABLE requests;
DROP TABLE responses;
DROP TABLE headers;
DROP TABLE scripts;
DROP TABLE response_headers;
DROP TABLE response_scripts;

CREATE TABLE domains (
    protocol TEXT NOT NULL,
    name TEXT NOT NULL,
    PRIMARY KEY (protocol, name)
);

-- path 0 means it's the domain
CREATE TABLE paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    element TEXT NOT NULL, 
    parent INTEGER, 
    domain TEXT NOT NULL,
    FOREIGN KEY (domain) REFERENCES domains(name), 
    FOREIGN KEY (parent) REFERENCES paths(id)
);

CREATE TABLE requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path INTEGER NOT NULL,
    params TEXT,
    method TEXT NOT NULL,
    data TEXT,
    response TEXT,
    FOREIGN KEY (path) REFERENCES paths(id)
    FOREIGN KEY (response) REFERENCES responses(hash)
);

CREATE TABLE responses (
    hash TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    cookies TEXT,
    FOREIGN KEY (request) REFERENCES requests(id)
);

CREATE TABLE headers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    value TEXT NOT NULL
);

CREATE TABLE scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT UNIQUE NOT NULL,
    url TEXT,
    content TEXT NOT NULL
);

CREATE TABLE response_headers (
    response TEXT NOT NULL,
    header INTEGER NOT NULL,
    FOREIGN KEY (response) REFERENCES responses(hash),
    FOREIGN KEY (header) REFERENCES headers(id)
);

CREATE TABLE response_scripts (
    response TEXT NOT NULL,
    script INTEGER NOT NULL,
    FOREIGN KEY (response) REFERENCES responses(hash),
    FOREIGN KEY (script) REFERENCES scripts(id)
);

COMMIT;
