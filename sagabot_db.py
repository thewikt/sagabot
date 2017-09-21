import sqlite3
from sqlite3 import Error

def dbconnect():
    try:
        conn = sqlite3.connect("sagabot.db")
        return conn
    except Error as e:
        print(e)
    return None

def selectbyname(conn, name):
    sql = "SELECT * FROM profiles WHERE mal_name = ?"
    c = conn.cursor()
    c.execute(sql, (name,))
    return c.fetchall()

def selectuser(conn, id_):
    sql = "SELECT * FROM profiles WHERE id = ?"
    c = conn.cursor()
    c.execute(sql, (id_,))
    return c.fetchall()

def insertuser(conn, vals):
    sql = "INSERT INTO profiles (id, mal_name, xp, level) VALUES (?, ?, ?, ?)"
    c = conn.cursor()
    c.execute(sql, vals)
    return c.lastrowid

def updateuser(conn, vals):
    sql = "UPDATE profiles SET mal_name = ?, xp = ?, level = ? WHERE id = ?"
    c = conn.cursor()
    c.execute(sql, vals)
    return c.lastrowid

def insertstats(conn, vals):
    sql = '''INSERT INTO stats (id, days, completed, meanscore)
    VALUES (?, ?, ?, ?)'''
    c = conn.cursor()
    c.execute(sql, vals)
    return c.lastrowid

def selectstats(conn, id_):
    sql='''SELECT profiles.id, profiles.mal_name, profiles.xp, profiles.level, stats.days, stats.completed, stats.meanscore
    FROM profiles LEFT JOIN stats
    WHERE profiles.id = stats.id AND profiles.id = ?'''
    c = conn.cursor()
    c.execute(sql, (id_,))
    return c.fetchall()

def updatestats(conn, vals):
    sql = '''UPDATE stats
    SET days = ?, completed = ?, meanscore = ?
    WHERE id = ?'''
    c = conn.cursor()
    c.execute(sql, vals)
    return c.lastrowid

def getlevel(conn, xp):
    sql = ''' SELECT *
    FROM levels
    WHERE ? BETWEEN minxp AND maxxp'''
    c = conn.cursor()
    c.execute(sql, (xp,))
    return c.fetchall()
