var knownIds = {};
var sendMessageBlock = false;
var updateCheckBlock = false;
var scrollBlock      = false;
var firstGetActions = true;
var currentUserNum  = 0;
var dateLastMinute  = new Date(0).setSeconds(0, 0);
var locale          = undefined;
var target          = null;

var dateFrequency   = "off";
var whisper         = "off";

var sendMessage = function(method){
    if(!method) {
      method = 'sendMessage';
    }
    message = $("#chatMsgValue").val();

    if (sendMessageBlock)
        return false;

    if (message == '')
        return false;

    sendMessageBlock = true;
  $("#chatMsgSubmit").attr("disabled", "disabled");
  $("#chatMsgValue").val("").keyup();

  var targetData = target ? { 'target': target } : {};
  removeTarget();

  var data = $.extend({}, {'method': method, 'message': message }, targetData);

    $.post(ajax_url, data,
        function(data) {                // Immediately update the chat, after sending the message
            currentScrollMode = scrollMode.alwaysBottom;
            updateCheck();
          }
        );
  $.doTimeout( 'remove_sendMessageBlock', blockTime, function(){
      $("#chatMsgSubmit").removeAttr("disabled");
        $("#chatMsgValue").focus();
        sendMessageBlock = false;
  });
  return false;
};

var goHierarchieUp = function(){
    // Move from {obj_chat}/{obj_session} to {obj_chat}
    var url = window.location.href;
    if (url.substr(-1) == '/') url = url.substr(0, url.length - 2);
    url = url.split('/');
    url.pop();
    window.location = url.join('/');
}

var sortByRoleName = function(object1, object2){
  // Compare two objects by their 'role' and 'name' properties lexicographically
  return [!object1.is_admin, object1.name] >= [!object2.is_admin, object2.name] ? 1 : -1;
}

// function to format time strings
var formatTimes = function(newTimesOnly) {
  // make german times more nice
  var timeStingSuffix = "";
  if (locale.substring(0, 2) == "de") {
    timeStingSuffix = " Uhr";
  }

  var now = new Date();
  var strF = "2-digit";
  var $toFormat = newTimesOnly ? $("#chatContent .chatdate:empty") : $("#chatContent .chatdate");
  $toFormat.each(function(i, v) {
    var $v = $(v);
    var timestamp = $v.data("time");
    var date = new Date(timestamp*1000);
    var dateD = new Date(timestamp*1000);

    // if we are on the same day, print without the date
    if(dateD.setHours(0,0,0,0) == now.setHours(0,0,0,0)) {
      $v.text(date.toLocaleTimeString(locale, { hour: strF, minute: strF } ) + timeStingSuffix );
    } else {
      $v.text(date.toLocaleString(locale, { year: strF, month: strF, day: strF, hour: strF, minute: strF }) + timeStingSuffix );
    }
  });
}

// Daemon that runs everytime a day changes to reformat all time strings
var startReformatDaemon = function() {
  var d = new Date();
  var h = d.getHours();
  var m = d.getMinutes();
  var s = d.getSeconds();
  var secondsUntilNextDay = (24*60*60)-(h*60*60)-(m*60)-s + 3;
  window.setTimeout(function () {
    formatTimes();
    startReformatDaemon();
  }, secondsUntilNextDay*1000);
}

