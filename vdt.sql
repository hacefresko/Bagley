PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

CREATE TABLE domains (
    name TEXT PRIMARY KEY NOT NULL
    );

CREATE TABLE paths (
    element TEXT NOT NULL, 
    parent TEXT DEFAULT NULL, 
    domain TEXT NOT NULL, 
    PRIMARY KEY (element, parent, domain), 
    FOREIGN KEY (domain) REFERENCES domains(name), 
    FOREIGN KEY (parent) REFERENCES paths(name)
    );

COMMIT;
