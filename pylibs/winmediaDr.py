#! /usr/local/bin/python
# -*- coding: utf-8 -*-

"""dls tjenester
utspillingsmodul.
Henter data fra databasen, sjekker utvalget fra sidevisningsmodulen, sjekker item som er på utspillingsmodulen
roterer så listen deretter.
"""

# TODO

#Støtte for albumbilder og titler, album illustrasjonene er i formen url = billedmappe + bilde

# BUGS

import MySQLdb as mdb
import re
import xml.dom.minidom
import time
from random import choice, sample
import math
import urllib
from httplib import HTTPConnection
import sys
import socket
import smtplib
from threading import Thread
from annonser import *
import re
from dbConn import database

ikkeDls = ['nett'] #Legg inn bloknavn som ikke støtter dls teknologien, nettradioen f. eks.

egenProd = 'EBU-NONRK' #Label for egenproduksjon
maxLevetid = 2
verbose = False
iDrift = 1
testum = 0
tagDest = False
timeout = 4
varsling = False

kanalAlow = ['p1','P2','NRK Petre','PETRE','NRK P3','Alltid Klassisk','mPetre','P3','p3']
kanalAlow = ['fmk','p3urort']
kanalAlow = ['p1','p2','p3','ak','an','mpetre','fmk','p3urort','p1of','ev1','ev2','nrk_5_1']
lagetGrense = 1980

#kanalAlow = ['mpetre']

#def database(host = "160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host = "localhost", user="tormodv", database="dab",passord=""):
#	"Lager en databaseconnection."
#	d = mdb.connect(user=user,passwd=passord, host=host)
#	d.select_db(database)
#	return d

metaW = '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />'
htmlWrapper = """<html>
<body>
%s
<font face="Arial">
<p>%s: %s</p>
<p>%s%s</p>
</font>
</body>
</html>"""
imgWrapper = """<img src="http://nettradio.nrk.no/albumill/%s" hspace="2" align="left" />
"""
XML = """<?xml version="1.0" encoding="iso-8859-1"?>
<nr>
<tl>%(tl)s</tl>
<st>%(st)s</st>
<ln>%(ln)s</ln>
<prgln>%(prgln)s</prgln>
<prglb>%(prglb)s</prglb>
<inf>%(inf)s</inf>
<url>%(url)s</url>
<anbf>%(anbf)s</anbf>
<itl>%(itl)s</itl>
<iart>%(iart)s</iart>
<ialbt>%(ialbt)s</ialbt>
<iill>%(iill)s</iill>
<ntl>%(ntl)s</ntl>
<nitl>%(nitl)s</nitl>
<nart>%(nart)s</nart>
<nalbt>%(nalb)s</nalbt>
<nill>%(nill)s</nill>
<act>%(act)s</act>
</nr>"""

EML = """<tl %(tl)s>
<st %(st)s>
<ln %(ln)s>
<prgln %(prgln)s>
<prglb %(prglb)s>
<inf %(inf)s>
<url %(url)s>
<anbf %(anbf)s>
<itl %(itl)s>
<iart %(iart)s>
<ialbt %(ialbt)s>
<iill %(iill)s>
<ntl %(ntl)s>
<nitl %(nitl)s>
<nart %(nart)s>
<nalbt %(nalb)s>
<nill %(nill)s>
<act %(act)s>"""

mal = EML

wrapper = """<?xml version="1.0" ?>
<WMAMETADATA>
<StreamName></StreamName>
<artist></artist>
<title></title>
<genre></genre>
<track></track>
<commandtype></commandtype>
<script>%s</script>
</WMAMETADATA>"""

wrapper = """<?xml version="1.0" ?>
<WMAMETADATA>
<commandtype>TEXT</commandtype>
<script>%s</script>
</WMAMETADATA>"""

wrapper = """<?xml version="1.0" ?>
<WMAMETADATA>
<artist>%s</artist>
<title>%s</title>
<genre></genre>
<track></track>
<commandtype>CAPTION</commandtype>
<script>%s</script>
</WMAMETADATA>"""

mp3Wrapper = """
<?xml version="1.0" ?>
<ICECASTMETADATA>
<StreamName>%s</StreamName>
<track>%s</track>
</ICECASTMETADATA>
"""

#Kjøre ting som iso strenger nå, omkode til slutt, intil databasen endres

"""Kommandtype one of:

URL
FILENAME
CAPTION
EVENT
OPENEVENT
TEXT"""

rappWrapper="""<html>
<body>
<table border="1">
%s
</table>
</body>
</html>
"""
lineWrapper = """<tr><td>%s</td><td>%s</td></tr>
"""

rappAdr = '/var/www/html/winmedia.html'
billedmappe = "http://nettradio.nrk.no/albumill/"
billedmappe = "/albumill/"
fakeURL = "http://160.68.118.65/php/includes/streamData.php"
#print len(mal)

crlf = chr(10) + chr(13)
crlf =  chr(10)

def parseLine(line):
	try:
		p=re.search(r'^.*(<body>)(.*?)(</body>)',line, re.DOTALL)
		return p.groups()[1]
	except:
		#return "feil"
		return line

def sendMail(til, fra, emne, melding, alvorlighetsgrad = 2):
	"Sender en mail fra NRKs postsystem"
	#Gjøre om til Iso
	emne = unicode(emne,'utf-8').encode('latin-1','replace')
	melding =  unicode(melding,'utf-8').encode('latin-1','replace')
	#Lage melding
	headers = "From: %s\r\nTo: %s\r\nX-Priority: %s\r\nSubject: %s\r\n\r\n" % (fra, ", ".join(til),alvorlighetsgrad, emne)
	msg = headers + melding
	#maexchowa01.nrk.no
	try:
		server = smtplib.SMTP('internsmtp.felles.ds.nrk.no')
		#server.set_debuglevel(1)
		server.sendmail(fra,til, msg)
		server.quit()
	except:
		return msg


