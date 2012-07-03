
import base64
import re

from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError
from tastypie import fields
from tastypie.authentication import Authentication
from tastypie.authorization import Authorization
from tastypie.bundle import Bundle
from tastypie.http import HttpUnauthorized
from tastypie.resources import Resource

bot_pool = {}

def get_bot(jid, password, pubsub_address='pubsub'):
    if jid in bot_pool:
        bot = bot_pool.get(jid)
        if password == bot._password:
            return bot
        else:
            return False

    bot = PubsubBot(jid, password, pubsub_address)
    if bot.connect():
        bot.process()
        bot_pool[jid] = bot
        return bot

    return False

class PubsubBot(ClientXMPP):

    def __init__(self, jid, password, pubsub_address='pubsub'):
        super(PubsubBot, self).__init__(jid, password)

        self._jid = jid
        self._password = password

        self._pubsub_address = pubsub_address
        self._domain = jid.split('@')[1].split('/')[0]
        self._pubsub_jid = self._pubsub_address + '.' + self._domain

        self.register_plugin('xep_0004')
        self.register_plugin('xep_0060')

    def get_nodes(self):
        """
        Get a list of pubsub nodes. Returns a list of strings.
        """
        response = self['xep_0060'].get_nodes(self._pubsub_jid)
        raw_nodes = response.get_payload()[0]
        nodes = []
        for node in raw_nodes:
            nodes.append(node.get('node'))
        return nodes

    def get_node(self, node):
        """
        Get the configuration for a single pubsub node

        node (str, unicode)
            The name of the node to lookup
        """
        response = self['xep_0060'].get_node_config(self._pubsub_jid, node=node)

        configuration = {}
        for field in response['pubsub_owner']['configure']['form']['fields'].values():
            field_name = field['var']
            if field_name == "FORM_TYPE" or not field_name:
                continue
            field_name = field_name.split('#')[1]

            configuration[field_name] = {}
            for key in ('label', 'type', 'value', 'var'):
                configuration[field_name][key] = field[key]

            for option in field['options']:
                try:
                    configuration[field_name]['options'].append(option['value'])
                except KeyError:
                    configuration[field_name]['options'] = []
                    configuration[field_name]['options'].append(option['value'])

            configuration[field_name]['value'] = field['value']

        return configuration

    def delete_node(self, node):
        """
        Delete a pubsub node.

        node (str, unicode)
            The name of the node to delete
        """
        response = self['xep_0060'].delete_node(self._pubsub_jid, node,
                                                block=False)

    def create_node(self, node=''):
        """
        Create a pubsub node.

        node (str, unicode) : ''
            The name of the node. The default is an empty string and will
            result in the XMPP server assigning a random name to the node.
        """
        response = self['xep_0060'].create_node(self._pubsub_jid, node)

        #TODO: handle some error cases mayhap?
        return response['pubsub']['create']['node']

    def update_node(self, node, **values):
        """
        Update a node's configuration

        node (str, unicode)
            The name of the node to update

        values
            Field and value pairs corresponding to pubsub node configuration
            fields. If the field names do not start with 'pubsub#', this prefix
            will be prepended.
        """
        print values
        form = self['xep_0004'].make_form(ftype='submit')
        form.add_field('FORM_TYPE', ftype='hidden',
                      value='http://jabber.org/protocol/pubsub#node_config')
        for field, value in values.items():
            if not re.match(r'^pubsub#', field):
               field = 'pubsub#' + field
            print 'Adding field/value:', field, value
            form.addField(field, value=value)

        try:
            self['xep_0060'].set_node_config(self._pubsub_jid, node, form)
        except IqError, e:
            return False
        else:
            return True


class DelegatedAuthentication(Authentication):
    """
    Delegate authentication (and subsequently authorization) to the XMPP
    server that will ultimately service the request. This expects HTTP Basic
    authentication. Authentication is successful if the decoded authorization
    header matches the pattern user@domain (i.e. it is a jid). The username
    and the password are placed into dictionary named "relaxmpp_credentials"
    in the django request object.
    """
    def _unauthorized(self):
        response = HttpUnauthorized()
        response['WWW-Authenticate'] = 'Basic Realm="relaxmpp API"'
        return response

    def is_authenticated(self, request, **kwargs):
        DelegatedAuthentication.credentials = {}
        auth_header = request.META.get('HTTP_AUTHORIZATION', False)
        if not auth_header:
            return self._unauthorized()
        try:
            auth_type, auth_hash = auth_header.split()
        except ValueError:
            return self._unauthorized()
        else:
            if auth_type != 'Basic':
                return self._unauthorized()
            raw_credentials = base64.b64decode(auth_hash)

        try:
            jid, password = raw_credentials.split(':')
        except ValueError:
            return self._unauthorized()
        else:
            if not re.match(r'\w+@[\w\.]+', jid):
                return self._unauthorized()
            request.relaxmpp_credentials = {'jid': jid, 'password': password}
            print id(request)
            print request.relaxmpp_credentials
            return True