var updateCheck = function(welcome_message){

    if (updateCheckBlock) // temporary workaround
        return;
    updateCheckBlock = true;

    $.post(ajax_url, {'method': 'getActions'}, function(data){
        // Status

        if (data.status.code == 1) { // Not authorized
            // $.doTimeout( 'updateCheck'); // stop updateCheck
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
            if (data.status.message != "") {
                kickmessage = data.status.message;
            }else{
                kickmessage = "Sie wurden von einem Moderator des Chats verwiesen!";
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
    }
      if (data.status.code == 6) { // Warned (to show in chat)
        //$.doTimeout( 'updateCheck' ); // stop updateCheck
        $("#chatContainer").append("<li>"+data.status.message+"</li>");
      }


        if (data.status.code > 6) // != OK
            return;

    if(typeof(data.users)!="undefined"){
      if(typeof(data.users['new'])!="undefined"){
        var users = data.users['new'].sort(sortByRoleName);
        // Get list of usernames
        var usernames = $(users).map(function(){ return $(this).attr("name"); }).get();

        for(var i in users) {
          var username = usernames[i];
          var role = users[i]['is_admin'] ? 'admin' : 'user';
          var added = false;
          element = $(printNewUser(username, role)).attr({"data-uname": username, "title": role == 'admin' ? username + " ist Moderator." : ""});

          $("#userContainer").children().each(function(){ // Enumerate all existing names and insert alphabetically
            var otherRole = $(this).hasClass('adminrole');
            var otherUsername = $(this).text();
            if ([!otherRole, otherUsername] >= [role != 'admin', username]) {
                $(element).insertBefore($(this));
                added = true;
                return false;
            }
            });

          if (!added)
            element.appendTo($("#userContainer"));

        };

        // Update the chat user counter
        var newUserNum = $("#userContainer").children().length;
        if(newUserNum != currentUserNum) {
          $("#userCount").text( newUserNum );
          currentUserNum = newUserNum;
        }

          // Notification: User has entered the room
          if (!firstGetActions){
            if (usernames.length == 1)
              $("#chatContent").append("<div class='chat-info'><span class='username'>"+usernames+"</span> hat den Raum betreten.</div>");
            else if (usernames.length != 0) {
              last_user = usernames.pop();
              $("#chatContent").append("<div class='chat-info'><span class='username'>"+usernames.join(', ')+"</span> und <span class='username'>"+last_user+"</span> haben den Raum betreten.</div>");
            }
          }
        }

        if(typeof(data.users['to_delete'])!="undefined"){
          user = data.users.to_delete.sort();
          for(var i in user)
            $(".chatUser[data-uname='"+user[i]+"']").remove();
          // Notification: User has left the room
          if (!firstGetActions){
            if (user.length == 1)
              $("#chatContent").append("<div class='chat-info'><span class='username'>"+user+"</span> hat den Raum verlassen.</div>");
            else if (user.length != 0) {
              last_user = user.pop();
              $("#chatContent").append("<div class='chat-info'><span class='username'>"+user.join(', ')+"</span> und <span class='username'>"+last_user+"</span> haben den Raum verlassen.</div>");
            }
          }
        }

      }

        if(typeof(data.messages)!="undefined"){
            if(typeof(data.messages['new'])!="undefined"){
                message = data.messages['new'];
                for(var i in data.messages['new']) {
                    var mDate = new Date(message[i].date*1000).setSeconds(0, 0);
                    if(dateFrequency == "minute" && mDate - dateLastMinute >= 60) {
                      dateLastMinute = mDate;
                      $("#chatContent").append("<div class='chat-info'><span class='chatdate' data-time='"+message[i].date+"'></span></div>");
                    }
                    $("#chatContent").append(printMessage(message[i]));
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

        // we potentially added new times, format them
        formatTimes(true);

    if(welcome_message){
        var $message = $("<li id='welcome_message'></li>").append($("<span class='message_content'></span>").text(welcome_message));
        $("#chatContent").append($message);
    }

    firstGetActions = false;
    updateCheckBlock = false;

    if (!scrollBlock)
      performScrollMode();
    });
};

var updateCheckTimeout = function(first_run){
    if(first_run){
        var welcome_message = $('#chat').data('welcome_message');
        if(welcome_message){
            welcome_message = 'Willkommensnachricht: ' + welcome_message;
            updateCheck(welcome_message);
        }else{
            updateCheck();
        }
    }else{
        updateCheck();
    }
    $.doTimeout( 'updateCheck', refreshRate, updateCheckTimeout);
};

/* Automatic scrollbar behaviour
   */

var scrollMode = { 'normal': 0, 'alwaysBottom': 1 },
    currentScrollMode = scrollMode.alwaysBottom;

var checkScrollMode = function() {
    var elem = $('#chatContent');

    if ( elem.scrollTop() + elem.innerHeight() >= elem[0].scrollHeight ) {
      currentScrollMode = scrollMode.alwaysBottom;

    } else {
      currentScrollMode = scrollMode.normal;
    }
};

var performScrollMode = function() {
    var elem = $('#chatContent');
    if (currentScrollMode == scrollMode.alwaysBottom && !( elem.scrollTop() + elem.innerHeight() >= elem[0].scrollHeight ))
      elem.scrollTop(elem[0].scrollHeight);
};

/* This function returns the changes of a message-entry based upon its message's attributes.
   Output will be an object with properties:
    * message_content
    * additional_content
    * entry_classes
*/
var applyAttributes = function (message, attributes) {
    var message_content = typeof(message)!="undefined" ? message : '';
    var additional_content  = '';
    var entry_classes = '';
    var whisper = false;

    if(typeof(attributes)!="undefined"){
        for (var i = 0; i < attributes.length; i++) {
            if (attributes[i].a_action == 'mod_edit_message') {
                additional_content += " Bearbeitet durch "+ attributes[i].a_name;
                entry_classes += " admin_edit";
            }
            if (attributes[i].a_action == 'mod_delete_message') {
                additional_content = "Gel&ouml;scht durch "+ attributes[i].a_name;
                entry_classes += " admin_delete";
            }
            if (attributes[i].admin_message == true) {
                entry_classes += " admin_message";
            }
            if (attributes[i].whisper == true) {
                whisper = true;
            }
        }
    }
    return { "entry_classes": entry_classes, "message_content": message_content, "additional_content": additional_content, 'whisper': whisper};
};

// remove the target chat user
var removeTarget = function() {
  target = null;
  var $chatMsgValue = $('#chatMsgForm #chatMsgValue');
  $('#chatMsgForm #chatMsgTarget').remove();
  $chatMsgValue.css("padding-top", $chatMsgValue.data("padding-top")).trigger("keyup").focus();
  $("#chatMsgMoreButtons").hide();
}


$(document).ready(
    function(){

      // read the data-settings on the chat DOM-object
      dateFrequency = $('#chat').data('date_frequency');
      whisper       = $('#chat').data('whisper');

      locale = $("html").attr("lang");

        jQuery.ajaxSetup({'cache':false});

    $("#chatMsgForm").submit(sendMessage);

        $.post(ajax_url, {'method': 'resetLastAction'}, function(data){
        updateCheckTimeout(true);
        });

        $("#logout").click(function() {
            updateCheckBlock = true;
            $.ajax(
              {type: "POST",
               data: {'method': 'logout'},
               dataType: "text",
               url: ajax_url,
                success: function(data) {
                     goHierarchieUp();
                 },
                error:function (xhr, ajaxOptions, thrownError){ // leave chat no matter what
                  goHierarchieUp();
                }
              });
          });

          // Handle the chatUser button clicks: Hide and unhide the chatUser list
          $("#chatUser button").click(function() {
            $("#chatUser #userContainer").toggle();
            $("#chatUser .chatUsersArrow").toggleClass("icon-up").toggleClass("icon-down");

            // If the chatUser list is visible now, make it closable by clicking anywhere on the page
            if($("#userContainer:visible").length) {
              $("body").on("click.chatUserContainer", function(e) {
                if( $(e.target).closest("#userContainer, #chatUser button").length == 0 ) {
                  $("#chatUser button").click();
                }
              });
            } else {
              $("body").off("click.chatUserContainer");
            }
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

    // logic for choosing a chat user as message target
    $('#chat').on('click', '#chatUser li a', function(e) {
      e.preventDefault();

      // cleanup the old target
      removeTarget();

      target = $(e.target).data("uname");

      var $targetContent = $('<span id="chatMsgTarget">Nachricht an: ' + target + ' <a href="#">X</a></span>');
      var $chatMsgValue = $('#chatMsgForm #chatMsgValue');

      $('#chatMsgForm').prepend($targetContent);

      // add some padding at the top of the textarea
      var targetContentHeight = $targetContent.outerHeight();
      var chatMsgValuePaddingTop = $chatMsgValue.css("padding-top");
      $chatMsgValue.data("padding-top", chatMsgValuePaddingTop);
      $chatMsgValue.css("padding-top", "calc(" + chatMsgValuePaddingTop + " + " + chatMsgValuePaddingTop + " + " + targetContentHeight + "px)").trigger("keyup").focus();

      // show the admin-buttons (if they exist)
      $("#chatMsgMoreButtons").css("display", "inline-block");

      // hide the chat user list
      $('#chatUser').click();
    });

    // logic for removing the message target
    $('#chatMsgForm').on('click', '#chatMsgTarget a', function(e) {
      e.preventDefault();
      removeTarget();
    });

    // Scrollbar movement
    $('#chatContent').bind('scrollstart',function(){
      scrollBlock = true;
    });

    $('#chatContent').bind('scrollstop',function(){
      scrollBlock = false;
      checkScrollMode();
    });

    //counter
    if(maxMessageLength>0){
      $('#chatMsgValue').bind("keypress keyup", function(event){
        $('#counter').text((maxMessageLength-$('#chatMsgValue').val().length) + " / " + maxMessageLength);
      });

      $('#chatMsgValue').keypress();
    }

    // auto resize the message input field
    var $textInput = $("#chatMsgValue");
    var textInputOffset = $textInput[0].offsetHeight - $textInput[0].clientHeight;
    $textInput
      .on('keyup', function() {
        $(this).css('height', '').css('height', this.scrollHeight + textInputOffset);
      }).keypress(function (e) {
        // prevent line breaks and send the message instead
        var key = e.which;
        if(key == 13) {
          e.preventDefault();
          sendMessage();
        }
      });

      // start the time reformat daemon
      startReformatDaemon();

    }
);


