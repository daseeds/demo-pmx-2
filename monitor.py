#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import urllib
import logging
import webapp2
import datetime
import random
from  models import *

from webapp2_extras.routes import RedirectRoute
from webapp2_extras import jinja2

#from models import Locale, Page, Menu, Picture
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import mail
from google.appengine.api import memcache

accountList = ["NATIXIS", "LA CAIXA", "CITIBANK CANADA"]

HTTP_DATE_FMT = "%a, %d %b %Y %H:%M:%S GMT"

def jinja2_factory(app):
	j = jinja2.Jinja2(app)
	j.environment.filters.update({
        #'naturaldelta':naturaldelta,
        })
	j.environment.globals.update({
        # 'Post': Post,
        #'ndb': ndb, # could be used for ndb.OR in templates
        })
	return j

class BaseHandler(webapp2.RequestHandler):
	@webapp2.cached_property
	def jinja2(self):
	# Returns a Jinja2 renderer cached in the app registry.
		return jinja2.get_jinja2(factory=jinja2_factory)

	def render_response(self, _template, **context):
		# Renders a template and writes the result to the response.
		rv = self.jinja2.render_template(_template, **context)
		self.response.write(rv)
	# def handle_exception(self, exception, debug):
	# 	# Log the error.
	# 	logging.exception(exception)
	# 	# Set a custom message.
	# 	self.response.write("An error occurred.")
	# 	# If the exception is a HTTPException, use its error code.
	# 	# Otherwise use a generic 500 error code.
	# 	if isinstance(exception, webapp2.HTTPException):
	# 		self.response.set_status(exception.code)
	# 	else:
	# 		self.response.set_status(500)
	def render_error(self, message):
		logging.exception("Error 500: {0}".format(message))
		self.response.write("Error 500: {0}".format(message))
		return self.response.set_status(500)
	def getKeyList(self, services):
		list = []
		for service in services:
			for key in service.inputKeys:
				item = dict()
				item['value'] = key
				item['text'] = key + " " + service.reference
				list.append(item)
		return list

	def getMatrixByFullProductId(self, account, dataflow, fullProduct_Id):
		matrix = dict()

		fullProduct = FullProduct.get_by_id(int(fullProduct_Id))

		keys = []
		keys.extend(fullProduct.services)
		keys.append(fullProduct.product)

		logging.info(keys)

		matrix['consumables'] = Property.query(Property.kind=="Consumable",
											Property.account==account,
											Property.dataflow==dataflow,
									 	     Property.parent.IN(keys)).fetch()

		logging.info(matrix['consumables'])

		return matrix

	def getMatrix(self,
				product_key,
				electrical_key,
				graphical_key,
				carrier_key,
				packaging_key,
				dispatch_key,
				SLA_key,
				site_key=""):

		keys = []

		logging.info(electrical_key)
		matrix = dict()
		if (product_key):
			matrix['product'] = Product.query(Product.inputKeys == product_key).fetch()
			if len(matrix['product']) > 0:
				matrix['product'] = matrix['product'][0]
				keys.append(matrix['product'].key)
		if (electrical_key):
			matrix['electrical'] = Service.query(Service.inputKeys == electrical_key).fetch()
			if len(matrix['electrical']) > 0:
				matrix['electrical'] = matrix['electrical'][0]
				keys.append(matrix['electrical'].key)
		if (graphical_key):
			matrix['graphical'] = Service.query(Service.inputKeys == graphical_key).fetch()
			if len(matrix['graphical']) > 0:
				matrix['graphical'] = matrix['graphical'][0]
				keys.append(matrix['graphical'].key)
		if (carrier_key):
			matrix['carrier'] = Service.query(Service.inputKeys == carrier_key).fetch()
			if len(matrix['carrier']) > 0:
				matrix['carrier'] = matrix['carrier'][0]
				keys.append(matrix['carrier'].key)
		matrix['packaging'] = Service(reference="dummy")
		if (packaging_key):
			matrix['packaging'] = Service.query(Service.inputKeys == packaging_key).fetch()
			if len(matrix['packaging']) > 0:
				matrix['packaging'] = matrix['packaging'][0]
				keys.append(matrix['packaging'].key)

		matrix['dispatch'] = Service(reference="dummy")
		if (dispatch_key):
			matrix['dispatch'] = Service.query(Service.inputKeys == dispatch_key).fetch()
			if len(matrix['dispatch']) > 0:
				matrix['dispatch'] = matrix['dispatch'][0]
				keys.append(matrix['dispatch'].key)

		matrix['SLA'] = Service(reference="dummy")
		if (SLA_key):
			matrix['SLA'] = Service.query(Service.inputKeys == SLA_key).fetch()
			if len(matrix['SLA']) > 0:
				matrix['SLA'] = matrix['SLA'][0]
				keys.append(matrix['SLA'].key)


		processes  = []
		allProcesses = Process.query().fetch()


		for process in allProcesses:
			if (matrix['electrical'].key in process.sElec or process.sElecSentinel == True) and (matrix['graphical'].key in process.sGraph or process.sGraphSentinel == True) and (matrix['carrier'].key in process.sCarrier or process.sGraphSentinel == True) and (matrix['packaging'].key in process.sPack or process.sPackSentinel == True) and (matrix['dispatch'].key in process.sDisp or process.sDispSentinel == True) and (matrix['SLA'].key in process.sSLA or process.sSLASentinel == True):
				processes.append(process)


		#ndb.AND(Process.services == matrix['electrical'].key,
		#								Process.services == matrix['graphical'].key,
		#								Process.services == matrix['carrier'].key)).fetch())

		matrix['processes'] = processes

		matrix['instrumentation'] = Property.query(Property.kind=="Instrumentation",
												Property.parent.IN(keys)).fetch()
		matrix['properties'] = Property.query(Property.kind=="Property",
									Property.parent.IN(keys)).fetch()
		matrix['consumable'] = Property.query(Property.kind=="Consumable",
												Property.parent.IN(keys)).fetch()

		matrix['instructions'] = Property.query(Property.kind=="Instruction",
												Property.parent.IN(keys)).fetch()


		logging.info(matrix)

		return matrix

