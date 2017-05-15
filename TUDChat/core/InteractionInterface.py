# -*- coding: utf-8 -*-
""" Interface exposed for the Chat client
"""

from zope.interface import Interface

class ITUDChatInteractionInterface(Interface):

    #############################
    #  Only admins/moderators
    #############################
    
    def openChatSession(self, REQUEST = None): # Noch unsicher, ob das rein kommt
        """ Open chat """   
    def closeChatSession(self, REQUEST = None): # Noch unsicher, ob das rein kommt   
        """ Close chat """        
    def editMessage(self, message_id, message, REQUEST = None):
        """ Edit message by its id """   
    def deleteMessage(self, message_id, REQUEST = None):
        """ Deletes message by its id """   
        
    #############################
    #  Only registered users
    #############################
    
    def sendMessage(self, message, REQUEST = None): # Username wird per Session ermittelt, die bei registerMe erzeugt wurde.
        """ Send message """
        
    def getActions(self, REQUEST = None):
        """ Returns action-list since the last getAction-Request
            Format: 
                    {
                        'messages: {
                              'new': [ { 'id': 1,
                                         'date': ..,
                                         'name': ..,
                                         'message': .., }, ... ],
                              'to_delete': [ 1,2,3 ],
                              'to_edit': [ { 'id': ..,
                                             'name': ..,
                                             'message': .., }, ... ]
                        },
                        'users': { 
                            'new': ['A','B'],                                     
                            'to_delete': ['C'],
                        }
                    }
            """
        
    def logout(self, REQUEST = None):
        """ Log me out """        
        
    def isAdmin(self, REQUEST = None):    
        """ Has the user admin privileges?
            returns: 'true', 'false' """
            
    #############################
    #  All users
    #############################


    def isRegistered(self, REQUEST = None):    
        """ Is the user registered?
            returns: 'true', 'false' """     
            
    def registerMe(self, user, REQUEST = None):
        """ Register user by its name
            returns: 'true' , when successful
                     'false', otherwise """        