def getUrl(d, kanal, port='9090', realm='dr'):
	"Gir riktig DR url på grunnlag av kanal, returnerer en liste"

	#sjekke kanaltabellen
	s  = []
	c = d.cursor()
	sql = """SELECT drUrl FROM kanalDistUrl WHERE navn =%s and type=%s"""
	c.execute(sql,(kanal, realm))
	rows = c.fetchall()
	for row in rows:
		s.append(row[0]% port)


	return s

def getUrlTest(kanal, port='9090'):
	"Gir riktig DR url på grunnlag av kanal, returnerer en liste"

	#sjekke kanaltabellen

	#return ["http://localhost/"]
	#if not kanal == 'p1_ndoa':
	if not kanal == 'mpetre':

		return []

	return ['http://160.68.104.136:%s/channel1' % port, 'http://160.68.104.136:%s/channel2' % port]

def sendDataWeb(data,uri, svar_fra_mottager = True, utverdier = []):
	#For at den ikke skal sende noe noe

	headers = {"Content-type": "application/xml",
		"Accept": "*/*",
		"User-Agent":"MDW 1.0 [no] (%s; U)"%sys.platform}
	#Splitte protokoll og uri
	protokol, uri = uri.split(':',1)
	uri=uri.lstrip('/')
	#Dele opp uri til hostname og url
	host,url = uri.split('/',1)

	try:
		conn = HTTPConnection(host)
		conn.request("POST", '/' + url,data, headers)
	except socket.error:
		#Legge inn forskjellige verdier her
		utverdier.append('Socket error')
		return 'Socket error'
	else:
		try:
			svar = conn.getresponse()
		except:
			utverdier.append('Connection reset by peer')
			return 'Connection reset by peer'
		if svar_fra_mottager:
			svar = svar.read()

		else:
			pass
			svar =  svar.status
		conn.close()
	utverdier.append(svar)
	return svar


def sjekkStatus(id, host = "nettradio.nrk.no", path = "/albumill/"):
	"Sjekker http status for etg bildeobjekt"
	try:
		conn = HTTPConnection(host)
		conn.request("GET", path + id)

	except:
		#Legge inn forskjellige verdier her
		if verbose:
			print 'Kunne ikke lage forbindelse'
	else:

		svar = conn.getresponse()
		conn.close()
		if svar.status == 200:
			return True
		else:
			return False

def finnUnger(noder,tag,kunEn=0):
	s=[]
	for node in noder:
		if node.nodeType == node.ELEMENT_NODE:
			if node.tagName == tag:
				s.append(node)
				if kunEn: return s

	return s

def hentVerdier(noder,lim=''):
	s=''
	for node in noder:
		if node.nodeType == node.TEXT_NODE:
			s+=node.data + lim
	return s

def finnVerdi(xmlobjekt,path,entity = 0):
	#path til nodeliste
	nodeliste = path.split('/')

	try:
		for node in nodeliste:
			if node=='':
				continue
			if node[0]!='@':
				xmlobjekt = finnUnger(xmlobjekt.childNodes,node,kunEn=1)[0]
			else:
				#returnere attributverdi
				return xmlobjekt.getAttribute(node[1:])

	except IndexError:
		return ''
	if not entity:
		return hentVerdier(xmlobjekt.childNodes)
	else:
		return entetyReplace(hentVerdier(xmlobjekt.childNodes))

def entetyReplace(s):
	s = s.replace('&','&amp;')

	return s



def minimumLevetid(d,kanal):
	"Finner den laveste gjenværende tid på en kanal"
	#Denne må modifiseres for å ta hensyn til alle dls'ene i kanalen
	#Kanskje heller ta vare på alle stoptidene slik at vi kan legge de på en stak som regenererer dls,ene?
	c = d.cursor()
	sql = """select
UNIX_TIMESTAMP(tid) + lengde - UNIX_TIMESTAMP()
 as tid_igjen
from iteminfo
where
 kanal=%s
order by tid_igjen
Limit 1
;"""
	c.execute(sql,(kanal))
	try:
		try:
			p = int(c.fetchone()[0])
		finally:
			c.close()
	except TypeError:
		return 0
	if kanal != 'ak':
		p += 600
	return p


def sammenlignTittler(tittel1,tittel2):
	"Sammenligner om titler er nesten like, f. eks. to satser av et verk, returnerer True hvis vi synes det er likt"
	#Vi finner forskjellen, Vi forutsetter at Verktittel begynner likt, dersom dette er et problem

	try:
		for i in range(len(tittel1)):
			if tittel1[i]!=tittel2[i]:break

	except:
		pass
	#Vi tar ut forskjellene
	likheten = tittel1[:i].rstrip(':.;, ')
	forskjell = tittel1[i:]

	#Vi gjør en enkel test i første omgang, siden kan dette brukes til noe ala : ... sats 1. fulgt av sats 2.

	if len(likheten)>3 * len(forskjell) and 'sats' in forskjell:
		return True
	else:
		return False


def ISOtilDato(dato,sekunder=0, sql=0):
	if not dato:
		return 0
	if type(dato)!=type(''):
		#Dette er en foreløpig patch for at en har begynt å bruke datetime objekter
		dato = dato.isoformat()
	if 'T' in dato or sql:
		try:
			if sekunder:
				tid= time.mktime ((int(dato[0:4]),int(dato[5:7]), int(dato[8:10]),int(dato[11:13]),int(dato[14:16])
						,int(dato[17:19]),-1,-1,-1))
			else:
				tid= time.mktime ((int(dato[0:4]),int(dato[5:7]), int(dato[8:10]),int(dato[11:13]),int(dato[14:16])
						,0,-1,-1,-1))
		except ValueError:
			tid = 0

	else:
		try:
			tid = int(dato)
		except:
			tid=0
	return tid

def finnKanaler(d, ikkeDistrikt = 0):
	"Returnerer alle kanalnavnene fra dab-databasen"
	c = d.cursor()
	if ikkeDistrikt:
		sql = """SELECT DISTINCT navn FROM kanal WHERE foreldre_id=id;"""
	else:
		sql = """SELECT DISTINCT navn FROM kanal;"""
	s = []
	c.execute(sql)
	while 1:
		p = c.fetchone()
		if p:
			s.append(p[0].lower())
		else:
			break
	c.close()
	return s

