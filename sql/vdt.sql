PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

DROP TABLE domains;
DROP TABLE paths;
DROP TABLE headers;
DROP TABLE responses;
DROP TABLE response_headers;

CREATE TABLE domains (
    name TEXT PRIMARY KEY NOT NULL
    );

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

COMMIT;
