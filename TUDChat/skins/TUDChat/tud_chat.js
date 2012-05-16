var knownIds = {};
var sendMessageBlock = false;
var updateCheckBlock = false;

var sendMessage = function(){
	message = $("#chatMsgValue").val();

	if (sendMessageBlock)
		return;

	if (message == '')
		return;

	sendMessageBlock = true;
  $("#chatMsgSubmit").attr("disabled", "disabled");
  $("#chatMsgValue").val("");

	$.post("sendMessage", { 'message': message },
        function(data) {                // Immediately update the chat, after sending the message
            updateCheck(); 
          }
        );
  $.doTimeout( 'remove_sendMessageBlock', blockTime, function(){
      $("#chatMsgSubmit").removeAttr("disabled");    	
    	$("#chatMsgValue").focus();
    	sendMessageBlock = false;  
  });
};

var goHierarchieUp = function(){
	// Move from {obj}/chat to {obj}
	var url = window.location.href;
	if (url.substr(-1) == '/') url = url.substr(0, url.length - 2);
	url = url.split('/');
	url.pop();
	window.location = url.join('/');
}

var updateCheck = function(){    
	
	if (updateCheckBlock) // temporary workaround
		return;

	$.getJSON("getActions", function(data){
		// Status

		if (data.status.code == 1) { // Not authorized
			// $.doTimeout( 'updateCheck'); // stop updateCheck
			updateCheckBlock = true;			
			$.notification.error("Sie sind nicht authorisiert! Bitte loggen Sie sich ein.", false, [{"name" :"Ok",
                                                                          "click":function(){                                                                          	
                                                                              $.notification.clear();
                                                                              goHierarchieUp();
                                                                          }},
                                                                         ]);			
			return;
		}
		if (data.status.code == 2) { // Kicked			
			//$.doTimeout( 'updateCheck' ); // stop updateCheck
			updateCheckBlock = true;
			if (data.status.message != "") {
				kickmessage = data.status.message;
			}else{
				kickmessage = "Sie wurden von einem Administrator des Chats verwiesen!";
			}
			$.notification.error(kickmessage, false, [{"name" :"Ok",
                                                                          "click":function(){                                                                          	
                                                                              $.notification.clear();
                                                                              goHierarchieUp();
                                                                          }},
                                                                         ]);			
			return;
		}

		if (data.status.code == 3) { // Banned
			//$.doTimeout( 'updateCheck' ); // stop updateCheck
			updateCheckBlock = true;
			$.notification.error("Sie wurden dauerhaft des Chats verwiesen! <br/><br/>Grund: " + data.status.message, false, [{"name" :"Ok",
                                                                          "click":function(){                                                                          	
                                                                              $.notification.clear();
                                                                              goHierarchieUp();
                                                                          }},
                                                                         ]);			
			return;
		}

    if (data.status.code == 5) { // Warned
      //$.doTimeout( 'updateCheck' ); // stop updateCheck
      $.notification.warn("Verwarnung! <br/><br/> <em>" + data.status.message+"</em>", false, [{"name" :"Ok",
                                                                          "click":function(){  
                                                                            $.notification.close($(this).closest(".notification").attr("id"));
                                                                          }},
                                                                         ]);      
      return;
    }
      if (data.status.code == 6) { // Warned (to show in chat)
        //$.doTimeout( 'updateCheck' ); // stop updateCheck
        $("#chatContainer").append("<li>"+data.status.message+"</li>");
        return;
      }
       

		if (data.status.code != 0) // != OK
			return;

		if(typeof(data.messages)!="undefined"){
			if(typeof(data.messages['new'])!="undefined"){
				message = data.messages['new'];
				for(var i in data.messages['new']) {          
					$("#chatContainer").append(printMessage(message[i]));
				}
			}
			if(typeof(data.messages.to_edit)!="undefined"){
				message = data.messages.to_edit;                
				for(var i in data.messages.to_edit){                    
					$("#chatEntry"+message[i].id).replaceWith(printMessage(message[i]));
				}
			}
			if(typeof(data.messages.to_delete)!="undefined"){
                message = data.messages.to_delete;                
				for(var i in data.messages.to_delete){
					$("#chatEntry"+message[i].id).replaceWith(printMessage(message[i]));
				}
			}
		}
		if(typeof(data.users)!="undefined"){
			if(typeof(data.users['new'])!="undefined"){
				var user = data.users['new'];
        var added = false;
				for(var i in data.users['new']) {
					element = $(printNewUser(user[i])).attr("data-uname", user[i]);
          $("#userContainer").children().each(function(){ // Enumerate all existing names and insert alphabetically
              if ($(this).text() > user[i]) {
                  $(element).insertBefore($(this));
                  added = true;
                  return false;
              }
              });
          if (!added)
            element.appendTo($("#userContainer"));
          };     
				}
			}
			if(typeof(data.users.to_delete)!="undefined"){
				user = data.users.to_delete;
				for(var i in data.users.to_delete)
					$(".chatUser[data-uname='"+user[i]+"']").remove();				
			}		
        performScrollMode();
	});
};

