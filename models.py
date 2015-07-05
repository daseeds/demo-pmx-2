#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from google.appengine.ext import ndb


sessionState = ["run", "stop"]
site_list = ["", "Gemenos", "Balrup", "Tours", "Fareham"]
propertyKind = ["Property", "Instrumentation", "Consumable", "Instruction"]

class Account(ndb.Model):
	reference = ndb.StringProperty(default="")

class Dataflow(ndb.Model):
	reference = ndb.StringProperty(default="")
	account = ndb.StringProperty(default="")
	inputKeys = ndb.StringProperty(repeated=True)
	serviceTypes = ndb.KeyProperty(kind='ServiceType', repeated=True)
	fullProducts = ndb.KeyProperty(kind='FullProduct', repeated=True)
	productKeysMap = ndb.StringProperty(repeated=True)

class ServiceType(ndb.Model):
	parent = ndb.KeyProperty(kind='Dataflow')
	dataflow = ndb.StringProperty(default="")
	account = ndb.StringProperty(default="")
	name = ndb.StringProperty(default="")
	inputKeys = ndb.StringProperty(repeated=True)

class Service(ndb.Model):
	reference = ndb.StringProperty(default="")
	dataflow = ndb.StringProperty(default="")
	account = ndb.StringProperty(default="")
	properties = ndb.KeyProperty(kind='Property', repeated=True)
	stype = ndb.StringProperty()
	inputKeys = ndb.StringProperty(repeated=True)
	serviceType = ndb.KeyProperty(kind='ServiceType')
	domain = ndb.StringProperty()

class FullProduct(ndb.Model):
	name = ndb.StringProperty(default="")
	services = ndb.KeyProperty(kind='Service', repeated=True)
	product = ndb.KeyProperty(kind='Product')
	dataflow = ndb.StringProperty(default="")
	account = ndb.StringProperty(default="")

class Product(ndb.Model):
	reference = ndb.StringProperty(default="")
	properties = ndb.KeyProperty(kind='Property', repeated=True)
	inputKeys = ndb.StringProperty(repeated=True)
	orderItem = ndb.StringProperty(default="")
	dataflow = ndb.StringProperty(default="")
	account = ndb.StringProperty(default="")

class Property(ndb.Model):
	name = ndb.StringProperty(default="")
	value = ndb.StringProperty(default="")
	site = ndb.StringProperty(default="", choices=site_list)
	kind = ndb.StringProperty(default=propertyKind[0], choices=propertyKind)
	parent = ndb.KeyProperty()
	dataflow = ndb.StringProperty(default="")
	account = ndb.StringProperty(default="")


class Process(ndb.Model):
	reference = ndb.StringProperty(default="")
	sElec = ndb.KeyProperty(kind='Service', repeated=True)
	sElecSentinel = ndb.ComputedProperty(lambda self: len(self.sElec) == 0)
	sGraph = ndb.KeyProperty(kind='Service', repeated=True)
	sGraphSentinel = ndb.ComputedProperty(lambda self: len(self.sGraph) == 0)
	sCarrier = ndb.KeyProperty(kind='Service', repeated=True)
	sCarrierSentinel = ndb.ComputedProperty(lambda self: len(self.sCarrier) == 0)
	sPack = ndb.KeyProperty(kind='Service', repeated=True)
	sPackSentinel = ndb.ComputedProperty(lambda self: len(self.sPack) == 0)
	sDisp = ndb.KeyProperty(kind='Service', repeated=True)
	sDispSentinel = ndb.ComputedProperty(lambda self: len(self.sDisp) == 0)
	sSLA = ndb.KeyProperty(kind='Service', repeated=True)
	sSLASentinel = ndb.ComputedProperty(lambda self: len(self.sSLA) == 0)
	sites = ndb.StringProperty(repeated=True)
	properties = ndb.KeyProperty(kind='Property', repeated=True)