class MainPage(BaseHandler):
   	def get(self):

		dataflows = Dataflow.query().fetch()
   		template_values = {
			'dataflows': dataflows,

		}
		return self.render_response('home.html', **template_values)



class Dashboard(BaseHandler):
   	def get(self, account_id, dataflow_id):

   		template_values = {
			'account_id': account_id,
			'dataflow_id': dataflow_id,

		}
		return self.render_response('dashboard.html', **template_values)

class ProcessesPage(BaseHandler):
   	def get(self, account_id, dataflow_id):

		services = Service.query(Service.account == account_id,
								 Service.dataflow == dataflow_id).order(Service.stype).fetch()
		dataflow = Dataflow.query(Dataflow.reference == dataflow_id,
								  Dataflow.account == account_id).fetch()[0]

		fullProducts = FullProduct.query(FullProduct.dataflow == dataflow_id,
								   FullProduct.account == account_id).fetch()

		products = Product.query(Product.account == account_id,
								Product.dataflow == dataflow_id).fetch()

		processes = Process.query(Process.account == account_id,
								 Process.dataflow == dataflow_id).fetch()

		productList = []
		for product in products:
			productList.append(product.reference)

		serviceTypeList = []
		for serviceType in dataflow.serviceTypes:
			services = Service.query(Service.account == account_id,
								 	 Service.dataflow == dataflow_id,
									 Service.serviceType == serviceType).order(Service.stype).fetch()
			serviceList = []
			for service in services:
				serviceList.append(service.reference)
			serviceTypeList.append(serviceList)

   		template_values = {
			'services': services,
			'account_id': account_id,
			'dataflow_id': dataflow_id,
			'inputKeys': dataflow.inputKeys,
			'serviceTypes': dataflow.serviceTypes,
			'fullProducts': fullProducts,
			'serviceTypeList': serviceTypeList,
			'productList': productList,
			'processes': processes,
		}



		return self.render_response('processes.html', **template_values)
	def post(self, account_id, dataflow_id):

		if self.request.get("reference"):
			process = Process(account = account_id,
							  dataflow = dataflow_id,
							  reference=self.request.get("reference"))
			process.put()


		else:
			process = ndb.Key(Process, int(self.request.get("process_id")))
			process.delete()
		self.redirect('/{0}/{1}/processes'.format(account_id, dataflow_id))

