from plone.testing import z2
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import FunctionalTesting

from plone.app.robotframework.remote import RemoteLibraryLayer
from plone.app.robotframework.autologin import AutoLogin
from plone.app.robotframework.content import Content
from plone.app.robotframework.genericsetup import GenericSetup
from plone.app.robotframework.i18n import I18N
from plone.app.robotframework.mailhost import MockMailHost
from plone.app.robotframework.quickinstaller import QuickInstaller
from plone.app.robotframework.server import Zope2ServerRemote
from plone.app.robotframework.users import Users

from collective.beaker.testing import BeakerConfigLayer

from tud.addons.chat.tests import setupCoreSessions
from tud.addons.chat.tests.database import DatabaseHelper

REMOTE_LIBRARY_BUNDLE_FIXTURE = RemoteLibraryLayer(
    bases=(PLONE_FIXTURE,),
    libraries=(AutoLogin, QuickInstaller, GenericSetup,
               Content, Users, I18N, MockMailHost,
               Zope2ServerRemote, DatabaseHelper),
    name="RemoteLibraryBundle:RobotRemote"
)

class TudAddonsChatLayer(BeakerConfigLayer, PloneSandboxLayer):
    """
    This class describes the test layer used for robot tests.
    """

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        """
        Sets up zope.
        This is the most appropriate place to load ZCML or install Zope 2-style products, using the `plone.testing.z2.installProduct` helper.

        :param app: zope application root
        :type app: OFS.Application.Application
        :param configurationContext: zcml configuration context
        :type configurationContext: plone.testing.zca.NamedConfigurationMachine
        """
        z2.installProduct(app, 'Products.ZMySQLDA')

        import tud.addons.chat
        self.loadZCML(package=tud.addons.chat, context=configurationContext)
        z2.installProduct(app, 'tud.addons.chat')

        import jarn.jsi18n
        self.loadZCML(package=jarn.jsi18n, context=configurationContext)
        z2.installProduct(app, 'jarn.jsi18n')

        # Add session to instance
        setupCoreSessions(app)

    def setUpPloneSite(self, portal):
        """
        Sets up the plone site.
        Provided no exception is raised, changes to the given site will be committed.

        :param portal: plone site
        :type portal: Products.CMFPlone.Portal.PloneSite
        """
        self.applyProfile(portal, 'tud.addons.chat.archetypes:archetypes')

    def setUp(self):
        """
        Sets up beaker config layer and plone sandbox layer.
        """
        BeakerConfigLayer.setUp()
        PloneSandboxLayer.setUp(self)

FIXTURE = TudAddonsChatLayer()

ROBOT_TESTING = FunctionalTesting(
    bases=(REMOTE_LIBRARY_BUNDLE_FIXTURE,
           z2.ZSERVER_FIXTURE,
           FIXTURE),
    name="TudAddonsChat:Robot")