def  distriktskanal(d, kanal):
	"Returnerer en liste av underkanaler på grunnlag av et kanalnavn"
	#Finne først intern ideen på kanalen
	c = d.cursor()
	sql = """SELECT DISTINCT id FROM kanal WHERE navn =%s LIMIT 1;"""
	c.execute(sql,(kanal))
	row = c.fetchone()
	c.close()
	if row:
		kanalId = row[0]
	else:
		kanalId = 99
		print "UKJENT KANAL", kanal

	#Finne så hvilke distriktskanaler vi har

	c = d.cursor()
	sql = """SELECT navn FROM kanal WHERE foreldre_id =%s ;"""
	s = []
	c.execute(sql,(kanalId))
	while 1:
		p = c.fetchone()
		if p:
			s.append(p[0])
		else:
			break
	c.close()
	#Dersom denne ender i en null, så har denne kanalen ingen avleggere, ikke en gang seg selv.
	#Derfor legger vi til kanalen selv som det ene punktet i en liste
	if s == []:
		c = d.cursor()
		sql = """SELECT navn FROM kanal WHERE ID =%s LIMIT 1;"""
		s = []
		c.execute(sql,(kanalId))
		while 1:
			p = c.fetchone()
			if p:
				s.append(p[0])
			else:
				break
		c.close()
	return s

def finnHovedkanal(d, kanal):
	"Returnerer navnet pÃ¥ hovedkanalen eller kanalnavn pÃ¥ grunnlag av kanalnavn"
	#Finne fÃ¸rst intern ideen pÃ¥ morkanalen
	c = d.cursor()
	sql = """SELECT DISTINCT foreldre_id FROM kanal WHERE navn =%s LIMIT 1;"""
	c.execute(sql,(kanal))
	row = c.fetchone()
	c.close()
	if row:
		hovedId = row[0]
	else:
		hovedId = 99
		print "UKJENT KANAL", kanal

	#Finne hva hovedkanalen heter

	c = d.cursor()
	sql = """SELECT navn FROM kanal WHERE id =%s LIMIT 1;"""
	s = []
	c.execute(sql,(hovedId))
	row = c.fetchone()
	c.close()
	if row:
		return row[0]
	else:

		print "FEIL I SQL"



def finnBlokker(d):
	"Returnerer alle blokkene fra dab-databasen"

	c = d.cursor()
	sql = """SELECT DISTINCT id, navn FROM blokk;"""
	s = {}
	c.execute(sql)
	while 1:
		p = c.fetchone()
		if p:
			s[int(p[0])] = p[1]
		else:
			break
	c.close()
	return s


def hentVisningsvalg(d,kanal, blokkId, datatype=None, oppdatering = 0):
	"Henter ut visningsvalg og verdier for filterfunksjonen"
	#Først finner vi kanal_ID på kanalen.
	c= d.cursor()
	sql="""SELECT id FROM kanal WHERE navn =%s LIMIT 1
;
"""
	c.execute(sql,(kanal))
	row = c.fetchone()
	c.close()
	if row:
		kanalId = row[0]
	else:
		kanalId = 99
		print "UKJENT KANAL", kanal

	#Så sjekke om denne datatypen skal være breaking for den gitte kanalen
	#Dette kan være bestemt av datatypen også
	if ':' in datatype:
		return datatype.split(':',1) # Gir en [datatype,'breaking'] type

	c= d.cursor()
	sql="""SELECT breaking from datatyper
INNER JOIN dataikanal ON dataikanal.datatype_id=datatyper.id
WHERE kanal_id=%s AND blokk_id=%s AND tittel=%s LIMIT 1;"""
	c.execute(sql,(kanalId,blokkId,datatype))
	row = c.fetchone()
	c.close()
	#print row, datatype, kanal
	try:
		if row[0]=='Y':
			return [datatype,'breaking']
	except:
		#Dette kan feile dersom datatypen/kanalen ikke er registrert -> skal da ikke vise noe
		pass

	if oppdatering:
		c= d.cursor()
		sql = """SELECT DISTINCT
				alias
				FROM datatyper
				INNER JOIN dataikanal ON datatyper.id=dataikanal.datatype_id
				WHERE dataikanal.kanal_id = %s AND dataikanal.blokk_id = %s;"""
		s = []
		c.execute(sql,(kanalId,blokkId))
		while 1:
			p = c.fetchone()
			if p:
				s.append(p[0])
			else:
				break

		#Legge over til navn i steden for id
		if not s:
			return []

		if len(s)==1:
			s=s[0]
			sql = """SELECT tittel from datatyper
					WHERE id=%s;"""
		else:
			sql = """SELECT tittel from datatyper
					WHERE id in %s;"""
		s1 = []
		c.execute(sql,(s,))

		while 1:
			p = c.fetchone()
			if p:

				s1.append(p[0])
			else:
				break

		c.close()



		return s1



	else:
		c= d.cursor()
		sql = """SELECT datatyper.tittel FROM datatyper
		INNER JOIN dataikanal ON datatyper.id=dataikanal.datatype_id
		WHERE kanal_id=%s AND blokk_id = %s;"""
		s = []
		c.execute(sql,(kanalId,blokkId))
		while 1:
			p = c.fetchone()
			if p:
				s.append(p[0])
			else:
				break
		c.close()
		return s

def hentPgrinfo(d,kanal,hovedkanal):
	"Henter kanalnavn og kanalbeskrivelse. Returnerer en liste de kanalnavn er 1. element og beskrivelsen 2."
	c= d.cursor()
	sql = """SELECT tittel, beskrivelse FROM iteminfo WHERE kanal=%s AND type='pgr' LIMIT 1;"""

	c.execute(sql,(kanal,))
	try:
		try:
			tittel, beskrivelse = c.fetchone()
		finally:
			c.close()
	except TypeError:

		return []
	return [tittel, beskrivelse]

