
import logging
logging.basicConfig()

import unittest

# A valid and properly configured chat user should be provided via config.py
import config
jid = config.jid
password = config.password

class PubsubBotTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.append('./')

    def setUp(self):
        pass

    def test_01_create_list_delete_nodes(self):
        from relaxmpp.pubsub import PubsubBot

        bot = PubsubBot(jid, password)
        if bot.connect():
            bot.process()

            print '\n - Checking that test node is not registered'
            nodes = bot.get_nodes()
            try:
                self.assertNotIn('node53', nodes)
            except AssertionError:
                print ' - Attempting to delete test node'
                bot.delete_node('node53')
                print '   Confirming deletion'
                nodes = bot.get_nodes()
                self.assertNotIn('node53', nodes)
                print '   Deleted'


            print ' - Attempting to create test node'
            node = bot.create_node('node53')
            self.assertEqual(node, 'node53')
            print '   Confirming the node was added'
            nodes = bot.get_nodes()
            self.assertIn('node53', nodes)

            print '   Test node added'

            print ' - Attempting to delete test node'
            bot.delete_node('node53')
            print '   Confirming deletion'
            nodes = bot.get_nodes()
            self.assertNotIn('node53', nodes)
            print '   Deleted'


            # Let's run through it letting the server generate the name
            node = bot.create_node()
            print node
            nodes = bot.get_nodes()
            self.assertIn(node, nodes)
            bot.delete_node(node)

            print bot.get_nodes()
            bot.disconnect()
        else:
            print 'sad trombone'

    def test_02_get_and_update_node_config(self):
        from relaxmpp.pubsub import PubsubBot

        bot = PubsubBot(jid, password)
        if bot.connect():
            bot.process()

            testnode = 'test1'
            nodes = bot.get_nodes()
            if testnode in nodes:
                bot.delete_node(testnode)
            bot.create_node(node=testnode)

            node_config = bot.get_node(testnode)
            print node_config.get('title')

            wtfbbq = {'pubsub#title': 'Foo bar and baz walk into a bar'}
            bot.update_node(testnode, **wtfbbq)
            node_config = bot.get_node(testnode)
            self.assertEqual(node_config['title']['value'],
                             'Foo bar and baz walk into a bar')

            bot.update_node(testnode, title='Something witty and pithy')
            node_config = bot.get_node(testnode)
            self.assertEqual(node_config['title']['value'],
                             'Something witty and pithy')


            bot.delete_node(testnode)
            bot.disconnect()