class ProcessPage(BaseHandler):
   	def get(self, account_id, dataflow_id, process_id):

		process = Process.get_by_id(int(process_id))

		electrical_list = self.getKeyList(Service.query(Service.stype == "Electrical").fetch())
		graphical_list = self.getKeyList(Service.query(Service.stype == "Graphical").fetch())
		carrier_list = self.getKeyList(Service.query(Service.stype == "Carrier").fetch())
		packaging_list = self.getKeyList(Service.query(Service.stype == "Packaging").fetch())
		dispatch_list = self.getKeyList(Service.query(Service.stype == "Dispatch").fetch())
		SLA_list = self.getKeyList(Service.query(Service.stype == "SLA").fetch())


   		template_values = {
			'account_id': account_id,
			'dataflow_id': dataflow_id,
			'process': process,
			'site_list': site_list,
			'propertyKind': propertyKind,
			'electrical_list': electrical_list,
			'graphical_list': graphical_list,
			'carrier_list': carrier_list,
			'packaging_list': packaging_list,
			'dispatch_list': dispatch_list,
			'SLA_list': SLA_list,
		}
		return self.render_response('process.html', **template_values)

	def post(self, account_id, dataflow_id, process_id):

		process = Process.get_by_id(int(process_id))

		if self.request.get("type") == "properties":
			prop = Property(site=self.request.get("site"),
							name=self.request.get("name"),
							value=self.request.get("value"),
							kind=self.request.get("kind"))
			prop.parent = process.key
			prop.put()
			process.properties.append(ndb.Key(Property, prop.key.id()))
			process.put()

		if self.request.get("type") == "addSite":
			process.sites.append(self.request.get("site"))
			process.put()

		if self.request.get("type") == "addServices":
			if self.request.get("electrical_key"):
				service = Service.query(Service.inputKeys == self.request.get("electrical_key")).fetch()
				process.sElec.append(service[0].key)
			if self.request.get("graphical_key"):
				service = Service.query(Service.inputKeys == self.request.get("graphical_key")).fetch()
				process.sGraph.append(service[0].key)
			if self.request.get("carrier_key"):
				service = Service.query(Service.inputKeys == self.request.get("carrier_key")).fetch()
				process.sCarrier.append(service[0].key)
			if self.request.get("packaging_key"):
				service = Service.query(Service.inputKeys == self.request.get("packaging_key")).fetch()
				process.sPack.append(service[0].key)
			if self.request.get("dispatch_key"):
				service = Service.query(Service.inputKeys == self.request.get("dispatch_key")).fetch()
				process.sDisp.append(service[0].key)
			if self.request.get("SLA_key"):
				service = Service.query(Service.inputKeys == self.request.get("SLA_key")).fetch()
				process.sSLA.append(service[0].key)
			process.put()

		if self.request.get("type") == "deleteProperty":
			prop = ndb.Key(Property, int(self.request.get("id")))
			process.properties.remove(prop)
			process.put()
			prop.delete()

		if self.request.get("type") == "deleteSite":
			process.sites.remove(self.request.get("id"))
			process.put()

		if self.request.get("type") == "deleteService":
			service = ndb.Key(Service, int(self.request.get("id")))
			if self.request.get("stype") == "Electrical":
				process.sElec.remove(service)
			if self.request.get("stype") == "Graphical":
				process.sGraph.remove(service)
			if self.request.get("stype") == "Carrier":
				process.sCarrier.remove(service)
			if self.request.get("stype") == "Packaging":
				process.sPack.remove(service)
			if self.request.get("stype") == "Dispatch":
				process.sDisp.remove(service)
			if self.request.get("stype") == "SLA":
				process.sSLA.remove(service)
			process.put()

		self.redirect('/processes/{0}'.format(unicode(process_id)))

class SettingsServiceTypesPage(BaseHandler):
   	def get(self, account_id, dataflow_id):

		dataflow = Dataflow.query(Dataflow.reference == dataflow_id).fetch()[0]
   		template_values = {
			'account_id': account_id,
			'dataflow_id': dataflow_id,
			'serviceTypes': dataflow.serviceTypes
		}
		return self.render_response('servicetypes.html', **template_values)
	def post(self, account_id, dataflow_id):

		if self.request.get("reference"):
			dataflow = Dataflow.query(Dataflow.reference == dataflow_id).fetch()[0]
			serviceType = ServiceType(name=self.request.get("reference"),
							dataflow=dataflow_id,
							account=account_id,
							parent = dataflow.key)
			serviceType.put()
			dataflow.serviceTypes.append(ndb.Key(ServiceType, serviceType.key.id()))
			dataflow.put()
		else:
			serviceType = ndb.Key(ServiceType, int(self.request.get("id")))
			dataflow = Dataflow.query(Dataflow.reference == dataflow_id).fetch()[0]
			dataflow.serviceTypes.remove(serviceType)
			dataflow.put()
			serviceType.delete()

		self.redirect('/{0}/{1}/serviceTypes'.format(account_id, dataflow_id))

