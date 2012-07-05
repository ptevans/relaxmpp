
======
Pubsub
======

Relaxmpp currently supports create, read, update, delete, and list operations.

Authentication and Authorization
================================

Relaxmpp delegates authentication and authorization to the chat server that
controls the resources being manipulated. You must send an HTTP authentication
header with your request which includes the JID and password of an XMPP user
that has the permissions required to perform the specified action on the chat
server.

Relaxmpp uses the information provided in the HTTP authorization header to open
an XMPP connection to the chat server and will return a 401 Not Authorized if
the HTTP authorization header is not found or not properly formed.

List Nodes
==========
Returns a list of nodes on the pubsub service. The config value is left empty
in list responses for performance reasons.

::

 GET /api/<domain>/pubsub

Create a Node
=============

::

 POST /api/<domain>/pubsub/
 {}
 {"node": "node_name"}

Get a Node's Configuration
==========================

::

 GET /api/<domain>/pubsub/<node>

Update a Node's Configuration
=============================
Update operations are partial or full. Include as much or as little of the JSON
received in the GET request as you like. Updates are all or nothing. If you try
to set a value, for example max_items, to something larger than the max value
the XMPP server allows, you should expect the entire update operation to fail.

::

 PUT /api/<domain>/pubsub/<node>
 {"config": {"some_field": {"value": "some_value"}}}

Delete a Node
=============

::

 DELETE /api/<domain>/pubsub/<node>
