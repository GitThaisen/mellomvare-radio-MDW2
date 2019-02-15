#! /usr/bin/python
# -*- coding: iso-8859-1 -*-



#Dette er en hjelpefil for roller



rollerelasjon = {'sanger':2,'stryker':1,'trebl�ser':1,'messingbl�sere':1,'tangent':1}
#Her m� alle grupper inn

#Instrumenter som ikke er roller
ikkeRolle = ['engelsk horn','fortepiano', 'hammerklaver']

rolleliste = {
	#Sangere
	'sopran':{'gruppe':'sanger','tittel':'sopranen','aktiv':'synger','passiv':'synger'},
	'mezzosopran':{'gruppe':'sanger','tittel':'mezzosopranen','aktiv':'synger','passiv':'synger'},
	'alt':{'gruppe':'sanger','tittel':'alten','aktiv':'synger','passiv':'synger'},
	'tenor':{'gruppe':'sanger','tittel':'tenoren','aktiv':'synger','passiv':'synger'},
	'baryton':{'gruppe':'sanger','tittel':'barytonen','aktiv':'synger','passiv':'synger'},
	'bass':{'gruppe':'sanger','tittel':'bassen','aktiv':'synger','passiv':'synger'},
	#Ting med tangenter
	'piano':{'gruppe':'tangent','tittel':'pianisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'fortepiano':{'gruppe':'tangent','tittel':'pianisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'hammerklaver':{'gruppe':'tangent','tittel':'pianisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'klaver':{'gruppe':'tangent','tittel':'pianisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'cembalo':{'gruppe':'tangent','tittel':'cembalisten','aktiv':'spiller','passiv':'akkompagnert av'},
	#Strykere
	'fiolin':{'gruppe':'stryker','tittel':'fiolinisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'bratsj':{'gruppe':'stryker','tittel':'bratsjisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'cello':{'gruppe':'stryker','tittel':'cellisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'kontrabass':{'gruppe':'stryker','tittel':'bassisten','aktiv':'spiller','passiv':'akkompagnert av'},
	#Trebl�sere
	'klarinett':{'gruppe':'trebl�ser','tittel':'klarinettisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'bassklarinett':{'gruppe':'trebl�ser','tittel':'bassklarinettisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'klarinett':{'gruppe':'trebl�ser','tittel':'klarinettisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'fagott':{'gruppe':'trebl�ser','tittel':'fagottisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'fl�yte':{'gruppe':'trebl�ser','tittel':'fl�ytisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'engelsk horn':{'gruppe':'trebl�ser','tittel':'oboisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'obo':{'gruppe':'trebl�ser','tittel':'oboisten','aktiv':'spiller','passiv':'akkompagnert av'},
	#Messingbl�sere
	'horn':{'gruppe':'messingbl�ser','tittel':'hornisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'trompet':{'gruppe':'messingbl�ser','tittel':'trompetisten','aktiv':'spiller','passiv':'akkompagnert av'},
	}