class settingsInputKeysPage(BaseHandler):
   	def get(self, account_id, dataflow_id):

		dataflow = Dataflow.query(Dataflow.reference == dataflow_id).fetch()[0]
   		template_values = {
			'account_id': account_id,
			'dataflow_id': dataflow_id,
			'inputKeys': dataflow.inputKeys
		}
		return self.render_response('settingsInputKeys.html', **template_values)
	def post(self, account_id, dataflow_id):

		if self.request.get("reference"):
			dataflow = Dataflow.query(Dataflow.reference == dataflow_id).fetch()[0]
			dataflow.inputKeys.append(self.request.get("reference"))
			dataflow.put()
		else:
			dataflow = Dataflow.query(Dataflow.reference == dataflow_id).fetch()[0]
			dataflow.inputKeys.remove(self.request.get("inputKey"))
			dataflow.put()
		self.redirect('/{0}/{1}/settingsInputKeys'.format(account_id, dataflow_id))



class settingsMapServicesKeys(BaseHandler):
   	def get(self, account_id, dataflow_id):

		dataflow = Dataflow.query(Dataflow.reference == dataflow_id).fetch()[0]

   		template_values = {
			'account_id': account_id,
			'dataflow_id': dataflow_id,
			'inputKeys': dataflow.inputKeys,
			'serviceTypes': dataflow.serviceTypes,
			'productKeysMap': dataflow.productKeysMap
		}
		return self.render_response('settingsMapServicesKeys.html', **template_values)
	def post(self, account_id, dataflow_id):
		dataflow = Dataflow.query(Dataflow.reference == dataflow_id, Dataflow.account == account_id).fetch()[0]

		for serviceType in dataflow.serviceTypes:
			sType = ServiceType.get_by_id(serviceType.id())
			sType.inputKeys = []
			for inputKey in dataflow.inputKeys:
				sType.inputKeys.append(self.request.get("{0}-{1}".format(serviceType.get().name, inputKey)))
			sType.put()

		dataflow.productKeysMap = []
		for inputKey in dataflow.inputKeys:
			dataflow.productKeysMap.append(self.request.get("product-{1}".format(serviceType.get().name, inputKey)))
		dataflow.put()


		self.redirect('/{0}/{1}/settingsMapServicesKeys'.format(account_id, dataflow_id))


class SettingsPage(BaseHandler):
   	def get(self):

		dataflows = Dataflow.query().fetch()
		accounts = Account.query().fetch()

		accountList = []
		for account in accounts:
			accountList.append(account.reference)

   		template_values = {
			'dataflows': dataflows,
			'accounts': accounts,
			'accountList': accountList,
		}
		return self.render_response('settings.html', **template_values)

	def post(self):

		if self.request.get("type") == 'account':
			account = Account(reference = self.request.get("account"))
			account.put()

		if self.request.get("type") == 'dataflow':
			dataflow = Dataflow(account = self.request.get("account"),
								reference = self.request.get("dataflow"))
			dataflow.put()

		self.redirect('/settings')

class ProductsPage(BaseHandler):
   	def get(self, account_id, dataflow_id):

		products = Product.query(Product.account == account_id,
						Product.dataflow == dataflow_id).fetch()
   		template_values = {
			'products': products,
			'account_id': account_id,
			'dataflow_id': dataflow_id,
		}
		return self.render_response('products.html', **template_values)
	def post(self, account_id, dataflow_id):

		if self.request.get("reference"):
			product = Product(account = account_id,
							  dataflow = dataflow_id,
							  reference=self.request.get("reference"),
							  orderItem = self.request.get("orderItem"))
			product.put()
		else:
			product = ndb.Key(Product, int(self.request.get("process_id")))
			product.delete()
		self.redirect('/{0}/{1}/products'.format(account_id, dataflow_id))

class ProductPage(BaseHandler):
   	def get(self, account_id, dataflow_id, product_id):

		product = Product.get_by_id(int(product_id))


   		template_values = {
			'product': product,
			'site_list': site_list,
			'propertyKind': propertyKind,
			'account_id': account_id,
			'dataflow_id': dataflow_id,
		}
		return self.render_response('product.html', **template_values)

	def post(self, account_id, dataflow_id, product_id):

		product = Product.get_by_id(int(product_id))

		if self.request.get("type") == "properties":
			prop = Property(site=self.request.get("site"),
							name=self.request.get("name"),
							value=self.request.get("value"),
							account = account_id,
							dataflow = dataflow_id,
							kind=self.request.get("kind"))
			prop.parent = product.key
			prop.put()
			product.properties.append(ndb.Key(Property, prop.key.id()))
			product.put()

		if self.request.get("type") == "inputKeys":
			product.inputKeys.append(self.request.get("value"))
			product.put()

		if self.request.get("type") == "deleteProperty":
			prop = ndb.Key(Property, int(self.request.get("id")))
			product.properties.remove(prop)
			product.put()
			prop.delete()

		if self.request.get("type") == "deleteInputKey":
			product.inputKeys.remove(self.request.get("id"))
			product.put()

		self.redirect('/products/{0}'.format(unicode(product_id)))