var updateCheckTimeout = function(){	    
    updateCheck();	
    $.doTimeout( 'updateCheck', refreshRate, updateCheckTimeout);
};

/* Automatic scrollbar behaviour 
   Source kindly taken from: http://www.yelotofu.com/2008/10/jquery-how-to-tell-if-youre-scroll-to-bottom */
   
var scrollMode = { 'normal': 0, 'alwaysBottom': 1 },
    currentScrollMode = scrollMode.alwaysBottom;

var checkScrollMode = function() {   
    var elem = $('#chatContent');
    var inner = $('#chatContainer');

    if ( (Math.abs(inner.offset().top) + elem.height() + elem.offset().top + 10) >= inner.outerHeight() ) { 
      currentScrollMode = scrollMode.alwaysBottom;      
    } else { 
      currentScrollMode = scrollMode.normal;
    }
};   

var performScrollMode = function() {    
    var elem = $('#chatContent');
    var inner = $('#chatContainer');
    if (currentScrollMode == scrollMode.alwaysBottom && !((Math.abs(inner.offset().top) + elem.height() + elem.offset().top + 10) >= inner.outerHeight()))
      elem.scrollTop(inner.outerHeight());
};   
 
    
/* This function returns the changes of a message-entry based upon its message's attributes.
   Output will be an object with properties:
    * message_content
    * additional_content
    * entry_classes
*/
var applyAttributes = function (message, attributes) {
    message_content = typeof(message)!="undefined" ? message : '';
    additional_content  = '';
    entry_classes = ''
    
    if(typeof(attributes)!="undefined"){
        for (i = 0; i < attributes.length; i++) {
            if (attributes[i].a_action == 'edit_message') {
                additional_content += " (bearbeitet durch "+ attributes[i].a_name +")";
                entry_classes += " admin_edit";                
            }
            if (attributes[i].a_action == 'delete_message') {
                additional_content = "Gel&ouml;scht durch "+ attributes[i].a_name;
                entry_classes += " admin_delete";
            }
            if (attributes[i].admin_message == true) {
                entry_classes += " admin_message";
            }
        }
    }
    return { "entry_classes": entry_classes, "message_content": message_content, "additional_content": additional_content };
};


$(document).ready(
	function(){
		jQuery.ajaxSetup({'cache':false});
		$("#chatMsgSubmit").click(sendMessage);
		$("#chatMsgValue").keypress(
			function(event){
				if(event.keyCode == 13) {
					sendMessage();
        }
			}
		);
		$.get("resetLastAction", function(data){        
		updateCheckTimeout();
		});        
        
        $("#logout").click(function() {
            updateCheckBlock = true;
            $.ajax(
              {type: "GET",
               dataType: "text",
               url: "logout",
                success: function(data) {
             	    goHierarchieUp();
                 },               
                error:function (xhr, ajaxOptions, thrownError){ // leave chat no matter what                  
                  goHierarchieUp();
                }    
              });            
          });
        // Scrollbar mode change
		$('#chatContent').scroll(function(){           
            // See: http://benalman.com/projects/jquery-dotimeout-plugin/
            $.doTimeout( 'checkScrollMode', 250, checkScrollMode);
        });
        // security information for user links
        $("#chatContent").delegate(".message_content a", "click", function(e) {
            if(!$(e.target.parentNode.parentNode).hasClass('admin_message')){
                $.notification.warn("Dieser Link wurde von einem Chat-Nutzer geschrieben. Die TU-Dresden möchte sich an dieser Stelle ausdrücklich von dem Inhalt dieses Links distanzieren. <br/><br/> Soll der Link <tt>" + e.target.href + "</tt> wirklich geöffnet werden?", false,                
                                                                        [{"name" :"Ja",
                                                                            "click":function(){                                                                           
                                                                              window.open(e.target.href,"_blank")
                                                                              $.notification.clear();
                                                                            }},
                                                                        {"name" :"Nein", "click": $.notification.clear },                                                                         
                                                                         ]);
                e.preventDefault();
            }
            
            
        });
	}
);