def hentNyheter(d,kanal, max=None):
	"Henter nyheter fra databasen, ev begrenset til max stykker"
	c= d.cursor()
	if not max:
		sql = """SELECT tittel, sammendrag FROM nyheter ORDER BY id;"""
		c.execute(sql)
	else:
		sql = """SELECT tittel, sammendrag FROM nyheter ORDER BY id LIMIT %s;"""
		c.execute(sql,(max,))


	while 1:
		row = c.fetchone()
		#print row
		if not row:
			c.close()
			break

		item = "%s. %s" % row
		if len(item)>128:
			item = row[1]
		if len(item)>128:
			item = item[:120] + '...'
		yield [item]


	c.close()


def hentProgrammeinfo(d,kanal,hovedkanal,distriktssending=0):
	"""Henter informasjon om programmet som er på lufta, returnerer dette som en tuple.
	Denne funksjonen bestemmer også om vi er i en distriktsflate eller ikke"""
	c= d.cursor()

	#Vi må sjekke om hovedkanalen har en distriktsflate

	sql = """SELECT element FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '1' LIMIT 1;"""

	c.execute(sql,(hovedkanal,))
	try:
		try:
			element, = c.fetchone()
		finally:
			c.close()
	except TypeError:
		element=''
		#Sjekke omo denne egentlig vil kunne feile

	if '<subject reference="ESCORT">R' in element:
		#Vi har en distriktssending
		distriktssending = True
		#Vi har ennå ikke distriktsvise programme info
		#Vi henter først ut navnet "Brandet" på kanalen
		c= d.cursor()

		sql = """SELECT branding FROM kanal WHERE navn=%s LIMIT 1;"""
		c.execute(sql,(kanal,))
		try:
			try:
				branding, = c.fetchone()
			finally:
				c.close()
		except TypeError:
			pass
			#Sjekke omo denne egentlig vil kunne feile
		if branding:
			tittelSufix = ' fra ' + branding
		else:
			tittelSufix = ''

		kanal = hovedkanal #Dette gjør at vi aldri henter programdata fra distriktsflaten

	else:
		#Vi skal ikke har regionvise resultater
		kanal = hovedkanal
		tittelSufix = ''
	c = d.cursor()
	sql = """SELECT tittel, beskrivelse, artist, tid, lengde FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '1' LIMIT 1;"""

	c.execute(sql,(kanal,))
	try:
		try:
			tittel, beskrivelse, artist, sendetid, lengde = c.fetchone()
		finally:
			c.close()
	except TypeError:
		#Dersom vi ikke har noe her, kan det hende det er en distriktskanal som ikke har egne metadata
		if hovedkanal and not distriktssending:
			return hentProgrammeinfo(d,hovedkanal,None,distriktssending=distriktssending)
		else:
			return '','','','','', distriktssending

	tittel = tittel + tittelSufix #Legger på f. eks. "fra NRK Trøndelag" på dirstriksflater
	if type(sendetid)!=type(''):
		#Dette er en foreløpig patch for at en har begynt å bruke datetime objekter
		sendetid = sendetid.isoformat()

	sekunderSiden = time.time() - ISOtilDato(sendetid,sekunder=1, sql=1)
	#print 888, sekunderSiden
	if sekunderSiden>30000:
		return  tittel, '', artist, sendetid[11:16], int(math.ceil(float(lengde) /60.0)), distriktssending


	return tittel, beskrivelse, artist, sendetid[11:16], int(math.ceil(float(lengde) /60.0)), distriktssending


def hentProgrammeNext(d,kanal,hovedkanal,distriktssending=0):
	"Henter informasjon om det neste programmet som skal på lufta, returnerer en liste med et element."
	c= d.cursor()
	sql = """SELECT tittel, tid FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '2' LIMIT 1;"""

	c.execute(sql,(kanal,))
	try:
		try:

			tittel, tid = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentProgrammeNext(d,hovedkanal,None)
		else:
			return ''

	return tittel

def hentEpg(d,kanal,hovedkanal,distriktssending=0):
	"Henter informasjon om programmene utover dagen og kvelden, returnerer en liste med et element."

	#Først finne klokka
	timen = time.localtime()[3]
	#Sikring for gamle data
	c= d.cursor()
	sql = """select TO_DAYS(NOW()) - TO_DAYS(date)  from epg_light_gyldighet WHERE kanal = %s LIMIT 1;"""

	c.execute(sql,(kanal,))

	try:
		try:
			dagerGammel = c.fetchone()[0]
		finally:
			c.close()

	except TypeError:

		if hovedkanal and not distriktssending:
			#Vi har en ukjent kanal, uten epg, vi prøver å gå opp et hakk
			return hentEpg(d,hovedkanal,None)
		else:
			return []

	if not (dagerGammel ==0 or (dagerGammel==1 and timen<6)):
		if verbose:print "EPG er GAMMEL"
		return []



	#Her er det vel ingen hensikt å dele på distrikter, der alle distriktene nå er like, med henhold til sendetidspunkter, eller?

	c= d.cursor()
	sql = """SELECT id, info FROM epg_light WHERE kanal=%s AND time=%s LIMIT 1;"""

	c.execute(sql,(kanal,timen))
	try:
		try:

			id, info = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentEpg(d,hovedkanal,None)
		else:
			return []


	item = "%s" % info #Legge inn På P1 i kveld...

	return [item]

def hentTextinfo(d,kanal,hovedkanal,distriktssending=0):
	"Henter informasjon og flashmeldinger om sendingen, støtter foreløpig kunn programnivået"

	c= d.cursor()
	sql = """SELECT tid, lengde, innhold FROM textinfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1;"""

	c.execute(sql,(kanal,))
	try:
		try:
			tid, lengde, innhold = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentTextinfo(d,hovedkanal,None)
		else:
			return ''



	#Rutine som sjekker om elementet er utløpt.

	oppdatere = 0 #?
	c1= d.cursor()
	sql = """SELECT tid, lengde FROM textinfo
	WHERE kanal=%s and localid='1';"""

	c1.execute(sql,(kanal,))
	try:
		tid1, lengde1 = c1.fetchone()
	except TypeError:
		#Raden eksisterer ikke

		c1.close()
		#Skal ikke ut
		return ''
	else:
		c1.close()

		slutttid1 = ISOtilDato(tid1,sekunder=1,sql=1) + lengde

		if time.time()>=slutttid1:


			return ''



	return innhold