class PubsubNode(object):
    """
    The PubsubNode class provides a model for working with pubsub nodes.
    """

    def __init__(self, node=None, domain=None, config={}, connection=None):
        """
        Create a new PubsubNode object.

        node (str, unicode) : None
            The name of the node

        domain (str, unicode) : None
            The XMPP chat domain that this node belong to

        config (dict) : {}
            A dictionary mapping configuration fields to values

        connection (PubsubBot) : None
            The XMPP connection to use
        """
        self.node = node
        self.domain = domain
        self.config = config
        self.connection = connection

    def commit_create(self):
        """
        Create this new pubsub node on the chat server.
        """
        if self.node is None:
            node = self.connection.create_node()
            self.node = node
        else:
            node = self.connection.create_node(node=self.node)
        return self

    def commit_update(self):
        """
        Commit changes to this pubsub node on the chat server.
        """
        config_updates = {}
        for field in self.config:
            config_updates[field] = self.config[field]['value']
        print config_updates
        self.connection.update_node(self.node, **config_updates)

    def commit_delete(self):
        """
        Delete this pubsub node from the chat server.
        """
        self.connection.delete_node(self.node)

    def get_config(self):
        self.config = self.connection.get_node(self.node)
        return self


class PubsubNodeCollection(object):
    """
    A collection of PubsubNode objects
    """

    def __init__(self, domain, connection=None):
        """
        Create a PubsubNodeCollection

        domain (str, unicode) : None
            The XMPP chat domain that these nodes belong to

        connection (PubsubBot) : None
            The XMPP connection to use
        """
        self.domain = domain
        self.connection = connection
        self.nodes = []

        if connection is not None:
            self.get_nodes()

    def get_nodes(self):
        nodes = self.connection.get_nodes()
        for node in nodes:
            self.nodes.append(PubsubNode(node, self.domain))


class PubsubResource(Resource):
    """
    This is the resource definition for Tastypie, mmmm.
    """
    node = fields.CharField(attribute='node')
    domain = fields.CharField(attribute='domain')
    config = fields.DictField(attribute='config')

    class Meta:
        resource_name = 'pubsub'
        object_class = PubsubNode
        authentication = DelegatedAuthentication()
        authorization = Authorization()

    def detail_uri_kwargs(self, bundle_or_obj):
        kwargs = {}

        if isinstance(bundle_or_obj, Bundle):
            kwargs['domain'] = bundle_or_obj.obj.domain
            kwargs['pk'] = bundle_or_obj.obj.node
        else:
            kwargs['domain'] = bundle_or_obj.domain
            kwargs['pk'] = bundle_or_obj.node

        print kwargs
        return kwargs

    def obj_get_list(self, request=None, **kwargs):
        connection = get_bot(**request.relaxmpp_credentials)
        return PubsubNodeCollection(kwargs['domain'], connection=connection).nodes

    def obj_create(self, bundle, request=None, **kwargs):
        bundle = self.full_hydrate(bundle)
        bundle.obj.connection = get_bot(**request.relaxmpp_credentials)
        bundle.obj.commit_create()
        return bundle

    def obj_get(self, request=None, **kwargs):
        domain = kwargs['domain']
        node = kwargs['pk']
        connection = get_bot(**request.relaxmpp_credentials)
        node = PubsubNode(node=node, domain=domain, connection=connection)
        node.get_config()
        return node

    def obj_update(self, bundle, request=None, **kwargs):
        bundle = self.full_hydrate(bundle)
        if kwargs['domain']:
            bundle.obj.domain = kwargs['domain']
        if kwargs['pk']:
            bundle.obj.node = kwargs['pk']
        bundle.obj.connection = get_bot(**request.relaxmpp_credentials)
        bundle.obj.commit_update()

    def obj_delete(self, request=None, **kwargs):
        domain = kwargs['domain']
        node = kwargs['pk']
        connection = get_bot(**request.relaxmpp_credentials)
        obj = PubsubNode(node=node, domain=domain, connection=connection)
        obj.commit_delete()

