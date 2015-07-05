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
	inputKeys_list = ndb.ComputedProperty(lambda self: ",".join(self.inputKeys))

class FullProduct(ndb.Model):
	name = ndb.StringProperty(default="")
	services = ndb.KeyProperty(kind='Service', repeated=True)
	servicesName = ndb.StringProperty(repeated=True)
	product = ndb.KeyProperty(kind='Product')
	dataflow = ndb.StringProperty(default="")
	account = ndb.StringProperty(default="")
	servicesName_list = ndb.ComputedProperty(lambda self: ",".join(self.servicesName))

class Product(ndb.Model):
	reference = ndb.StringProperty(default="")
	properties = ndb.KeyProperty(kind='Property', repeated=True)
	inputKeys = ndb.StringProperty(repeated=True)
	orderItem = ndb.StringProperty(default="")
	dataflow = ndb.StringProperty(default="")
	account = ndb.StringProperty(default="")
	inputKeys_list = ndb.ComputedProperty(lambda self: ",".join(self.inputKeys))

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
	dataflow = ndb.StringProperty(default="")
	account = ndb.StringProperty(default="")
	sites = ndb.StringProperty(repeated=True)
	properties = ndb.KeyProperty(kind='Property', repeated=True)
	services = ndb.KeyProperty(kind='Service', repeated=True)