def hentIteminfo(d,kanal,hovedkanal,distriktssending=0, item = False, info = False):
	"Henter informasjon om innslaget som er på lufta, returnerer en liste med et element."
	c= d.cursor()
	#samsending?

	sql = """SELECT kildekanal FROM iteminfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1 ;"""
	c.execute(sql,(kanal,))
	row =  c.fetchone()
	if row:
		kildekanal = row[0]
	else:
		kildekanal = False
	if kildekanal:
		#Da henter vi verdiene fra denne isteden
		kanal = kildekanal

	sql = """SELECT tittel, artist, beskrivelse,label, digastype, bildeID FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""

	c.execute(sql,(kanal,))
	try:
		try:
			tittel, artist, beskrivelse, label, digastype, bilde = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentIteminfo(d,hovedkanal,None, item = item, info = info)
		else:
			return '','','',''
	if digastype == '':digastype = 'Music' #Lex BMS
	if digastype !='Music':
		return '','','',''

	album = '' #Denne informasjonen finnes ikke foreløpi
	#Vi tester bildet
	if len(bilde)<4:bilde =''
	if not (bilde =='' or bilde =='.jpg'):
		if not sjekkStatus(bilde):
			#Bildet finnes ikke, vi trimmer
			bilde = bilde[-16:]
			if not sjekkStatus(bilde):
				#Finnes fremdeles ikke
				bilde =''
		else:
			pass
	else:
		bilde = ''

	#Artist feltet må endres litt
	if artist:
		artist = artist.replace('|',' ')
		artist = artist.lstrip('. ')
		artist = artist[0].upper() + artist[1:]

	#Vi finner opptaksdato
	c= d.cursor()
	sql = """SELECT YEAR(laget) FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
	c.execute(sql,(kanal,))
	try:
		try:
			laget, = c.fetchone()
		finally:
			c.close()
	except :
		laget = 0
	else:
		if laget<lagetGrense:
			tittel = "%s, innspilt %s," % (tittel,laget)

	if info and beskrivelse:
		album = beskrivelse



	return tittel, artist, album, bilde

def hentNewsItem(d,kanal,hovedkanal,distriktssending=0, news = False, info = False):
	"Henter informasjon om innslaget som er på lufta, returnerer en liste med et element."
	c= d.cursor()
	#samsending?

	sql = """SELECT kildekanal FROM iteminfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1 ;"""
	c.execute(sql,(kanal,))
	row =  c.fetchone()
	if row:
		kildekanal = row[0]
	else:
		kildekanal = False
	if kildekanal:
		#Da henter vi verdiene fra denne isteden
		kanal = kildekanal

	sql = """SELECT tittel, artist, beskrivelse,label, digastype, bildeID FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""

	c.execute(sql,(kanal,))
	try:
		try:
			tittel, artist, beskrivelse, label, digastype, bilde = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentNewsItem(d,hovedkanal,None, news = news, info = info)
		else:
			return '','','',''

	if digastype == '':digastype = 'Music' #Lex BMS
	if digastype !='News':
		return '','','',''


	album = '' #Denne informasjonen finnes ikke foreløpig
	if len(bilde)<4:bilde =''

	if not (bilde =='' or bilde =='.jpg'):
                if not sjekkStatus(bilde):
                        #Bildet finnes ikke, vi trimmer
                        bilde = bilde[-16:]
                        if not sjekkStatus(bilde):
                                #Finnes fremdeles ikke
                                bilde =''
                else:
                        pass
        else:
                bilde = ''





	#Artist feltet må endres litt
	if artist:
		artist = artist.replace('|',' ')
		artist = artist.lstrip('. ')
		artist = artist[0].upper() + artist[1:]

	#Vi finner opptaksdato
	c= d.cursor()
	sql = """SELECT YEAR(laget) FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
	c.execute(sql,(kanal,))
	try:
		try:
			laget, = c.fetchone()
		finally:
			c.close()
	except :
		laget = 0
	else:
		if laget<lagetGrense:
			tittel = "%s, innspilt %s," % (tittel,laget)
	#Hack for IBSEN
	if beskrivelse:
		album = beskrivelse
		#Så et nytt hack
	if kanal in ['nrk_5_1','gull','barn']:
		#Vi skal ikke ha med artist
		artist = ''
	if not news:
		tittel = ''
		artist = ''
	if not info:
		album = ''

	return tittel, artist, album, bilde


def hentItemNext(d,kanal,hovedkanal,distriktssending=0, musikk=False, news = False):
	"Henter informasjon om det neste innslaget som skal på lufta, returnerer en liste med et element."
	c= d.cursor()
	#samsending?

	sql = """SELECT kildekanal FROM iteminfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1 ;"""
	c.execute(sql,(kanal,))
	row =  c.fetchone()
	if row:
		kildekanal = row[0]
	else:
		kildekanal = False
	if kildekanal:
		#Da henter vi verdiene fra denne isteden
		kanal = kildekanal

	#Først finne ut om vi har to like titler. Dersom denne feiler har vi i alle fall ikke noen like titler.
	try:
		sql = """SELECT tittel FROM iteminfo WHERE kanal=%s AND type='item' AND (localid = '4' OR localid = '3')  LIMIT 2;"""
		c.execute(sql,(kanal,))

		tittel1 = c.fetchone()[0]
		tittel2 = c.fetchone()[0]
	except:
		pass

	#Dersom titlene er like med untak av satsbetegnelsene viser vi ingenting
	else:
		if sammenlignTittler(tittel1,tittel2):
			return '','','',''

	#Ellers viser vi nesteinformasjon
	sql = """SELECT tittel,artist, beskrivelse, digastype, bildeID FROM iteminfo WHERE kanal=%s AND type='item' AND localid = '4' LIMIT 1;"""


	c.execute(sql,(kanal,))
	try:
		try:
			tittel, artist, beskrivelse, digastype, bilde = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentItemNext(d,hovedkanal,None, musikk=musikk, news=news)
		else:
			return '','','',''
	if digastype == '':digastype = 'Music' #Lex BMS
	if digastype == 'Music' and not musikk:
		#Vi skal ikke vise
		return '','','',''
	if digastype == 'News' and not news:
		#Vi skal ikke vise
                return '','','',''



	album = ''
	if bilde!='':
		if not sjekkStatus(bilde):
			bilde =''
		else:
			bilde = billedmappe + bilde

	#Artist feltet må endres litt
	if artist:
		artist = artist.replace('|',' ')
		artist = artist.lstrip('. ')
		artist = artist[0].upper() + artist[1:]

	#Aldri infofelt paa neste, og ikke artis paa news
	if digastype =='News':
		#Vi skal ikke ha med kun tittel, pga plassmangel
		return tittel, '', '', ''

	return tittel, artist, album, bilde

