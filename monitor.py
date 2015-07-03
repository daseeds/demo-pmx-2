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
   	def get(self):

		processes = Process.query().fetch()
   		template_values = {
			'processes': processes,

		}
		return self.render_response('processes.html', **template_values)
	def post(self):

		if self.request.get("reference"):
			process = Process(reference=self.request.get("reference"))
			process.put()
		else:
			process = ndb.Key(Process, int(self.request.get("process_id")))
			process.delete()
		self.redirect('/processes')

class ProcessPage(BaseHandler):
   	def get(self, process_id):

		process = Process.get_by_id(int(process_id))

		electrical_list = self.getKeyList(Service.query(Service.stype == "Electrical").fetch())
		graphical_list = self.getKeyList(Service.query(Service.stype == "Graphical").fetch())
		carrier_list = self.getKeyList(Service.query(Service.stype == "Carrier").fetch())
		packaging_list = self.getKeyList(Service.query(Service.stype == "Packaging").fetch())
		dispatch_list = self.getKeyList(Service.query(Service.stype == "Dispatch").fetch())
		SLA_list = self.getKeyList(Service.query(Service.stype == "SLA").fetch())


   		template_values = {
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

	def post(self, process_id):

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

		self.redirect('/{0}/{1}/settingsMapServicesKeys'.format(account_id, dataflow_id))


class SettingsPage(BaseHandler):
   	def get(self, account_id, dataflow_id):

   		template_values = {
			'account_id': account_id,
			'dataflow_id': dataflow_id,
		}
		return self.render_response('settings.html', **template_values)


class ProductsPage(BaseHandler):
   	def get(self, account_id, dataflow_id):

		products = Product.query().fetch()
   		template_values = {
			'products': products,
			'account_id': account_id,
			'dataflow_id': dataflow_id,
		}
		return self.render_response('products.html', **template_values)
	def post(self):

		if self.request.get("reference"):
			product = Product(reference=self.request.get("reference"))
			product.put()
		else:
			product = ndb.Key(Product, int(self.request.get("process_id")))
			product.delete()
		self.redirect('/products')

class ProductPage(BaseHandler):
   	def get(self, product_id):

		product = Product.get_by_id(int(product_id))


   		template_values = {
			'product': product,
			'site_list': site_list,
			'propertyKind': propertyKind,
		}
		return self.render_response('product.html', **template_values)

	def post(self, product_id):

		product = Product.get_by_id(int(product_id))

		if self.request.get("type") == "properties":
			prop = Property(site=self.request.get("site"),
							name=self.request.get("name"),
							value=self.request.get("value"),
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


class indusServices(BaseHandler):
   	def get(self, account_id, dataflow_id):

		services = Service.query(Service.account == account_id,
								 Service.dataflow == dataflow_id).order(Service.stype).fetch()

		typeList = []
		dataflow = Dataflow.query(Dataflow.reference == dataflow_id).fetch()[0]
		for serviceType in dataflow.serviceTypes:
			typeList.append(serviceType.get().name)


   		template_values = {
			'services': services,
			'typeList': typeList,
			'account_id': account_id,
			'dataflow_id': dataflow_id,
		}
		return self.render_response('services.html', **template_values)
	def post(self, account_id, dataflow_id):

		if self.request.get("reference"):
			service = Service(reference=self.request.get("reference"),
							  stype=self.request.get("stype"),
							  account = account_id,
							  dataflow = dataflow_id)
			service.put()
		else:
			service = ndb.Key(Service, int(self.request.get("process_id")))
			service.delete()
		self.redirect('/{0}/{1}/indusServices'.format(account_id, dataflow_id))

class indusServicesKeyMap(BaseHandler):
   	def get(self, account_id, dataflow_id):

		services = Service.query(Service.account == account_id,
								 Service.dataflow == dataflow_id).order(Service.stype).fetch()
		dataflow = Dataflow.query(Dataflow.reference == dataflow_id,
								  Dataflow.account == account_id).fetch()[0]


   		template_values = {
			'services': services,
			'account_id': account_id,
			'dataflow_id': dataflow_id,
			'inputKeys': dataflow.inputKeys,

		}
		return self.render_response('indusServicesKeyMap.html', **template_values)
	def post(self, account_id, dataflow_id):

		services = Service.query(Service.account == account_id,
								 Service.dataflow == dataflow_id).order(Service.stype).fetch()
		dataflow = Dataflow.query(Dataflow.reference == dataflow_id,
								  Dataflow.account == account_id).fetch()[0]

		for service in services:
			service.inputKeys = []
			for inputKey in dataflow.inputKeys:
				service.inputKeys.append(self.request.get("{0}-{1}".format(service.reference, inputKey)))

			service.put()

		self.redirect('/{0}/{1}/indusServicesKeyMap'.format(account_id, dataflow_id))


class ServicePage(BaseHandler):
   	def get(self, service_id):

		service = Service.get_by_id(int(service_id))


   		template_values = {
			'service': service,
			'site_list': site_list,
			'propertyKind': propertyKind,

		}
		return self.render_response('service.html', **template_values)

	def post(self, service_id):

		service = Service.get_by_id(int(service_id))

		if self.request.get("type") == "properties":
			prop = Property(site=self.request.get("site"),
							name=self.request.get("name"),
							value=self.request.get("value"),
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



		self.redirect('/services/{0}'.format(unicode(service_id)))


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
		self.redirect('/dashboard')

class fillDB(BaseHandler):
   	def get(self):

		logging.info("re populate DB..")

		Account(reference='NATIXIS').put()
		Dataflow(reference='CNCE CARD', account='NATIXIS').put()


		self.redirect('/dashboard')




application = webapp2.WSGIApplication([
    webapp2.Route(r'/', MainPage),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>', Dashboard),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/indusServices', indusServices),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/indusServicesKeyMap', indusServicesKeyMap),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/products', ProductsPage),
	webapp2.Route(r'/products/<product_id:([^/]+)?>', ProductPage),
	webapp2.Route(r'/processes', ProcessesPage),
	webapp2.Route(r'/processes/<process_id:([^/]+)?>', ProcessPage),
	webapp2.Route(r'/<account_id:([^/]+)?>/<dataflow_id:([^/]+)?>/settings', SettingsPage),
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
