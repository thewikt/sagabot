#!/usr/bin/python3

import discord
import requests
import asyncio
from discord.ext import commands
from bs4 import BeautifulSoup
from scipy.stats import norm
from sagabot_db import *
from difflib import SequenceMatcher
import re

client = commands.Bot(command_prefix="!", description="Show me your power level!")
thisroles={}
tiers = dict(zip([(i*5, i*5+4) for i in range(22)], '[E-],[E],[E+],[D-],[D],[D+],[C-],[C],[C+],[B-],[B],[B+],[A-],[A],[A+],[S-],[S],[S+],[SS-],[SS],[SS+],[SSS]'.split(',')))
tiers[(110, 114)]='EX'
#variables for !mal
middle = norm(5, 2).pdf(5)
factor=60./13.
lock = asyncio.Lock()

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
    if not re.match("^[a-z0-9_-]*$", username):
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
    if not re.match("^[a-z0-9_-]*$", username):
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
            #TBD: update request to use aiohttp
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

            xp = int(round(days_number * completed_number * factor * score_factor, 0))
            level = (getlevel(conn, xp)[0][0])

            await client.say("Konto MAL: "+username+ \
            "\nCompleted: "+completed+ \
            "\nDays: "+days+ \
            "\nMean score: "+meanscore+ \
            "\nLevel: "+str(level)+ \
            "\nXP: "+str(xp))
        else:
            print("malcheck: found user. Getting stats from DB.")
            id_=user[0][0]
            stats = selectstats(conn, id_)
            try:
                username, xp, level, days, completed, meanscore = stats[0][1:]
            except IndexError:
                print("malcheck: Failed to retrieve stats for ID "+str(id_))
                await client.say("Profil MAL jest w bazie, ale nie ma statystyk. Właściciel powinien użyć polecenia !mal.")
                return
            await client.say("Konto MAL: "+username+ \
            "\nCompleted: "+str(completed)+ \
            "\nDays: "+str(days)+ \
            "\nMean score: "+str(meanscore)+ \
            "\nLevel: "+str(level)+ \
            "\nXP: "+str(xp))


@client.command(pass_context=True, description="Dla związanego z twoim Discordem konta wylicza powerlevel i nadaje rangę.")
async def mal(ctx):
    conn = dbconnect()

    with conn:
        print("mal: Selecting ID "+ctx.message.author.id)
        with (await lock):
            user = selectuser(conn, int(ctx.message.author.id))
        if not user:
            print("mal: ID "+ctx.message.author.id+" not bound")
            await client.say("Nie masz zbindowanego konta. Użyj !malbind username")
            return
        else:
            username = user[0][1]
            xp_old = user[0][2]
            level_old = user[0][3]

            if not xp_old: xp_old = 0
            if not level_old: level_old = 0
    #TBD: EXPORT THIS TO FUNCTION V
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

    xp = int(round(days_number * completed_number * factor * score_factor, 0))
    with conn:
        lvrow = getlevel(conn, xp)
        level = lvrow[0][0]
        maxxp = lvrow[0][2]

    if not xp_old:
        print("mal: New evaluation")
    elif xp == xp_old:
        print("mal: No change for "+ctx.message.author.name)
    elif xp > xp_old:
        increase = xp - xp_old
        remaining = maxxp - xp
        print("mal: "+ctx.message.author.name+" gained "+str(increase)+" XP, "+str(remaining)+" left to next level")
        await client.say(ctx.message.author.name+" zyskał "+str(increase)+" XP, pozostało "+str(remaining)+" do następnego poziomu")
    else:
        decrease = xp_old - xp
        remaining = maxxp - xp
        print("mal: "+ctx.message.author.name+" lost "+str(decrease)+" XP, "+str(remaining)+" left to next level")
        await client.say(ctx.message.author.name+" stracił "+str(decrease)+" XP, pozostało "+str(remaining)+" do następnego poziomu")

    if level > level_old:
        print("mal: "+ctx.message.author.name+" leveled up!")
        await client.say("**Level up!** "+ctx.message.author.name+" ma teraz level "+str(level))
    elif level < level_old:
        print("mal: "+ctx.message.author.name+" leveled down.")
        await client.say("Level down. "+ctx.message.author.name+" ma teraz level "+str(level))


    if level > 110:
        tier = tiers[(110, 114)]
    else:
        tiermin = level - (level % 5)
        tiermax = tiermin + 4
        tier = tiers[(tiermin, tiermax)]
    print("mal: "+ctx.message.author.name+" should be in tier "+tier)
    targetrole = thisroles[tier]
    otherroles=[i for i in ctx.message.author.roles if i.name != tier and i.name in tiers.values()]
    if (targetrole.name not in [i.name for i in ctx.message.author.roles]) or otherroles:
        print("mal: changing roles")
        await client.remove_roles(ctx.message.author, *otherroles)
        await asyncio.sleep(1)
        await client.add_roles(ctx.message.author, targetrole)
        print("mal: removed "+str([i.name for i in otherroles])+", added "+targetrole.name)
    else:
        print("mal: appropriate tier found, no other tiers found")

    #conn = dbconnect()
    with (await lock):
        with conn:
            if xp != xp_old:
                updateuser(conn, (username, xp, level, int(ctx.message.author.id)))
                print("mal: Updated user "+username+" "+ctx.message.author.id)
            print("mal: Updating stats")
            stats = selectstats(conn, int(ctx.message.author.id))
            if not stats:
                insertstats(conn, (int(ctx.message.author.id), days_number, completed_number, meanscore_number))
                print("mal: Stats inserted")
            else:
                updatestats(conn, (days_number, completed_number, meanscore_number, int(ctx.message.author.id)))
                print("mal: Stats updated")

    await client.say("Konto MAL: "+username+ \
    "\nCompleted: "+completed+ \
    "\nDays: "+days+ \
    "\nMean score: "+meanscore+ \
    "\nLevel: "+str(level)+ \
    "\nXP: "+str(xp)+ \
    "\nDo następnego poziomu pozostało: "+str(maxxp-xp)+" XP")


@client.command(description="Wyszukuje serię anime na MALu.")
async def malfind(*, query : str):

    output=BeautifulSoup(requests.get('https://myanimelist.net/api/anime/search.xml?q='+query, auth=('Wikt', 'PASSWORD')).text, 'xml')
    try:
        results=output.find_all('entry')
        scores = [SequenceMatcher(None, query, t.title.text).ratio() for t in results]
        top = results[scores.index(max(scores))]
    except ValueError:
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
    print('init: Logged in as '+client.user.name)
    for i in discord.utils.get(client.servers, name='Sasuga-san@Ganbaranai').roles:
        thisroles[i.name]=i

client.run('token')