class services(BaseHandler):
   	def get(self, account_id, dataflow_id):

		services = Service.query(Service.account == account_id,
								 Service.dataflow == dataflow_id,
								 Service.domain == self.request.get("domain")).order(Service.stype).fetch()

		typeList = []
		dataflow = Dataflow.query(Dataflow.reference == dataflow_id).fetch()[0]
		for serviceType in dataflow.serviceTypes:
			typeList.append(serviceType.get().name)

   		template_values = {
			'services': services,
			'typeList': typeList,
			'account_id': account_id,
			'dataflow_id': dataflow_id,
			'domain': self.request.get("domain"),
		}
		return self.render_response('services.html', **template_values)
	def post(self, account_id, dataflow_id):

		if self.request.get("reference"):
			service = Service(reference=self.request.get("reference"),
							  stype=self.request.get("stype"),
							  account = account_id,
							  dataflow = dataflow_id,
							  domain = self.request.get("domain"))
			serviceType = ServiceType.query(ServiceType.account == account_id,
											ServiceType.dataflow == dataflow_id,
											ServiceType.name == self.request.get("stype")).fetch()[0]
			service.serviceType = serviceType.key
			service.put()
		else:
			service = ndb.Key(Service, int(self.request.get("process_id")))
			service.delete()
		self.redirect('/{0}/{1}/services?domain={2}'.format(account_id, dataflow_id, self.request.get("domain") ))

class servicesKeyMap(BaseHandler):
   	def get(self, account_id, dataflow_id):

		services = Service.query(Service.account == account_id,
								 Service.dataflow == dataflow_id).order(Service.stype).fetch()
		dataflow = Dataflow.query(Dataflow.reference == dataflow_id,
								  Dataflow.account == account_id).fetch()[0]

		products = Product.query(Product.account == account_id,
								 Product.dataflow == dataflow_id).fetch()


   		template_values = {
			'services': services,
			'account_id': account_id,
			'dataflow_id': dataflow_id,
			'inputKeys': dataflow.inputKeys,
			'serviceTypes': dataflow.serviceTypes,
			'products': products,
			'productKeysMap': dataflow.productKeysMap
		}
		return self.render_response('servicesKeyMap.html', **template_values)
	def post(self, account_id, dataflow_id):

		services = Service.query(Service.account == account_id,
								 Service.dataflow == dataflow_id).order(Service.stype).fetch()
		dataflow = Dataflow.query(Dataflow.reference == dataflow_id,
								  Dataflow.account == account_id).fetch()[0]

		products = Product.query(Product.account == account_id,
								 Product.dataflow == dataflow_id).fetch()

		for service in services:
			service.inputKeys = []
			for inputKey in dataflow.inputKeys:
				service.inputKeys.append(self.request.get("{0}-{1}".format(service.reference, inputKey)))
			service.put()

		for product in products:
			product.inputKeys = []
			for inputKey in dataflow.inputKeys:
				product.inputKeys.append(self.request.get("{0}-{1}".format(product.reference, inputKey)))
			product.put()

		self.redirect('/{0}/{1}/servicesKeyMap'.format(account_id, dataflow_id))


class service(BaseHandler):
   	def get(self, account_id, dataflow_id,service_id):

		service = Service.get_by_id(int(service_id))


   		template_values = {
			'service': service,
			'site_list': site_list,
			'account_id': account_id,
			'dataflow_id': dataflow_id,
			'propertyKind': propertyKind,

		}
		return self.render_response('service.html', **template_values)

	def post(self, account_id, dataflow_id,service_id):

		service = Service.get_by_id(int(service_id))

		if self.request.get("type") == "properties":
			prop = Property(site=self.request.get("site"),
							name=self.request.get("name"),
							value=self.request.get("value"),
							account = account_id,
							dataflow = dataflow_id,
							kind=self.request.get("kind"))
			prop.parent = service.key
			prop.put()
			service.properties.append(ndb.Key(Property, prop.key.id()))
			service.put()

		if self.request.get("type") == "inputKeys":
			service.inputKeys.append(self.request.get("value"))
			service.put()

		if self.request.get("type") == "deleteProperty":
			prop = ndb.Key(Property, int(self.request.get("id")))
			service.properties.remove(prop)
			service.put()
			prop.delete()

		if self.request.get("type") == "deleteInputKey":
			service.inputKeys.remove(self.request.get("id"))
			service.put()

		self.redirect('/{0}/{1}/services/{2}'.format(account_id, dataflow_id, unicode(service_id)))

