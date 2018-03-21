"""
This is a cron script, which realizes chat specific tasks.
A system cron should periodical execute this script.
"""
import os
import sys
import argparse
import logging
from time import strftime, localtime
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
import transaction
from zope.component.hooks import setSite
from zope import interface
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManager import setSecurityPolicy
from Products.CMFCore.tests.base.security import PermissiveSecurityPolicy, OmnipotentUser
from Products.CMFCore.utils import getToolByName
import Testing
from ZODB.POSException import ConflictError
from plone import api

from tud.addons.chat.interfaces import IChatSession, IAddonInstalled

def dir_arg(path):
    """
    Checks if given path exists and if it is a directory.

    :param path: path to check
    :type path: str
    :return: given path, if it exists and it is a directory
    :rtype: str
    """
    if not os.path.exists(path):
        msg = "{!r} doesn't exist".format(path)
        raise argparse.ArgumentTypeError(msg)
    if not os.path.isdir(path):
        msg = "{!r} has to be a directory".format(path)
        raise argparse.ArgumentTypeError(msg)
    return path

def main(app):
    """
    Executes chat specific tasks.
    Before execution is performed arguments will be parsed, logging will be initialized, new security manager will be set and plone site will be prepared.
    If a conflict error occurs during chat task execution, all chat tasks will rerun.

    :param app: zope application root
    :type app: OFS.Application.Application
    """
    arg_parser = argparse.ArgumentParser(description=u"chat cron")
    arg_parser.add_argument('-c', '--script', required=True, help='script name')
    arg_parser.add_argument('-s', '--site', required=True, metavar='SITE', help='name of the Plone site')
    arg_parser.add_argument('-l', '--logging-path',
                            metavar='PATH',
                            type=dir_arg,
                            required=False,
                            help='path to logging folder')
    arg_parser.add_argument('-d', '--do',
                            action='store_true',
                            help='set to actually perform changes, otherwise a dry run is performed')
    options = arg_parser.parse_args(sys.argv[1:])

    #setup logging
    logger = logging.getLogger('chat')
    stream_logger = logging.StreamHandler()
    stream_logger.setFormatter(logging.Formatter('%(levelname)s - %(asctime)s - %(name)s - %(message)s'))
    logger.addHandler(stream_logger)
    if options.logging_path:
        time_str = strftime('%Y-%m-%d_%H-%M', localtime())
        log_path = '{}_{}.log'.format('chat', time_str)
        log_path = os.path.join(options.logging_path, log_path)
        log_handler = logging.FileHandler(log_path, 'a')
        log_handler.setFormatter(logging.Formatter('%(levelname)s;%(asctime)s;%(name)s;%(message)s'))
        logger.addHandler(log_handler)
    logger.setLevel(logging.DEBUG)

    logger.info('script started')

    _policy=PermissiveSecurityPolicy()
    _oldpolicy=setSecurityPolicy(_policy)
    newSecurityManager(None, OmnipotentUser().__of__(app.acl_users))
    app = Testing.makerequest.makerequest(app)
    interface.alsoProvides(app.REQUEST, IAddonInstalled) # layer is needed to use browser views

    # Get Plone site object from Zope application server root
    if options.site not in app:
        logger.error('can not find plone site {0} at server'.format(options.site))
        return
    if not options.do:
        logger.info('This is a dry run. To perform actual changes use "--do" argument.')
    site = app.unrestrictedTraverse(options.site)
    site.setupCurrentSkin(app.REQUEST)
    setSite(site)

    while True:
        try:
            archiveClosedChatSessions(site, logger, options.do)
            deleteOldChatSessions(site, logger, options.do)
            break
        except ConflictError, e:
            logger.error(repr(e))
            transaction.abort()
        except KeyboardInterrupt:
            logger.warning('script interrupted')
            raise
        except Exception, e:
            logger.error(repr(e))
            raise
    if options.do:
        # commit changes
        transaction.get().note('chat')
        transaction.commit()
        app._p_jar.sync()
        logger.info('transaction commited')
    logger.info('script finished')

def archiveClosedChatSessions(site, logger, do):
    """
    This function starts in all closed and not archived chat sessions a workflow transition which obfuscates user names. Only chat sessions that have been closed for more than 5 minutes will be affected.

    :param logger: provides logging functionality
    :type logger: logging.Logger
    :param do: True, if changes should be persisted, otherwise False
    :type do: bool
    :return: count of archived chat sessions
    :rtype: str
    """
    catalog = getToolByName(site, 'portal_catalog')
    query = {
        'object_provides': IChatSession.__identifier__,
        'ChatSessionEndDate': {'query': datetime.now() - timedelta(minutes = 6), 'range': 'max'},
        'review_state': 'editable'
        }
    session_brains = catalog(query)
    for session_brain in session_brains:
        session_url = session_brain.getURL()
        if do:
            logger.info(u'archive session at {}'.format(session_url))
            session = session_brain.getObject()
            api.content.transition(obj=session, transition='archive')
        else:
            logger.info(u'would archive session at {}'.format(session_url))

    if do:
        logger.info("archived chat sessions: {}".format(str(len(session_brains))))

    return str(len(session_brains))

def deleteOldChatSessions(site, logger, do):
    """
    This function deletes chat sessions that have been closed for at least 3 months.

    :param logger: provides logging functionality
    :type logger: logging.Logger
    :param do: True, if changes should be persisted, otherwise False
    :type do: bool
    :return: count of deleted chat sessions
    :rtype: str
    """
    catalog = getToolByName(site, 'portal_catalog')
    query = {
        'object_provides': IChatSession.__identifier__,
        'ChatSessionEndDate': {'query': datetime.now() - relativedelta(months=3), 'range': 'max'},
        }
    session_brains = catalog(query)
    for session_brain in session_brains:
        session_url = session_brain.getURL()
        if do:
            logger.info(u'delete session at {}'.format(session_url))
            session = session_brain.getObject()
            api.content.delete(obj=session, check_linkintegrity=False)
        else:
            logger.info(u'would delete session at {}'.format(session_url))

    if do:
        logger.info("deleted chat sessions: {}".format(str(len(session_brains))))

    return str(len(session_brains))

if __name__ == '__main__':
    main(app)
