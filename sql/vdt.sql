PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

DROP TABLE domains;
DROP TABLE paths;
DROP TABLE responses;
DROP TABLE bodies;
DROP TABLE headers;
DROP TABLE scripts;
DROP TABLE response_bodies;
DROP TABLE response_headers;
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

CREATE TABLE responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path INTEGER NOT NULL,
    params TEXT,
    method TEXT NOT NULL,
    cookies TEXT,
    data TEXT,
    FOREIGN KEY (path) REFERENCES paths(id)
);

CREATE TABLE bodies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL
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

CREATE TABLE response_bodies (
    response INTEGER NOT NULL,
    body INTEGER NOT NULL,
    FOREIGN KEY (response) REFERENCES responses(id),
    FOREIGN KEY (body) REFERENCES bodies(id)
);

CREATE TABLE response_headers (
    response INTEGER NOT NULL,
    header INTEGER NOT NULL,
    FOREIGN KEY (response) REFERENCES responses(id),
    FOREIGN KEY (header) REFERENCES headers(id)
);

CREATE TABLE response_scripts (
    response INTEGER NOT NULL,
    script INTEGER NOT NULL,
    FOREIGN KEY (response) REFERENCES responses(id),
    FOREIGN KEY (script) REFERENCES scripts(id)
);

COMMIT;
