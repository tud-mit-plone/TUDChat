from Products.CMFCore.utils import getToolByName

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

    if HAVE_JARN_JSI18N:
        if not HAVE_MOCKUP:
            setup.runAllImportStepsFromProfile('profile-jarn.jsi18n:default')
    else:
        if not HAVE_MOCKUP:
            logger.warning('No product for javascript internationalization found! Please install jarn.jsi18n!')
