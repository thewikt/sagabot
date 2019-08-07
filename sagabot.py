#!/usr/bin/python3

import discord
import asyncio
import aiohttp
from discord.ext import commands
from bs4 import BeautifulSoup
from scipy.stats import norm
from sagabot_db import *
from difflib import SequenceMatcher
from io import BytesIO
import re
from sys import argv

#config
#format: plik z wieloma linijkami, w każdej linijce jeden parametr "nazwa=wartość"
#oczekiwane parametry: token, mal_acct, mal_pwd, server

config={}
try:
    #inny konfig w argumencie, np. do testowania
    cfgfile=argv[1]
except IndexError:
    #default - produkcyjny
    cfgfile='config.txt'
with open(cfgfile, 'r') as f:
    config_lines=f.readlines()
for line in config_lines:
    kv=line.split("=")
    config[kv[0]]=kv[1].strip()

client = commands.Bot(command_prefix="!", description="Show me your power level!")
thisroles={}
tiers = dict(zip([(i*5, i*5+4) for i in range(22)], '[E-],[E],[E+],[D-],[D],[D+],[C-],[C],[C+],[B-],[B],[B+],[A-],[A],[A+],[S-],[S],[S+],[SS-],[SS],[SS+],[SSS]'.split(',')))
tiers[(110, 114)]='EX'
#variables for !mal
middle = norm(5.5, 3.5).pdf(5.5)
factor=60./13.
lock = asyncio.Lock()

async def fetch(session, url):
    async with session.get(url) as r:
        return await r.text()

async def calculateXP(days_number, completed_number, meanscore_number):
        score_factor = norm(5.5, 3.5).pdf(meanscore_number) / middle
        xp = int(round(days_number * completed_number * factor * score_factor, 0))
        return xp

@client.command(pass_context=True, description="Wiąże z twoim Discordem podane konto na MAL.")
async def malbind(ctx, username_in : str):
    username = username_in.lower()
    if not re.match("^[a-z0-9_-]*$", username):
        print("mal: Malformed MAL username")
        await ctx.send("Nieprawidłowy format nazwy profilu.")
        return

    conn = dbconnect()
    #print(ctx.message.author.id+" "+str(type(ctx.message.author.id)))
    with conn:
        user_row = selectuser(conn, ctx.message.author.id)
        check = selectbyname(conn, username)
        if check:
            print("malbind: username "+username+" already exists")
            if check[0][0] == ctx.message.author.id:
                await ctx.send("Już zbindowałeś to konto.")
            else:
                await ctx.send("Ktoś już zbindował konto "+username_in+".")
            return
        if not user_row:
            print("malbind: Inserting "+username+" for "+str(ctx.message.author.id))
            print(insertuser(conn, (ctx.message.author.id, username, "", "")))
            await ctx.send(ctx.message.author.name+": przypisano Ci konto MAL "+username_in)
        elif user_row[0][1] != username:
            print("malbind: Updating "+str(ctx.message.author.id)+" to "+username)
            print(updateuser(conn, (username, user_row[0][2], user_row[0][3], ctx.message.author.id)))
            await ctx.send(ctx.message.author.name+": zmieniono Ci konto MAL na "+username_in)
        else:
            print("malbind: Row for ID "+str(ctx.message.author.id)+" already exists!")
            await ctx.send("Już jest przypisane konto")

