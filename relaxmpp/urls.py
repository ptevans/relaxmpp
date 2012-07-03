from django.conf.urls import patterns, include
from relaxmpp.pubsub import PubsubResource

pubsub_resource = PubsubResource()

urlpatterns = patterns('',
    (r'^api/(?P<domain>[\w\.]+)/', include(pubsub_resource.urls)),
)
