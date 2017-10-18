(function( global, $ ) {

    var TudChat = (function() {
        var publicVars = {};

        // default options
        var options = {
            admin:            false,
            welcomeMessage:   "",
        };

        var knownIds            = {},
            lastUpdate          = new Date(),
            updateIntervalId    = null,
            updateCheckBlock    = false,
            sendMessageBlock    = false,
            scrollBlock         = false,
            firstGetActions     = true,
            dateLastMinute      = new Date(0).setSeconds(0, 0),
            target              = null,
            locale              = "en",
            _                   = null;

        // initialize once the document is "ready"
        $(function() {
            // extract options and locale from DOM
            options = $.extend({}, options, $('#chat').data());
            locale  = $("html").attr("lang");

            publicVars.ajaxUrl = options.ajaxUrl;

            // init with jsi18n (either from mockup or jarn)
            if(typeof(require) == "function" && require.defined("mockup-i18n")) {
                require(['mockup-i18n'], function(I18N) {
                    var i18n = new I18N();
                    init(i18n);
                });
            } else {
                init(jarn.i18n);
            }
        });


        var sendMessage = function(method){
            if(!method) {
                method = 'sendMessage';
            }
            message = $("#chatMsgValue").val();

            // don't allow empty messages for the normal message sending method
            if (sendMessageBlock || (message == '' && method =='sendMessage')) {
                return false;
            }

            sendMessageBlock = true;

            $("#chatMsgSubmit").attr("disabled", "disabled").attr("isSending", true);
            $("#chatMsgValue").val("").keyup();

            // set the target
            var targetData = target ? { 'target_user': target } : {};
            removeTarget();

            var data = $.extend({}, {'method': method, 'message': message }, targetData);

            $.post(options.ajaxUrl, data,
                // Immediately update the chat, after sending the message
                function(data) {
                    currentScrollMode = scrollMode.alwaysBottom;
                    updateCheck();
                }
            );

            window.setTimeout(function() {
                $("#chatMsgSubmit").removeAttr("disabled isSending");
                $("#chatMsgValue").focus();
                sendMessageBlock = false;
            }, options.blockTime);
        };

        var goHierarchieUp = function(){
            // Move from {obj_chat}/{obj_session} to {obj_chat}
            var url = window.location.href;
            if (url.substr(-1) == '/') url = url.substr(0, url.length - 2);
            url = url.split('/');
            room = /^[^\?]+/.exec(url.pop())[0];
            target_url = url.join('/') + '?room=' + encodeURIComponent(room)
            window.location = target_url;
        }

        // get a username link for whispering or the plain username as fallback if whisper is not allowed
        var getUnameLink = function(username, linkOptions) {
            var defaults = {
                fromAdmin: false, // wether the sender is admin
                toAdmin: false, // wether the target is admin
                afterStart: true, // only print the link if we are not in the firstGetActions phase
                checkOnline: false, // check if the username is 'online'
                linkTitle: _('send_private_message', {user: username}), // title of the link
                preText: "", // text that will be prepended (before the link)
                fallback: false // fallback as alternative to the link
            };
            linkOptions = $.extend({}, defaults, linkOptions);

            var cssClasses = new Array();
            if(linkOptions.toAdmin) {
                cssClasses.push("icon-view");
            }
            if(username == options.ownUserName) {
                cssClasses.push("self");
            }

            // there are some cases were we don't want to print a link
            if(
                !(options.whisper == "on" || (options.whisper == "restricted" && linkOptions.toAdmin) || linkOptions.fromAdmin)
                || (username == options.ownUserName)
                || (linkOptions.afterStart && firstGetActions)
                || (linkOptions.checkOnline && !$("#userContainer a[data-uname='"+username+"']").length )
            ) {
                if(linkOptions.fallback) {
                    return linkOptions.fallback;
                } else {
                    var spanText = $("<span class='username' />")
                                .addClass(cssClasses.join(" "))
                                .append(username)
                                .prop("outerHTML");
                    return linkOptions.preText + spanText;
                }
            }

            var title   = (linkOptions.linkTitle) ? linkOptions.linkTitle : "",
                linkHtml = $("<a href='#' class='username' />")
                            .attr("title", title)
                            .addClass(cssClasses.join(" "))
                            .attr("data-uname", username)
                            .append(username)
                            .prop("outerHTML");
            return linkOptions.preText + linkHtml;
        }

        function printMessage(message) {
            var timeSpan = adminSpan = whisperSpan = whisperIcon = "",
                changes             = applyAttributes(message.message, message.attributes),
                parsed_message      = TudChatHyperlink(changes.message_content),
                entryClasses        = [changes.entry_classes],
                additional_content  = changes.additional_content;

            if(options.admin) {
                entryClasses.push("admin");
            }

            if(message.name == options.ownUserName) {
                entryClasses.push("ownMessage");
            }

            if(options.dateFrequency == "message") {
                timeSpan = $("<span/>")
                    .addClass("chatdate")
                    .attr("data-time", message.date);
            }

            // handle whisper messages
            if(changes.whisper_target) {
                entryClasses.push("whisper");
                whisperSpan = $("<span class='additional_content' />")
                    .html( getUnameLink( changes.whisper_target, { preText: _('private_message_to') + " ", fromAdmin: options.admin } ) );
                whisperIcon = $("<span class='whisper-icon '/>");
            } else if(options.admin) {
                // add extra buttons for admins
                adminSpan = $("<span/>")
                    .addClass("adminActions")
                    .append(
                        $("<a href='#' class='edit'>&nbsp;</a>")
                            .attr("data-mid", message.id)
                            .attr("title", _('edit_message'))
                    )
                    .append(
                        $("<a href='#' class='delete'>&nbsp;</a>")
                            .attr("data-mid", message.id)
                            .attr("title", _('delete_message'))
                    )
            }

            var userNameString = getUnameLink(message.name, { fromAdmin: options.admin, checkOnline: true, toAdmin: changes.admin_message });

            // the actual message content
            var messageContent = $("<span class='message_content'/>")
                .append(
                    whisperSpan,
                    $("<span class='message'/>").append(parsed_message)
                );
            if(additional_content != "") {
                messageContent.append(
                    $("<span class='additional_content'/>").append(additional_content)
                )
            }

            return $("<div/>")
                .attr("id", "chatEntry"+message.id)
                .addClass(entryClasses.join(" "))
                .append(
                    $("<span class='meta-information'>").append(userNameString, timeSpan, adminSpan),
                    whisperIcon,
                    $("<div/>").append(messageContent)
                );
        }

        function printNewUser(user, role) {
            var liContent = getUnameLink(user, { afterStart: false, fromAdmin: options.admin, toAdmin: (role == "admin") }),
                entryClasses = new Array();
            if (user == options.ownUserName) {
                entryClasses.push('ownUsername');
            }
            entryClasses.push(role + 'role');

            return $("<li/>")
                        .addClass("chatUser")
                        .addClass(entryClasses.join(" "))
                        .append(liContent)
                        .prop("outerHTML");
        }

        // function to format time strings
        var formatTimes = function(newStampsOnly) {
            // make german times more pretty
            var timeStingSuffix = "";
            if (locale.substring(0, 2) == "de") {
                timeStingSuffix = " Uhr";
            }

            var now = new Date(),
                strF = "2-digit",
                $toFormat = newStampsOnly ? $("#chatContent .chatdate:empty") : $("#chatContent .chatdate");
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
            var d = new Date(),
                h = d.getHours(),
                m = d.getMinutes(),
                s = d.getSeconds(),
                secondsUntilNextDay = (24*60*60)-(h*60*60)-(m*60)-s + 3;

            window.setTimeout(function () {
                formatTimes();
                startReformatDaemon();
            }, secondsUntilNextDay*1000);
        }

        var updateCheck = function(welcomeMessage){
            if (updateCheckBlock) {
                return;
            }
            updateCheckBlock = true;

            $.post(options.ajaxUrl, {'method': 'getActions'}, function(data){
                lastUpdate = new Date();

                if(!$("#chatMsgSubmit[isSending]").length) {
                    $("#chatMsgSubmit").removeAttr("disabled");
                }
                $("#chat .serverError:visible").fadeOut(400);

                // Status
                if (data.status.code == 1) { // Not authorized
                    stopUpdateChecker();
                    goHierarchieUp();
                    return;
                }
                if (data.status.code == 2) { // Kicked
                    stopUpdateChecker();
                    goHierarchieUp();
                    return;
                }

                if (data.status.code == 3) { // Banned
                    stopUpdateChecker();
                    goHierarchieUp();
                    return;
                }

                if (data.status.code == 5) { // Warned
                    $.notification.warn(_('warning') + "<br/><br/> <em>" + data.status.message+"</em>", false, [{"name" :_('button_ok'),
                        "click":function(){
                            $.notification.close($(this).closest(".notification").attr("id"));
                        }},
                    ]);
                }

                if (data.status.code > 5) // != OK
                return;

                // handle user information
                if(typeof(data.users)!="undefined"){

                    // new users
                    if(typeof(data.users['new'])!="undefined"){

                        var sortByRoleAndName = function(object1, object2){
                            // Compare two objects by their 'role' and 'name' properties lexicographically
                            return [!object1.is_admin, object1.name] >= [!object2.is_admin, object2.name] ? 1 : -1;
                        }
                        var users = data.users['new'].sort(sortByRoleAndName);

                        for(var i in users) {
                            var username    = users[i].name,
                                role        = users[i]['is_admin'] ? 'admin' : 'user',
                                added       = false,
                                $element    = $(printNewUser(username, role))
                                    .attr({"data-uname": username, "title": (role == 'admin' ? _('user_is_moderator', {user: username}) : "") });

                            $("#userContainer").children().each(function(){ // Enumerate all existing names and insert alphabetically
                                var otherRole = $(this).hasClass('adminrole'),
                                    otherUsername = $(this).text();
                                if ([!otherRole, otherUsername] >= [role != 'admin', username]) {
                                    $(this).before($element)
                                    added = true;
                                    return false;
                                }
                            });

                            if (!added) {
                                $("#userContainer").append($element);
                            }
                        };

                        // Notification: User has entered the room
                        if (!firstGetActions){
                            // get list of usernames
                            var usernames = $(users).map(function(){ return $(this).attr("name"); }).get();

                            if (usernames.length == 1)
                            $("#chatContent").append(
                                $("<div class='chat-info'/>")
                                .html( _('user_enters_room', {user: "<span class='username'>"+usernames+"</span>"}) )
                            );
                            else if (usernames.length != 0) {
                                last_user = usernames.pop();
                                $("#chatContent").append(
                                    $("<div class='chat-info'>")
                                    .html( _('users_enter_room', {users: "<span class='username'>"+usernames.join(', ')+"</span>", last_user: "<span class='username'>"+last_user+"</span>"}) )
                                );
                            }
                        }
                    }

                    // users who left the room
                    if(typeof(data.users['to_delete'])!="undefined"){
                        users = data.users.to_delete.sort();
                        for(var i in users) {
                            $("#chat .chatUser[data-uname='"+users[i]+"']").remove();
                            $("#chat a.username[data-uname='"+users[i]+"']").replaceWith(
                                $("<span/>")
                                    .addClass( $("#chat a.username[data-uname='"+users[i]+"']").attr("class") )
                                    .append(users[i])
                            );
                        }
                        // Notification: User has left the room
                        if (!firstGetActions){
                            if (users.length == 1)
                            $("#chatContent").append("<div class='chat-info'>" + _('user_leaves_room', {user: "<span class='username'>"+users[0]+"</span>"}) + "</div>");
                            else if (users.length != 0) {
                                last_user = users.pop();
                                $("#chatContent").append("<div class='chat-info'>" + _('users_leave_room', {users: "<span class='username'>"+users.join(', ')+"</span>", last_user: "<span class='username'>"+last_user+"</span>"}) + "</div>");
                            }
                        }
                    }

                    // Update the chat user counter
                    var newUserNum = $("#userContainer").children().length;
                    if(newUserNum != $("#userCount").text() ) {
                        $("#userCount").text( newUserNum );
                    }
                }

                // handle message data
                if(typeof(data.messages)!="undefined"){

                    // new messages
                    if(typeof(data.messages['new'])!="undefined"){
                        var message = data.messages['new'];
                        for(var i in data.messages['new']) {
                            var mDate = new Date(message[i].date*1000).setSeconds(0, 0);
                            if( options.dateFrequency == "message" || (options.dateFrequency == "minute" && mDate - dateLastMinute >= 60) ) {
                                dateLastMinute = mDate;
                                $("#chatContent").append("<div class='chat-info'><span class='chatdate' data-time='"+message[i].date+"'></span></div>");
                            }
                            $("#chatContent").append(printMessage(message[i]));
                        }
                    }

                    // edited messages
                    if(typeof(data.messages.to_edit)!="undefined"){
                        var messages = data.messages.to_edit;
                        for(var i in messages){
                            $("#chatEntry"+messages[i].id).html(printMessage(messages[i]));
                        }
                    }

                    // deleted messages
                    if(typeof(data.messages.to_delete)!="undefined"){
                        var messages = data.messages.to_delete;
                        for(var i in messages){
                            console.log(messages[i]);
                            $("#chatEntry"+messages[i].id).html(printMessage(messages[i]));
                        }
                    }
                }

                // we potentially added new times, format them
                formatTimes(true);

                if(firstGetActions && options.welcomeMessage){
                    var $message = $("<div id='welcomeMessage' class='chat-info'></div>").text(options.welcomeMessage);
                    $("#chatContent").append($message);
                }

                firstGetActions = false;
                updateCheckBlock = false;

                if (!scrollBlock) {
                    performScrollMode();
                }

                // end of ajax success handling
            })
            .fail(function() {
                updateCheckBlock = false;
                $("#chatMsgSubmit").attr("disabled", "disabled");
                $("#chat .serverError:hidden").fadeIn(400);
            });
        };

        var startUpdateChecker = function() {
            if(typeof(updateIntervalId) != null) {
                clearInterval(updateIntervalId);
            }

            // in case the server doesn't respond,
            // slow down the updateChecker
            var errorTime = (new Date() - lastUpdate) / 2;
            var timeout = Math.max(options.refreshRate, errorTime);

            updateIntervalId = window.setTimeout(function() {
                updateCheck();
                startUpdateChecker();
            }, Math.min(timeout, 10000));
        };

        var stopUpdateChecker = function() {
            if(typeof(updateIntervalId) != null) {
                clearInterval(updateIntervalId);
            }
        }

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
            * whisper_target
        */
        var applyAttributes = function (message, attributes) {
            var message_content = typeof(message)!="undefined" ? message : '',
                additional_content  = '',
                entry_classes = '',
                whisper_target = null,
                admin_message = false;

            if(typeof(attributes)!="undefined"){
                for (var i = 0; i < attributes.length; i++) {
                    if (attributes[i].a_action == 'mod_edit_message') {
                        additional_content += getUnameLink(attributes[i].a_name, { preText: _('message_edited_by') + " ", toAdmin: true });
                        entry_classes += " admin_edit";
                    }
                    if (attributes[i].a_action == 'mod_delete_message') {
                        additional_content = getUnameLink(attributes[i].a_name, { preText: _('message_deleted_by') + " ", toAdmin: true });
                        entry_classes += " admin_delete";
                    }
                    if (attributes[i].admin_message == true) {
                        entry_classes += " admin_message";
                        admin_message = true;
                    }
                    if (attributes[i].whisper_target != null) {
                        whisper_target = attributes[i].whisper_target;
                    }
                }
            }
            return { "entry_classes": entry_classes, "message_content": message_content, "additional_content": additional_content, "whisper_target": whisper_target, "admin_message": admin_message };
        };

        // remove the target chat user
        var removeTarget = function() {
            target = null;
            var $chatMsgValue = $('#chatMsgForm #chatMsgValue');
            $('#chatMsgForm #chatMsgTarget').remove();
            $chatMsgValue.css("padding-top", $chatMsgValue.data("padding-top")).trigger("keyup").focus();
            $("#chatMsgMoreButtons").hide();
        }


        var init = function(i18n) {

            i18n.loadCatalog('tud.addons.chat.js');
            _ = i18n.MessageFactory('tud.addons.chat.js');
            publicVars._ = _;

            jQuery.ajaxSetup({'cache':false});

            $("#chatMsgForm").submit(function(e) {
                e.preventDefault();
                var $btn = $(this).find("button[type=submit]:focus" );
                var method = $btn.data("method");
                sendMessage(method);
            });

            $.post(options.ajaxUrl, {'method': 'resetLastAction'}, function(data){
                if(options.welcomeMessage){
                    updateCheck(options.welcomeMessage);
                }else{
                    updateCheck();
                }
                startUpdateChecker();
            });

            $("#logout").click(function() {
                updateCheckBlock = true;
                $.ajax(
                    {type: "POST",
                    data: {'method': 'logout'},
                    dataType: "text",
                    url: options.ajaxUrl,
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
                if(!$(this).hasClass("username") && !$(e.target.parentNode.parentNode).hasClass('admin_message')){
                    $.notification.warn(_('link_warning_1') + "<br/><br/>" + _('link_warning_2', {link: "<tt>" + e.target.href + "</tt>"}), false,
                        [{"name" :_('button_yes'),
                        "click":function(){
                            window.open(e.target.href,"_blank")
                            $.notification.clear();
                        }},
                        {"name" :_('button_no'), "click": $.notification.clear },
                    ]);
                    e.preventDefault();
                }
            });

            // logic for choosing a chat user as message target
            $('#chat').on('click', '#chatUser li a, a.username', function(e) {
                e.preventDefault();

                // cleanup the old target
                removeTarget();

                target = $(e.target).data("uname");

                var $targetContent = $('<span id="chatMsgTarget">' + _('message_to', {target: target}) + ' <a href="#" class="close"></a></span>');
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
            if(options.maxMessageLength>0){
                $('#chatMsgValue').bind("keypress keyup", function(event){
                    $('#counter').text((options.maxMessageLength-$('#chatMsgValue').val().length) + " / " + options.maxMessageLength);
                });
                $('#chatMsgValue').keypress();
            }

            // auto resize the message input field and handle target deletion
            var $textInput = $("#chatMsgValue"),
                textInputOffset = $textInput[0].offsetHeight - $textInput[0].clientHeight;
            $textInput
                .on('keyup', function() {
                    $(this).css('height', '').css('height', this.scrollHeight + textInputOffset);
                })
                .keydown(function (e) {
                    var key = e.keyCode;
                    // prevent line breaks and send the message instead
                    if(key == 13) {
                        e.preventDefault();
                        sendMessage();
                    }
                    // remove the target on backspace if no text is left
                    if(key == 8 && $textInput.val().length == 0) {
                        removeTarget();
                    }
                });

            // Let chatContent have 0.7 of the websites height
            var chatResize = function() {
                var documentHeight = $(window).height();
                $("#chatContent").height((documentHeight * 0.7));
            }
            $(window).resize(chatResize);
            chatResize();

            // start the time reformat daemon
            startReformatDaemon();
        }

        publicVars.updateCheck = updateCheck;
        return publicVars;
    })();

    global.TudChat = TudChat;

})( this, $ );