@client.command(description = "Dla użytkownika pokazuje statystyki i powerlevel. Działa także dla niepowiązanych kont.")
async def malcheck(ctx, username_in : str):
    username=username_in.lower()
    if not re.match("^[a-z0-9_-]*$", username):
        print("malcheck: Malformed MAL username: "+username_in)
        await ctx.send("Nieprawidłowy format nazwy profilu.")
        return
    conn = dbconnect()
    with conn:
        user=selectbyname(conn, username)
        #print(user)
        if not user:
            #get it from MAL
            print("malcheck: User not in DB. Getting from MAL")
            async with aiohttp.ClientSession() as session:
                text=await fetch(session, "https://myanimelist.net/profile/"+username)
            soup=BeautifulSoup(text, 'html.parser')

            try:
                days=soup.select("div.di-tc.al")[0].text.split(' ')[1]
                completed=soup.select("a.circle.anime.completed")[0].next_sibling.text
                meanscore=soup.select("span.fn-grey2.fw-n")[1].parent.text.split(' ')[2]
            except IndexError as e:
                await ctx.send("Nie można pobrać danych z profilu. Czy na pewno dobrze podałeś nazwę?")
                print(text)
                print(str(e))
                return

            days_number= float(days)
            completed_number = float(completed.replace(',', ''))
            meanscore_number = float(meanscore)

            xp = await calculateXP(days_number, completed_number, meanscore_number)
            level = (getlevel(conn, xp)[0][0])

            await ctx.send("Konto MAL: "+username+ \
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
                await ctx.send("Profil MAL jest w bazie, ale nie ma statystyk. Właściciel powinien użyć polecenia !mal.")
                return
            await ctx.send("Konto MAL: "+username+ \
            "\nCompleted: "+str(completed)+ \
            "\nDays: "+str(days)+ \
            "\nMean score: "+str(meanscore)+ \
            "\nLevel: "+str(level)+ \
            "\nXP: "+str(xp))


@client.command(description="Dla związanego z twoim Discordem konta wylicza powerlevel i nadaje rangę.")
async def mal(ctx):
    conn = dbconnect()

    with conn:
        print("mal: Selecting ID "+str(ctx.message.author.id))
        with (await lock):
            user = selectuser(conn, ctx.message.author.id)
        if not user:
            print("mal: ID "+str(ctx.message.author.id)+" not bound")
            await ctx.send("Nie masz zbindowanego konta. Użyj !malbind username")
            return
        else:
            username = user[0][1]
            xp_old = user[0][2]
            level_old = user[0][3]

            if not xp_old: xp_old = 0
            if not level_old: level_old = 0
    #TBD: EXPORT THIS TO FUNCTION V
    async with aiohttp.ClientSession() as session:
        text = await fetch(session, "https://myanimelist.net/profile/"+username)
    soup=BeautifulSoup(text, 'html.parser')
    try:
        days=soup.select("div.di-tc.al")[0].text.split(' ')[1]
        completed=soup.select("a.circle.anime.completed")[0].next_sibling.text
        meanscore=soup.select("span.fn-grey2.fw-n")[1].parent.text.split(' ')[2]
    except IndexError as e:
        await ctx.send("Nie można pobrać danych z profilu. Czy na pewno dobrze podałeś nazwę?")
        print(text)
        print(str(e))
        return

    days_number= float(days)
    completed_number = float(completed.replace(',', ''))
    meanscore_number = float(meanscore)

    xp = await calculateXP(days_number, completed_number, meanscore_number)

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
        await ctx.send(ctx.message.author.name+" zyskał "+str(increase)+" XP, pozostało "+str(remaining)+" do następnego poziomu")
    else:
        decrease = xp_old - xp
        remaining = maxxp - xp
        print("mal: "+ctx.message.author.name+" lost "+str(decrease)+" XP, "+str(remaining)+" left to next level")
        await ctx.send(ctx.message.author.name+" stracił "+str(decrease)+" XP, pozostało "+str(remaining)+" do następnego poziomu")

    if level > level_old:
        print("mal: "+ctx.message.author.name+" leveled up!")
        await ctx.send("**Level up!** "+ctx.message.author.name+" ma teraz level "+str(level))
    elif level < level_old:
        print("mal: "+ctx.message.author.name+" leveled down.")
        await ctx.send("Level down. "+ctx.message.author.name+" ma teraz level "+str(level))


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
        await ctx.send(ctx.message.author.name+" jest teraz w tierze **"+tier+"**!")
    else:
        print("mal: appropriate tier found, no other tiers found")

    #conn = dbconnect()
    with (await lock):
        with conn:
            if xp != xp_old:
                updateuser(conn, (username, xp, level, ctx.message.author.id))
                print("mal: Updated user "+username+" "+str(ctx.message.author.id))
            print("mal: Updating stats")
            stats = selectstats(conn, ctx.message.author.id)
            if not stats:
                insertstats(conn, (ctx.message.author.id, days_number, completed_number, meanscore_number))
                print("mal: Stats inserted")
            else:
                updatestats(conn, (days_number, completed_number, meanscore_number, ctx.message.author.id))
                print("mal: Stats updated")

    final_stats="Konto MAL: "+username+ \
    "\nCompleted: "+completed+ \
    "\nDays: "+days+ \
    "\nMean score: "+meanscore+ \
    "\nLevel: "+str(level)+ \
    "\nXP: "+str(xp)

    if xp == xp_old or not xp_old:
        final_stats+="\nDo następnego poziomu pozostało: "+str(maxxp-xp)+" XP"

    await ctx.send(final_stats)

# Polecenie zakomentowane - stare API najwyraźniej niedostępne. 
# Może wymagać adaptacji do Jikan. 
#@client.command(description="Wyszukuje serię anime na MALu.")
#async def malfind(ctx, query : str):
#    auth=aiohttp.BasicAuth(config['mal_acct'], password=config['mal_pwd'])
#    async with aiohttp.ClientSession(auth=auth) as session:
#        text = await fetch(session, 'https://myanimelist.net/api/anime/search.xml?q='+query)
#    soup=BeautifulSoup(text, 'xml')
#    try:
#        results=soup.find_all('entry')
#        scores = [SequenceMatcher(None, query, t.title.text).ratio() for t in results]
#        top = results[scores.index(max(scores))]
#    except ValueError:
#        await ctx.send("Nic nie znaleziono.")
#        return
#
#    title = top.title.text
#    episodes = top.episodes.text
#    score = top.score.text
#    type_ = top.find('type').text
#    start = top.start_date.text
#    end = top.end_date.text
#    id_ = top.id.text
#
#    full = '**Title: **'+title+ \
#        '\n**Episodes: **'+episodes+ \
#        '\n**Score: **'+score+ \
#        '\n**Type: **'+type_+ \
#        '\n**Start date: **'+start+ \
#        '\n**End date: **'+end+ \
#        '\nhttps://myanimelist.net/anime/'+id_+'/'
#    await ctx.send(full)

@client.command(description="Losuje smug dziewczynkę z API smug.kancolle.pl. (10s cooldown)", pass_context=True)
@commands.cooldown(1, 10.0)
async def smug(ctx):
    print("smug: getting a random smug pic")
    async with aiohttp.get("https://smug.kancolle.pl/smug/random") as r:
        json_r=await r.json()
    smug_pic=json_r['url']
    targetchan=ctx.message.channel
    print("smug: received response "+smug_pic+", posting to "+targetchan.name)

    async with aiohttp.get(smug_pic) as r:
        smug_img=BytesIO()
        while True:
            chunk=await r.content.read(1024)
            if not chunk:
                break
            smug_img.write(chunk)
        smug_img.seek(0)
    print("smug: saved file to memory, uploading")

    await client.send_file(targetchan, smug_img, filename=smug_pic.split('/')[-1])

@client.command(description="Dodaje smug do API smug.kancolle.pl.", pass_context=True)
async def smugadd(ctx):
    fromText=False
    try:
        attachment=ctx.message.attachments[0]['url']
    except (IndexError, KeyError):
        if len(ctx.message.content.split(' ')) > 1:
            attachment=ctx.message.content.split(' ')[1]
            fromText=True
        else:
            print("smugadd: nic nie zostało załączone")
            await ctx.send(ctx.message.author.name+": nie znaleziono załącznika ani linka.")
            return

    print("smugadd: sending "+attachment+" to the API")
    async with aiohttp.post("https://smug.kancolle.pl/smug/add/", data={'url':attachment, 'source':str(ctx.message.author)}, headers={'Authorization':'Token '+config['smugtoken']}) as r:
        if r.status == 200:
            print("smugadd: success")
            await ctx.send(ctx.message.author.name+": Dodano obrazek do zbioru smug.")
        else:
            print("smugadd: failure, response: "+str(r.status))
            print(await r.text())
            if fromText:
                await ctx.send(ctx.message.author.name+": Dodanie obrazka się nie powiodło. Czy link jest prawidłowy?")
            else:
                await ctx.send(ctx.message.author.name+": Dodanie obrazka się nie powiodło.")

@client.event
async def on_ready():
    print('init: Logged in as '+client.user.name)
    for i in discord.utils.get(client.guilds, name=config['server']).roles:
        thisroles[i.name]=i

client.run(config['token'])
