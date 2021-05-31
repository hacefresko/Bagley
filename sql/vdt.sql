PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

DROP TABLE domains;
DROP TABLE paths;
DROP TABLE requests;
DROP TABLE responses;
DROP TABLE headers;
DROP TABLE scripts;
DROP TABLE request_headers;
DROP TABLE response_headers;
DROP TABLE response_scripts;

CREATE TABLE domains (
    name TEXT PRIMARY KEY
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
    content TEXT NOT NULL,
    cookies TEXT NOT NULL
);

CREATE TABLE headers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    value TEXT NOT NULL
);

CREATE TABLE scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    content TEXT NOT NULL
);

CREATE TABLE request_headers (
    request INTEGER NOT NULL,
    header INTEGER NOT NULL,
    FOREIGN KEY (request) REFERENCES requests(id),
    FOREIGN KEY (header) REFERENCES headers(id)
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
