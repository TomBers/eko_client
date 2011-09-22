import sqlite3

def get_files_for_sync(limit = 5):
    conn = sqlite3.connect('/tmp/sqlitedb.test')