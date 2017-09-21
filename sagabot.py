#!/usr/bin/python3

import discord
import requests
import asyncio
from discord.ext import commands
from bs4 import BeautifulSoup
from scipy.stats import norm
import sqlite3
import re

client = commands.Bot(command_prefix="!", description="Show me your power level!")
thisroles={}
#variables for !mal
middle = norm(5, 2).pdf(5)
factor=60./13.

def dbconnect():
    try:
        conn = sqlite3.connect("malbot.db")
        return conn
    except Error as e:
        print(e)
    return None

def selectbyname(conn, name):
    sql = "select * from profiles where mal_name = ?"
    c = conn.cursor()
    c.execute(sql, (name,))
    return c.fetchall()

def selectuser(conn, id_):
    sql = "select * from profiles where id = ?"
    c = conn.cursor()
    c.execute(sql, (id_,))
    return c.fetchall()

def insertuser(conn, vals):
    sql = "insert into profiles (id, mal_name, tier, level) values (?, ?, ?, ?)"
    c = conn.cursor()
    c.execute(sql, vals)
    return c.lastrowid

def updateuser(conn, vals):
    sql = "update profiles set mal_name = ?, tier = ?, level = ? where id = ?" #(mal_name, tier, level, id)
    c = conn.cursor()
    c.execute(sql, vals)
    return c.lastrowid

def insertstats(conn, vals):
    sql = '''insert into stats (id, days, completed, meanscore)
    values (?, ?, ?, ?)'''
    c = conn.cursor()
    c.execute(sql, vals)
    return c.lastrowid

def selectstats(conn, id_):
    sql="select profiles.id, profiles.mal_name, profiles.level, stats.days, stats.completed, stats.meanscore from profiles left join stats where profiles.id = stats.id and profiles.id = ?"
    c = conn.cursor()
    c.execute(sql, (id_,))
    return c.fetchall()

def updatestats(conn, vals):
    sql = '''update stats
    set days = ?, completed = ?, meanscore = ?
    where id = ?'''
    c = conn.cursor()
    c.execute(sql, vals)
    return c.lastrowid

#@client.command()
#async def help():
#    await client.say('''
#    Polecenia: \n
#    **!malbind** <username> - wiąże z twoim Discordem podane konto na MAL. \n
#    **!mal** - dla związanego z twoim Discordem konta wylicza powerlevel i nadaje rangę. \n
#    **!malcheck** <username> - dla użytkownika pokazuje statystyki i powerlevel. Działa także dla niepowiązanych kont. \n
#    **!malfind** <zapytanie> - wyszukuje na MALu i zwraca pierwszy wynik - serię anime. \n
#    ''')

@client.command(pass_context=True, description="Wiąże z twoim Discordem podane konto na MAL.")
async def malbind(ctx, username_in : str):
    username = username_in.lower()
    if not re.match("^[a-z0-9_]*$", username):
        print("mal: Malformed MAL username")
        await client.say("Nieprawidłowy format nazwy profilu.")
        return

    conn = dbconnect()
    #print(ctx.message.author.id+" "+str(type(ctx.message.author.id)))
    with conn:
        user_row = selectuser(conn, int(ctx.message.author.id))
        check = selectbyname(conn, username)
        if check:
            print("malbind: username "+username+" already exists")
            if check[0][0] == int(ctx.message.author.id):
                await client.say("Już zbindowałeś to konto.")
            else:
                await client.say("Ktoś już zbindował konto "+username_in+".")
            return
        if not user_row:
            print("malbind: Inserting "+username+" for "+ctx.message.author.id)
            print(insertuser(conn, (int(ctx.message.author.id), username, "", "")))
            await client.say(ctx.message.author.name+": przypisano Ci konto MAL "+username_in)
        elif user_row[0][1] != username:
            print("malbind: Updating "+ctx.message.author.id+" to "+username)
            print(updateuser(conn, (username, user_row[0][2], user_row[0][3], int(ctx.message.author.id))))
            await client.say(ctx.message.author.name+": zmieniono Ci konto MAL na "+username_in)
        else:
            print("malbind: Row for ID "+ctx.message.author.id+" already exists!")
            await client.say("Już jest przypisane konto")

@client.command(description = "Dla użytkownika pokazuje statystyki i powerlevel. Działa także dla niepowiązanych kont.")
async def malcheck(username_in : str):
    username=username_in.lower()
    if not re.match("^[a-z0-9_]*$", username):
        print("malcheck: Malformed MAL username: "+username_in)
        await client.say("Nieprawidłowy format nazwy profilu.")
        return
    conn = dbconnect()
    with conn:
        user=selectbyname(conn, username)
        #print(user)
        if not user:
            #get it from MAL
            print("malcheck: User not in DB. Getting from MAL")
            soup=BeautifulSoup(requests.get("https://myanimelist.net/profile/"+username).text, 'html.parser')

            try:
                days=soup.select("div.di-tc.al")[0].text.split(' ')[1]
                completed=soup.select("a.circle.anime.completed")[0].next_sibling.text
                meanscore=soup.select("span.fn-grey2.fw-n")[1].parent.text.split(' ')[2]
            except IndexError:
                await client.say("Nie można pobrać danych z profilu. Czy na pewno dobrze podałeś nazwę?")
                return

            days_number= float(days)
            completed_number = float(completed.replace(',', ''))
            meanscore_number = float(meanscore)

            score_factor = norm(5, 2).pdf(meanscore_number) / middle

            powerlevel = int(round(days_number * completed_number * factor * score_factor, 0))
            await client.say("Konto MAL: "+username+"\nCompleted: "+completed+"\nDays: "+days+"\nMean score: "+meanscore+"\nPower level: "+str(powerlevel))
        else:
            print("malcheck: found user. Getting stats from DB.")
            id_=user[0][0]
            stats = selectstats(conn, id_)
            try:
                username, powerlevel, days, completed, meanscore = stats[0][1:]
            except IndexError:
                print("malcheck: Failed to retrieve stats for ID "+str(id_))
                await client.say("Profil MAL jest w bazie, ale nie ma statystyk. Właściciel powinien użyć polecenia !mal.")
                return
            await client.say("Konto MAL: "+username+ \
            "\nCompleted: "+str(completed)+ \
            "\nDays: "+str(days)+ \
            "\nMean score: "+str(meanscore)+ \
            "\nPower level: "+str(powerlevel))
            print(stats)


