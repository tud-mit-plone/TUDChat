# -*- coding: utf-8 -*-
""" Interface for the Persistence Layer (probably biased towards SQL-Databases)
"""

from Interface import Interface

class ITUDChatStorage(Interface):

    def createChatSession(self):
        """ returns chat_uid """        
    def closeChatSession(self, chat_uid):
        """ TODO: enter text """
    def openChatSession(self, chat_uid):
        """ TODO: enter text """        
    def getChatSession(self, chat_uid):
        """ TODO: enter text """        
    # Low-level methods
    def getActions(self, chat_uid, last_action, start_action):
        """ TODO: enter text """
    def sendAction(self, chat_uid, user, action, content = "", target = None):
        """ TODO: enter text """
    # High-level methods    
    def sendMessage(self, chat_uid, user, message):
        """ TODO: enter text """
    def editMessage(self, user, message_id, message):
        """ TODO: enter text """
    def deleteMessage(self, user, message_id):
        """ TODO: enter text """
    def getLastChatAction(self, chat_uid):
        """ TODO: enter text """