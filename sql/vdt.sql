PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

DROP TABLE domains;
DROP TABLE paths;
DROP TABLE headers;
DROP TABLE responses;
DROP TABLE response_headers;
DROP TABLE scripts;
DROP TABLE response_scripts;

CREATE TABLE domains (
    name TEXT PRIMARY KEY NOT NULL
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

CREATE TABLE headers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    value TEXT NOT NULL
);

CREATE TABLE responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path INTEGER NOT NULL,
    params TEXT,
    method TEXT NOT NULL,
    cookies TEXT,
    data TEXT,
    body TEXT NOT NULL,
    FOREIGN KEY (path) REFERENCES paths(id)
);

CREATE TABLE response_headers (
    response INTEGER NOT NULL,
    header INTEGER NOT NULL,
    FOREIGN KEY (response) REFERENCES responses(id),
    FOREIGN KEY (header) REFERENCES headers(id)
);

-- id is script hash (since some scripts does not have any identifier such as url, we need a way of identifying them)
CREATE TABLE scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT UNIQUE NOT NULL,
    url TEXT,
    content TEXT NOT NULL
);

CREATE TABLE response_scripts (
    response INTEGER NOT NULL,
    script TEXT NOT NULL,
    FOREIGN KEY (response) REFERENCES responses(id),
    FOREIGN KEY (script) REFERENCES scripts(id)
);

COMMIT;