def hentBadetemperaturer(d,kanal,hovedkanal,distriktssending=0):
	"Henter badetemperaturer til reiseradioen o.l."
	c= d.cursor()
	sql = """select
stedsnavn,
vanntemperatur

from bade_temp
where
vanntemperatur <> 0
and
TO_DAYS(NOW()) - TO_DAYS(oppdatert) = 0
and svarteliste = 'N'
order by
vanntemperatur
desc
;"""
	s=[]
	listestreng = 'Badetemperaturene : Høyest - '
	c.execute(sql,)
	temperaturliste = c.fetchall()
	if len(temperaturliste) == 0:
		return []
	if len(temperaturliste) > 12:
		temperaturliste = [temperaturliste[0]]+sample(temperaturliste[1:-1],10)+ [temperaturliste[-1]]
	for temp in temperaturliste:
		listestreng += "%s:%s|" % temp
	listestreng += '(lavest)'


	#Sette sammen dls til så få linjer som mulig
	part = ''
	deler = listestreng.split('|')
	for delen in deler:

		if part:
			if len(part) + len(delen) < 125:
				part = part + ' ' + delen
			elif len(delen) < 125:
				#Vi legger den ferdige dls fragmentet til listen
				s.append(part + '...')
				part = '...' + delen

		else:

			part = delen
	#Opprydding vi må uansett legge til den siste part
	s.append(part)


	return s

def storForbokstav(item):
	return item[0].upper() + item[1:]

def roter(s,n):
	"Roterer en liste N plasser"
	return s[n:] + s[:n]

def querryNettradioBase(tittel,kanal):
	#return ' ','NRK nettradio','http://',' ',' '
	#JTS ikke i drift
	return '','','','',''

	if not iDrift:
		return "Et bilde","En tekst","En lenke","En url","En act"
	try:
		xmldok = sendDataGet(fakeURL, tittel, kanal)
		#print xmldok
		pars = xml.dom.minidom.parseString(xmldok)
		a = finnVerdi( pars,'program/pic',  entity = 0).encode('iso-8859-1')
		b = finnVerdi( pars,'program/text',  entity = 0).encode('iso-8859-1')
		c = finnVerdi( pars,'program/links',  entity = 0).encode('iso-8859-1')
		d = finnVerdi( pars,'program/url',  entity = 0).encode('iso-8859-1')
		e = finnVerdi( pars,'program/act',  entity = 0).encode('iso-8859-1')
		#Vi skrur av de ferdiglagede tekstene
		b = ''
		return a,b,c,d,e
	except:
		return '','','','',''



def sendDataStreambase(dok,baseUrl,kanalnavn,interval=4,command='start',password='nettradioscript'):
	#For at den ikke skal sende noe n
	if not iDrift or testum:
		return "Ville ha sendt til %s adressen!" % baseUrl
	#if kanalnavn=='p3':kanalnavn='petre'
	sendUrl = baseUrl
	data = {}
	data['channel']=kanalnavn.encode('iso-8859-1')
	data['type'] = 'XML'
	data['data'] = dok
	data['interval'] = interval
	data['command'] = command
	data['password'] = password
	data_enc = urllib.urlencode(data)
	#print data_enc
	a=urllib.urlopen(sendUrl,data_enc)
	svar = a.read(400)
	a.close()
	return svar

def sendDataGet(url, navn, kanal):
	tilogData = url + '?' + urllib.urlencode({'name':navn,'channel':kanal})
	msg = "Ikke svar"

	u=urllib.urlopen(tilogData)
	try:

		msg =u.read(2048)


	finally:
		u.close()
	return msg

def getOffNavn(d, kanal):
	"Henter det offisielle navnet for kanal"
	c =  d.cursor()
	sql = """SELECT OFFNAVN from kanal where navn=%s LIMIT 1"""
	c.execute(sql, (kanal))
	offnavn = 'NRK'
	for row in c.fetchall():
		offnavn = row[0]
	c.close()
	return offnavn