class matrix(BaseHandler):
   	def get(self, account_id, dataflow_id):

		services = Service.query(Service.account == account_id,
								 Service.dataflow == dataflow_id).order(Service.stype).fetch()
		dataflow = Dataflow.query(Dataflow.reference == dataflow_id,
								  Dataflow.account == account_id).fetch()[0]

		fullProducts = FullProduct.query(FullProduct.dataflow == dataflow_id,
								   FullProduct.account == account_id).fetch()

		products = Product.query(Product.account == account_id,
								Product.dataflow == dataflow_id).fetch()

		productList = []
		for product in products:
			productList.append(product.reference)

		serviceTypeList = []
		for serviceType in dataflow.serviceTypes:
			services = Service.query(Service.account == account_id,
								 	 Service.dataflow == dataflow_id,
									 Service.serviceType == serviceType).order(Service.stype).fetch()
			serviceList = []
			for service in services:
				serviceList.append(service.reference)
			serviceTypeList.append(serviceList)

   		template_values = {
			'services': services,
			'account_id': account_id,
			'dataflow_id': dataflow_id,
			'inputKeys': dataflow.inputKeys,
			'serviceTypes': dataflow.serviceTypes,
			'fullProducts': fullProducts,
			'serviceTypeList': serviceTypeList,
			'productList': productList,
		}
		return self.render_response('matrix.html', **template_values)
	def post(self, account_id, dataflow_id):

		if self.request.get("action") == 'add':
			fullProduct = FullProduct(account = account_id,
									  dataflow = dataflow_id,
									  name = self.request.get("name"))

			dataflow = Dataflow.query(Dataflow.reference == dataflow_id,
										  Dataflow.account == account_id).fetch()[0]

			for serviceType in dataflow.serviceTypes:
				service = Service.query(Service.account == account_id,
									 	 Service.dataflow == dataflow_id,
										 Service.reference == self.request.get(serviceType.get().name)).order(Service.stype).fetch()[0]
				fullProduct.services.append(ndb.Key(Service, service.key.id()))
				fullProduct.servicesName.append(service.reference)

			product = Product.query(Product.account == account_id,
									Product.dataflow == dataflow_id,
									Product.reference == self.request.get('product')).fetch()[0]

			fullProduct.product = product.key
			fullProduct.put()

		if self.request.get("action") == 'delete':
			fullProduct = ndb.Key(FullProduct, int(self.request.get("fullProduct_id")))
			fullProduct.delete()

		self.redirect('/{0}/{1}/matrix'.format(account_id, dataflow_id))

