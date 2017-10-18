from zope.component import getUtility
from Products.CMFCore.utils import getToolByName
from plone.registry.interfaces import IRegistry

try:
    from Products.CMFPlone.resources.browser.cook import cookWhenChangingSettings
except ImportError:
    pass

try:
    import jarn.jsi18n
    HAVE_JARN_JSI18N = True
except ImportError:
    HAVE_JARN_JSI18N = False

try:
    import mockup
    HAVE_MOCKUP = True
except ImportError:
    HAVE_MOCKUP = False

def setupVarious(context):
    '''
    Ordinarily, GenericSetup handlers check for the existence of XML files.
    Here, we are not parsing an XML file, but we use a text file as a
    flag to check that we actually meant for this import step to be run.
    The file is found in profiles/default.
    '''

    if context.readDataFile('tud.addons.chat-default.txt') is None:
        return

    logger = context.getLogger('tud.addons.chat')
    site = context.getSite()
    setup = getToolByName(site, 'portal_setup')
    registry = getUtility(IRegistry)

    if HAVE_JARN_JSI18N:
        if not HAVE_MOCKUP:
            setup.runAllImportStepsFromProfile('profile-jarn.jsi18n:default')
    else:
        if not HAVE_MOCKUP:
            logger.warning('No product for javascript internationalization found! Please install jarn.jsi18n!')

    # remove chat css and javascript resources from legacy bundle (plone 5)
    if 'plone.bundles/plone-legacy.resources' in registry.records:
        legacy_resources = registry.records['plone.bundles/plone-legacy.resources']
        legacy_resources.value = [legacy_resource for legacy_resource in legacy_resources.value if not legacy_resource.startswith('resource-tud-addons-chat-')]

        cookWhenChangingSettings(site)