def lagMetadata(kanal='alle',datatype=None,id='', verbose=False, loggWin = False):
	"Henter data for en gitt kanal ut i fra de forskjellige databasene og setter sammen til metadata som mates inn i nkoderne"
	rapp3 = []
	rapp = []
	d = database()
	if kanal == 'alle':
		kanaler = finnKanaler(d,ikkeDistrikt = 1)
	else:
		kanaler = [kanal]
		#Det kan hende at kanalene er delt opp i distrikter - eks. p1oslo


	#Finne blokker
	blokker = finnBlokker(d)

	for kanal in kanaler:
		#For inføringsfasen kan vi filtrere hvilke kanaler som skal fra denne applikasjonen
		#if kanal not in kanalAlow:
		#	continue
		utdata = {}
		#Hente basisverdier for prglb, inf, anbf og url
		#NB dersom vi mangler programinfo vil denne feile, vi setter derfor inn  nullverdier.
		try:
			utdata['prglb'],utdata['inf'],utdata['anbf'],utdata['url'],utdata['act'] = querryNettradioBase(hentProgrammeinfo(d,kanal,kanal)[0],kanal)
		except IndexError:
			utdata['prglb'],utdata['inf'],utdata['anbf'],utdata['url'],utdata['act'] = '','','','',''


		#Det kan hende at kanalene er delt opp i distrikter - eks. p1oslo
		#utvid kanaler
		distriktskanaler = distriktskanal(d, kanal)
		if len(distriktskanaler) == 1:
			#Vi har kunn en kanal, distrikskanal eller kanalen selv, vi mÃ¥ finne moderkanalen
			hovedkanal = finnHovedkanal(d, kanal)
		else:
			#Vi har en kanal med barn, ergo er hovedkanalen kanalen selv.
			hovedkanal = kanal

		for kanal in distriktskanaler:
			offnavn = getOffNavn(d, kanal)
			#print offnavn
			for blokkId in blokker:
				#print blokkId
				if blokker[blokkId] not in ikkeDls:
					if verbose:print "Ikke vis som DLS på %s" % blokker[blokkId]
					continue

				if verbose:print "Viser på %s" % blokker[blokkId]

				#Bygge opp visningslista
				#Hente visningsvalg
				visningsvalg = hentVisningsvalg(d, kanal, blokkId, datatype=datatype)
				oppdateres = hentVisningsvalg(d, kanal, blokkId, datatype=datatype, oppdatering = 1)

				if verbose:print "Visningsvalg:", visningsvalg
				if verbose:print "Opdateringskriterie;", oppdateres

				#Sjekke om det er nødvendig å oppdatere
				if not datatype in oppdateres:
					if verbose:print "SKAL IKKE VISES", kanal,blokkId
					continue

				s=[]
				#Så til tjenestegruppene
				if 'news' in visningsvalg:
					if listetype == 0:
						max = 1
					else:
						max = None
					nytt = hentNyheter(d,kanal,max=max)
				else:
					nytt = []

				#Denne typen er foreløpig ikke støttet eller nødvendig
				"""
				if 'pgrinfo' in visningsvalg:
					s.extend(hentPgrinfo(d,kanal,hovedkanal))
				"""

				if 'programmeinfo' in visningsvalg:
					utdata['tl'], info, utdata['prgln'], utdata['st'], utdata['ln'], distriktssending = hentProgrammeinfo(d,kanal,hovedkanal)
					#Ettersom vi ikke skal stryke standardinformsjonen, med et tomt feilt fra PI, må vi gjøre følgende
					if info != '':
						utdata['inf'] = info
					if not 'inf' in utdata : utdata['inf']=''

				else:
					if not 'tl' in utdata : utdata['tl'] = ''
					if not 'inf' in utdata : utdata['inf'] = ''
					if not 'prgln' in utdata : utdata['prgln'] = ''
					if not 'st' in utdata : utdata['st'] = ''
					if not 'ln' in utdata : utdata['ln'] = ''
					distriktssending = False

				if 'textinfo' in visningsvalg:
					info = hentTextinfo(d,kanal,hovedkanal)
					if info !='':
						utdata['inf'] = info
				else:
					if not 'inf' in utdata : utdata['inf'] = ''


				if 'iteminfo' in visningsvalg or 'musicInfo' in visningsvalg:
					#Musikkobjekter
					tittel, artist, album, bilde = hentIteminfo(d,kanal,hovedkanal, distriktssending = distriktssending, item = 'iteminfo' in visningsvalg, info = 'musicInfo' in visningsvalg)
				else:
					tittel, artist, album, bilde = '','','',''

				if 'newsItem' in visningsvalg or 'newsInfo' in visningsvalg:
					#Andre innslag

					n_tittel, n_artist, n_album, n_bilde = hentNewsItem(d,kanal,hovedkanal, distriktssending = distriktssending, news = 'newsItem' in visningsvalg, info = 'newsInfo' in visningsvalg)
				else:
					n_tittel, n_artist, n_album, n_bilde = '','','',''
					#Disse vil aldri opptre samtidig
				if n_tittel: tittel = n_tittel
				if n_artist: artist = n_artist
				if n_album: album = n_album
				if n_bilde: bilde = n_bilde

				utdata['itl'], utdata['iart'], utdata['ialbt'], utdata['iill'] = tittel, artist, album, bilde
				#For å sørge for at vi har et komplett sett uansett
				if not 'itl' in utdata : utdata['itl'] = ''
				if not 'iart' in utdata : utdata['iart'] = ''
				if not 'ialbt' in utdata : utdata['ialbt'] = ''
				if not 'iill' in utdata : utdata['iill'] = ''


				if 'itemNext' in visningsvalg or 'newsItemNext' in visningsvalg:
					utdata['nitl'], utdata['nart'], utdata['nalb'], utdata['nill'] = hentItemNext(d,kanal,hovedkanal, distriktssending = distriktssending, musikk = 'itemNext' in visningsvalg, news = 'newsItemNext' in visningsvalg)
				else:
					if not 'nitl' in utdata : utdata['nitl'] = ''
					if not 'nart' in utdata : utdata['nart'] = ''
					if not 'nalb' in utdata : utdata['nalb'] = ''
					if not 'nill' in utdata : utdata['nill'] = ''


				if 'programmeNext' in visningsvalg:
					utdata['ntl'] = hentProgrammeNext(d,kanal,hovedkanal)
				else:
					if not 'ntl' in utdata : utdata['ntl'] = ''

				"""if 'epg' in visningsvalg:
					s.extend(hentEpg(d,kanal,hovedkanal))
				"""
				#Så er det badetemperaturene - kan bli laaaaange
				if 'bath' in visningsvalg:
					s.extend(hentBadetemperaturer(d,kanal,hovedkanal))

				#**** Siden vi har med xml at lave skal konvertering av & etc skje her
				if verbose:print utdata
				utdok = mal % utdata
				#print utdok, len(utdok)

				#kanal = 'fmk'

				#Finne riktig url



				enkoderurls = getUrl(d, kanal, port='9090')

				#Sjekke bilde
				if utdata['iill'] !='':
					imgTag=imgWrapper % utdata['iill']
					#print imgTag
				else:
					imgTag = ''
				#lt gt av xml
				utdok = utdok.replace('<','&lt;').replace('>','&gt;')
				#gre datafeltene litt
				if tagDest:
					utdata['itl'] = '[%s]'
				utdata['tl'] = utdata['tl'].replace('&','&amp;').replace('"','&quot;')
				utdata['itl'] = utdata['itl'].replace('&','&amp;').replace('"','&quot;')
				utdata['iart'] = utdata['iart'].replace('&','&amp;').replace('"','&quot;')
				utdata['nitl'] = utdata['nitl'].replace('&','&amp;').replace('"','&quot;')
				utdata['nart'] = utdata['nart'].replace('&','&amp;').replace('"','&quot;')
				if utdata['itl']:
					if utdata['iart']:
						utdata['itl'] = " med ".join([utdata['itl'],utdata['iart']])
					else:
						pass
					if utdata['nitl']:
						if utdata['nart']:
							utdata['nitl'] = ", neste: " + " med ".join([utdata['nitl'],utdata['nart']])
						else:
							utdata['nitl'] = ", neste: " + utdata['nitl']
				elif utdata['nitl']:
					utdata['nitl']="Neste: " + utdata['nitl']

				#Legge inn i wrapper
				if offnavn == utdata['tl']:
					utdata['tl'] = ''
				utdok = htmlWrapper % (imgTag, offnavn, utdata['tl'], utdata['itl'], utdata['nitl'])
				utdok = wrapper % (utdata['iart'], utdata['itl'], utdok)
				#print utdok
				if tagDest:
					utdok = utdok % (offnavn, offnavn)
				#Så lage utf-8 støtte

				utdok = unicode(utdok, encoding = 'latin-1').encode('latin-1')
				if verbose:print kanal
				if verbose:print utdok

				for encUrl in enkoderurls:
					if verbose:print encUrl
					try:
						if tagDest:
							pass

						if timeout:
							utverdier = []
							argumenter = {'utverdier':utverdier}
							t = Thread(target=sendDataWeb,
							args=(utdok,encUrl),
							kwargs=argumenter)
							t.setDaemon(1)
							t.start()
							t.join(timeout)
							try:
								u = utverdier[0]
							except:
								u = 'Udefinert'
						else:
							u = sendDataWeb(utdok, encUrl)
					except 0:
						u = 'Kunne ikke sende'
						if verbose==False:
							pass
							#sendMail(['tormodv@nrk.no'], 'enkodere@nrk.no', 'Feil i metadatatjeneste WIN' , 'Feil i metadataene: %s' % offnavn, alvorlighetsgrad = 2)
					#Sjekke utverdier
					if u == 'Socket error':
						pass
						if varsling:sendMail(['tormodv@nrk.no'], 'enkodere@nrk.no', 'Feil i metadatatjeneste WIN, melder socket error' , 'Feil i metadataene: %s' % kanal, alvorlighetsgrad = 2)
					elif u == 'Connection reset by peer':
						pass
						#***Legg i n feilhandtering her
					rapp.append((offnavn, u))
					if verbose:
						print 'SVAR:'
						print u



				#Samme for mp3, vi setter ikke dette inn på enkoderne naa
				enkoderurls = getUrl(d, kanal, port='9091', realm='test')
				utdok = mp3Wrapper %  (offnavn, utdata['tl'] + ':' + utdata['itl'])
				utdok = unicode(utdok, encoding = 'latin-1').encode('utf-8')
				if verbose:print utdok
				for encUrl in enkoderurls:
					if verbose:print encUrl
					try:
						if tagDest:
                                                        pass
                                                        utdok1 = utdok % (encUrl[-17:] + ' ' + offnavn)
						else:
							utdok1 = utdok
						#Sende dataene
						if timeout:
							utverdier = []
							argumenter = {'utverdier':utverdier}
							t = Thread(target=sendDataWeb,
							args=(utdok1,encUrl),
							kwargs=argumenter)
							t.setDaemon(1)
							t.start()
							t.join(timeout)
							try:
								u = utverdier[0]
							except:
								u = 'Udefinert'
						else:
							u = sendDataWeb(utdok1, encUrl)
					except 0:
						u = 'Kunne ikke sende'
                                        if verbose:
						print 'SVAR:'
                                                print u
					rapp3.append((offnavn, u))
					if u == 'Socket error':
                                                pass
                                                if varsling:sendMail(['tormodv@nrk.no'], 'enkodere@nrk.no', 'Feil i metadatatjeneste mp3, melder socket error' , 'Feil i metadataene: %s' % kanal, alvorlighetsgrad = 2)

				"""
				try:
					u = '"%s"' % sendDataStreambase(utdok,streambaseUrl,kanal)
				except 0:
					#Dette må gjøres på en annen måte her, meldingene må gå til dab som svar og der fyres som en feilmelding
					return error("nr11",quark, melding="Kunne ikke sende til Streambase")
				"""

				#f=open('test.txt','a')
				#f.write(time.ctime() + kanal + '\n'+ u+'\n')
				#f.close()
				#if verbose:print "Dette svarte tjener:" , u

				#return 0
				#lagTestWebNett.sendData(kanal, eml=utdok, svar=u)
				#print rapp, rapp3

	#Lukke databasen
	#Generere og lagre rapp
	if loggWin:
		rappTabell = ''
		for line in rapp:
			rappTabell += lineWrapper % (line[0],  parseLine(line[1]))
		rapport =  rappWrapper % rappTabell
		f = open(rappAdr,'w')
		f.write(rapport)
		f.close()
		d.close()

if __name__=='__main__':
	for i in range(3):
		now = time.time()
		lagMetadata(kanal='alle',datatype='iteminfo', verbose=False, loggWin = True)
		brukt = time.time() - now
		if 15-brukt>=0:
			time.sleep(15-brukt)