class keysSimul(BaseHandler):
   	def get(self, account_id, dataflow_id):

		dataflow = Dataflow.query(Dataflow.reference == dataflow_id,
								  Dataflow.account == account_id).fetch()[0]

		fullProduct = None
		keyDict = None
		newfullProduct = None
		message=""
		messageType=""
		if self.request.get('action') == 'exec':

			services = Service.query(Service.account == account_id,
									 Service.dataflow == dataflow_id).order(Service.stype).fetch()


			fullProducts = FullProduct.query(FullProduct.dataflow == dataflow_id,
									   FullProduct.account == account_id).fetch()

			products = Product.query(Product.account == account_id,
									Product.dataflow == dataflow_id).fetch()

			keyDict = dict()
			for inputKey in dataflow.inputKeys:
				keyDict[inputKey] = self.request.get(inputKey)

			serviceList=[]
			serviceNdbList=[]

			allElementsAvailabe = 1
			for serviceType in dataflow.serviceTypes:
				list = []
				i = 0
				logging.info(serviceType.get().name)
				for inputKey in serviceType.get().inputKeys:
					if inputKey == 'on':
						logging.info(dataflow.inputKeys[i] + '=' +self.request.get(dataflow.inputKeys[i]))
						list.append(self.request.get(dataflow.inputKeys[i]))
					else:
						list.append("")
					i = i + 1
				logging.info(list)
				service = Service.query(Service.account == account_id,
									    Service.dataflow == dataflow_id,
										Service.inputKeys_list==",".join(list),
										Service.stype == serviceType.get().name).fetch()
				if service:
					logging.info(service[0])
					serviceList.append(service[0].reference)
					serviceNdbList.append(service[0].key)
				else:
					messageType = "danger"
					message += "No service found for type " + serviceType.get().name +"<br> "
					allElementsAvailabe = 0

			list = []
			i = 0
			logging.info('product')
			for inputKey in dataflow.productKeysMap:
				if inputKey == 'on':
					logging.info(dataflow.inputKeys[i] + '=' +self.request.get(dataflow.inputKeys[i]))
					list.append(self.request.get(dataflow.inputKeys[i]))
				else:
					list.append("")
				i = i + 1
			logging.info(list)

			products = Product.query(Product.account == account_id,
								Product.dataflow == dataflow_id,
								Product.inputKeys_list==",".join(list)).fetch()
			if products:
				product = products[0]
				logging.info(product)
			else:
				messageType = "danger"
				message += "No product found <br> "
				allElementsAvailabe = 0


			logging.info(serviceList)
			fullProducts = FullProduct.query(FullProduct.dataflow == dataflow_id,
									   FullProduct.account == account_id,
										FullProduct.servicesName_list==",".join(serviceList),
										FullProduct.product == product.key).fetch()

			if allElementsAvailabe == 1:

				if fullProducts:
					fullProduct = fullProducts[0]
					logging.info(fullProduct)
					messageType = "success"
					message = "This full product exists in the matrix"
				else:
					newfullProduct = dict()
					newfullProduct['services'] = []
					newfullProduct['services'].extend(serviceNdbList)
					newfullProduct['product'] = product.key
					logging.info(newfullProduct)
					messageType = "warning"
					message = "Key to service map OK, but full product not in matrix"


		logging.info(message)
   		template_values = {
			'account_id': account_id,
			'dataflow_id': dataflow_id,
			'inputKeys': dataflow.inputKeys,
			'fullProduct': fullProduct,
			'serviceTypes': dataflow.serviceTypes,
			'message': message,
			'keyDict': keyDict,
			'messageType': messageType,
			'newfullProduct': newfullProduct,
		}
		return self.render_response('keysSimul.html', **template_values)
	def post(self, account_id, dataflow_id):

		if self.request.get("action") == 'add':
			fullProduct = FullProduct(account = account_id,
									dataflow = dataflow_id,
									name = self.request.get("name"))

			dataflow = Dataflow.query(Dataflow.reference == dataflow_id,
										Dataflow.account == account_id).fetch()[0]

			for serviceType in dataflow.serviceTypes:
				service = Service.query(Service.account == account_id,
										Service.dataflow == dataflow_id,
										Service.reference == self.request.get(serviceType.get().name)).order(Service.stype).fetch()[0]
				fullProduct.services.append(ndb.Key(Service, service.key.id()))
				fullProduct.servicesName.append(service.reference)

			product = Product.query(Product.account == account_id,
									Product.dataflow == dataflow_id,
									Product.reference == self.request.get('product')).fetch()[0]

			fullProduct.product = product.key
			fullProduct.put()

		if self.request.get("action") == 'delete':
			fullProduct = ndb.Key(FullProduct, int(self.request.get("fullProduct_id")))
			fullProduct.delete()

		self.redirect('/{0}/{1}/keysSimul'.format(account_id, dataflow_id))

class fullproduct(BaseHandler):
	def get(self, account_id, dataflow_id, fullproduct_id):
		matrix = self.getMatrixByFullProductId(account_id, dataflow_id, fullproduct_id)


   		template_values = {
			'consumables': matrix['consumables'],
			'account_id': account_id,
			'dataflow_id': dataflow_id,
		}

		return self.render_response('fullproduct.html', **template_values)


class TestPage(BaseHandler):
	def get(self):

		product_list = self.getKeyList(Product.query().fetch())
		electrical_list = self.getKeyList(Service.query(Service.stype == "Electrical").fetch())
		graphical_list = self.getKeyList(Service.query(Service.stype == "Graphical").fetch())
		carrier_list = self.getKeyList(Service.query(Service.stype == "Carrier").fetch())
		packaging_list = self.getKeyList(Service.query(Service.stype == "Packaging").fetch())
		dispatch_list = self.getKeyList(Service.query(Service.stype == "Dispatch").fetch())
		SLA_list = self.getKeyList(Service.query(Service.stype == "SLA").fetch())

   		template_values = {
			'product_list': product_list,
			'electrical_list': electrical_list,
			'graphical_list': graphical_list,
			'carrier_list': carrier_list,
			'packaging_list': packaging_list,
			'dispatch_list': dispatch_list,
			'site_list': site_list,
			'SLA_list': SLA_list,
		}
		return self.render_response('test.html', **template_values)

class getInterfaceFromKeys(BaseHandler):
	def get(self):

		p = []

		p.append(self.getMatrix(self.request.get('product_key_p1'),
					   self.request.get('electrical_key_p1'),
					   self.request.get('graphical_key_p1'),
					self.request.get('carrier_key_p1'),
					self.request.get('packaging_key_p1'),
					self.request.get('dispatch_key_p1'),
					self.request.get('SLA_key_p1')))

		p.append(self.getMatrix(self.request.get('product_key_p2'),
					   self.request.get('electrical_key_p2'),
					   self.request.get('graphical_key_p2'),
					self.request.get('carrier_key_p2'),
					self.request.get('packaging_key_p2'),
					self.request.get('dispatch_key_p2'),
					self.request.get('SLA_key_p2')))

		return self.render_response('interface.html', **template_values)