@client.command(pass_context=True, description="Dla związanego z twoim Discordem konta wylicza powerlevel i nadaje rangę.")
async def mal(ctx):
    conn = dbconnect()
    with conn:
        print("mal: Selecting ID "+ctx.message.author.id)
        user = selectuser(conn, int(ctx.message.author.id))
        if not user:
            print("mal: ID "+ctx.message.author.id+" not bound")
            await client.say("Nie masz zbindowanego konta. Użyj !malbind username")
            return
        else:
            username = user[0][1]
            tier_old = user[0][2]
            level_old = user[0][3]
    soup=BeautifulSoup(requests.get("https://myanimelist.net/profile/"+username).text, 'html.parser')

    try:
        days=soup.select("div.di-tc.al")[0].text.split(' ')[1]
        completed=soup.select("a.circle.anime.completed")[0].next_sibling.text
        meanscore=soup.select("span.fn-grey2.fw-n")[1].parent.text.split(' ')[2]
    except IndexError:
        await client.say("Nie można pobrać danych z profilu. Czy na pewno dobrze podałeś nazwę?")
        return

    days_number= float(days)
    completed_number = float(completed.replace(',', ''))
    meanscore_number = float(meanscore)

    score_factor = norm(5, 2).pdf(meanscore_number) / middle

    powerlevel = int(round(days_number * completed_number * factor * score_factor, 0))
    tier_new=''

    if powerlevel == level_old:
        print("mal: No change for "+ctx.message.author.name)
    #S-tier
    elif powerlevel > 1000000 :
        print("mal: S-tier for "+ctx.message.author.name)
        tier_new = 'S-tier'
        await client.say(ctx.message.author.name+" kwalifikuje się do S-tier!")
        await client.remove_roles(ctx.message.author, thisroles['A-tier'], thisroles['B-tier'])
        await client.add_roles(ctx.message.author, thisroles['S-tier'])
    #A-tier
    elif powerlevel > 100000 and powerlevel <= 1000000 :
        print("mal: A-tier for "+ctx.message.author.name)
        tier_new = 'A-tier'
        await client.say(ctx.message.author.name+" kwalifikuje się do A-tier!")
        await client.remove_roles(ctx.message.author, thisroles['S-tier'], thisroles['B-tier'])
        await client.add_roles(ctx.message.author, thisroles['A-tier'])
    #B-tier
    else:
        print("mal: B-tier for "+ctx.message.author.name)
        tier_new = 'B-tier'
        await client.say(ctx.message.author.name+" kwalifikuje się do B-tier!")
        await client.remove_roles(ctx.message.author, thisroles['A-tier'], thisroles['S-tier'])
        await client.add_roles(ctx.message.author, thisroles['B-tier'])
    #await client.add_roles(ctx.message.author, thisroles['under 9k'])

    conn = dbconnect()
    with conn:
        if powerlevel != level_old or tier_new:
            updateuser(conn, (username, tier_new, powerlevel, int(ctx.message.author.id)))
            print("mal: Updated user "+username+" "+ctx.message.author.id)
        print("mal: Updating stats")
        stats = selectstats(conn, int(ctx.message.author.id))
        if not stats:
            insertstats(conn, (int(ctx.message.author.id), days_number, completed_number, meanscore_number))
            print("mal: Stats inserted")
        else:
            updatestats(conn, (days_number, completed_number, meanscore_number, int(ctx.message.author.id)))
            print("mal: Stats updated")
    await client.say("Konto MAL: "+username+"\nCompleted: "+completed+"\nDays: "+days+"\nMean score: "+meanscore+"\nPower level: "+str(powerlevel))


@client.command(description="Wyszukuje na MALu i zwraca pierwszy wynik - serię anime.")
async def malfind(query : str):

    results=BeautifulSoup(requests.get('https://myanimelist.net/api/anime/search.xml?q='+query, auth=('Wikt', 'PASSWORD')).text, 'xml')
    try:
        top=results.find_all('entry')[0]
    except IndexError:
        await client.say("Nic nie znaleziono.")
        return

    title = top.title.text
    episodes = top.episodes.text
    score = top.score.text
    type_ = top.find('type').text
    start = top.start_date.text
    end = top.end_date.text
    id_ = top.id.text

    full = '**Title: **'+title+ \
        '\n**Episodes: **'+episodes+ \
        '\n**Score: **'+score+ \
        '\n**Type: **'+type_+ \
        '\n**Start date: **'+start+ \
        '\n**End date: **'+end+ \
        '\nhttps://myanimelist.net/anime/'+id_+'/'
    await client.say(full)

@client.event
async def on_ready():
    print('init: Logged in as')
    print(client.user.name)
    print(client.user.id)
    for i in discord.utils.get(client.servers, name='testMALmemes').roles:
        thisroles[i.name]=i

client.run('token')