class getJifFromKeys(BaseHandler):
	def get(self):

		m = self.getMatrix(self.request.get('product_key'),
					   self.request.get('electrical_key'),
					   self.request.get('graphical_key'),
					self.request.get('carrier_key'),
					self.request.get('packaging_key'),
					self.request.get('dispatch_key'),
					self.request.get('SLA_key'))


		operations = []
		implemented = []

		for process in m['processes']:
			process.services = []
			if m['electrical'] in process.sElec:
				process.services.append(m['electrical'])
			if m['graphical'] in process.sGraph:
				process.services.append(m['graphical'])
			if m['carrier'] in process.sCarrier:
				process.services.append(m['carrier'])
			if m['packaging'] in process.sPack:
				process.services.append(m['packaging'])
			if m['dispatch'] in process.sDisp:
				process.services.append(m['dispatch'])
			if m['SLA'] in process.sSLA:
				process.services.append(m['SLA'])

		i=0
		# Electrical
		process = self.getProcessFromElecService(m['electrical'], m)
		operation = dict()
		if process:
			operation['process'] = process
			operation['services'] = self.getServicesFromProcess(process, m)
			for item in operation['services']:
				implemented.append(item)
		else:
			operation['No Process'] = "No process for this service"
			implemented.append(m['electrical'])
		operations.append(operation)

		logging.info(operations)




   		template_values = {
			'processes': m['processes'],
			'product': m['product'],
			'sercElec': m['electrical'],
			'sercGraph': m['graphical'],
			'sercCarr': m['carrier'],
			'sercPack': m['packaging'],
			'sercDisp': m['dispatch'],
			'sercSLA': m['SLA'],
			'instrumentation': m['instrumentation'],
			'consumable': m['consumable'],
			'properties': m['properties'],
			'instructions': m['instructions'],
			'site': self.request.get('site'),
		}

		return self.render_response('jif.html', **template_values)

	def getProcessFromElecService(self, service, m):
		for process in m['processes']:
			if service in process.sElec:
				return process

	def getServicesFromProcess(self, process, m):
		services = []
		logging.info(process)
		logging.info(m)
		if m['electrical'] in process.sElec:
			services.append(m['electrical'])
		if m['graphical'] in process.sGraph:
			services.append(m['graphical'])
		if m['carrier'] in process.sCarrier:
			services.append(m['carrier'])
		if m['packaging'] in process.sPack:
			services.append(m['packaging'])
		if m['dispatch'] in process.sDisp:
			services.append(m['dispatch'])
		if m['SLA'] in process.sSLA:
			services.append(m['SLA'])
		logging.info(services)
		return services




class deleteDB(BaseHandler):
   	def get(self):

		logging.info("delete DB")
   		ndb.delete_multi(ndb.Query(default_options=ndb.QueryOptions(keys_only=True)))
		self.redirect('/')

class fillDB(BaseHandler):
   	def get(self):

		logging.info("re populate DB..")

		Account(reference='NATIXIS').put()
		Dataflow(reference='CNCE CARD', account='NATIXIS').put()


		self.redirect('/')




application = webapp2.WSGIApplication([
    webapp2.Route(r'/', MainPage),
	webapp2.Route(r'/settings', SettingsPage),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>', Dashboard),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/services', services),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/services/<service_id:([^/]+)?>', service),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/servicesKeyMap', servicesKeyMap),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/products', ProductsPage),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/matrix', matrix),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/matrix/<fullproduct_id:([^/]+)?>', fullproduct),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/products/<product_id:([^/]+)?>', ProductPage),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/processes', ProcessesPage),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/processes/<process_id:([^/]+)?>', ProcessPage),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/keysSimul', keysSimul),

	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/serviceTypes', SettingsServiceTypesPage),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/settingsInputKeys', settingsInputKeysPage),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/settingsMapServicesKeys', settingsMapServicesKeys),
	webapp2.Route(r'/deleteDB', deleteDB),
	webapp2.Route(r'/test', TestPage),
	webapp2.Route(r'/test/getJifFromKeys', getJifFromKeys),
	webapp2.Route(r'/test/getInterfaceFromKeys', getInterfaceFromKeys),
	webapp2.Route(r'/fillDB', fillDB),


#    webapp2.Route(r'/<locale_id:([^/]+)?>/<page_id:([^/]+)?>', ModelViewer),
#    webapp2.Route(r'/<locale_id:([^/]+)?>', LocaleViewer),

	], debug=True)
