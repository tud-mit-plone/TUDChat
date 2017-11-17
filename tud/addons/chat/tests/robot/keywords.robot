*** Settings ***

Resource  plone/app/robotframework/keywords.robot
Resource  plone/app/robotframework/selenium.robot

Library  OperatingSystem
Library  DateTime
Library  Remote  ${PLONE_URL}/RobotRemote

*** Variables ***

${DB_ID}  chatdb
${DB_PREFIX}  test

*** Keywords ***

#------------------------------------------------------------------------------
# Database keywords
#------------------------------------------------------------------------------

Prepare database connection
    [Arguments]
    ${db_server} =  Get Environment Variable  DB_SERVER  localhost
    ${db_user} =  Get Environment Variable  DB_USER  chattest
    ${db_password} =  Get Environment Variable  DB_PASSWORD  chattest
    ${db_name} =  Get Environment Variable  DB_NAME  chattest
    Zmysql Add Object  ${DB_ID}  ${db_server}  ${db_user}  ${db_password}  ${db_name}

Clear Database
    Zmysql Clear Database  ${DB_ID}

#------------------------------------------------------------------------------
# Content creation keywords
#------------------------------------------------------------------------------

Create Chat
    [Arguments]  ${title}
    Create Content  chat
    Set Text Field  title  ${title}
    Set Text Field  connector_id  ${DB_ID}
    Set Text Field  database_prefix  ${DB_PREFIX}

Add Chat
    [Arguments]  ${title}
    Create Chat  ${title}
    ${location} =  Save Edit Form
    [Return]  ${location}

Create Chat Session
    [Arguments]  ${title}  ${start}  ${end}
    Create Content  chatsession
    Set Text Field  title  ${title}
    Set Date Field  start_date  ${start}
    Set Date Field  end_date  ${end}

Add Chat Session
    [Arguments]  ${title}  ${start}  ${end}
    Create Chat Session  ${title}  ${start}  ${end}
    ${location} =  Save Edit Form
    [Return]  ${location}

Create Content
    [Arguments]  ${content_type}  ${title}=
    Open add new menu
    Click Link  css=#plone-contentmenu-factories a.contenttype-${content_type}

    Page Should Contain Element  css=#archetypes-fieldname-title input
    Set Text Field  title   ${title}

Save Edit Form
    Click button  name=form.button.save
    # now with waiting to make sure the info got inserted
    Wait Until Page Contains  Changes saved.
    ${location} =  Get Location
    [Return]  ${location}

Set Text Field
    [Documentation]  Enter content into a given text field.
    [Arguments]  ${fieldname}  ${content}
    Page Should Contain Element  css=#archetypes-fieldname-${fieldname} input
    Input Text  ${fieldname}  ${content}

Set Textarea Field
    [Documentation]  Enter content into a given textarea
    [Arguments]  ${fieldname}  ${content}
    Page Should Contain Element  css=#archetypes-fieldname-${fieldname} textarea
    Input Text  ${fieldname}  ${content}

Set Date Field
    [Arguments]  ${fieldname}  ${date}
    Page Should Contain Element  css=#archetypes-fieldname-${fieldname}
    ${year} =  Convert To String  ${date.year}
    ${month} =  Convert To String  ${date.month}
    ${day} =  Convert To String  ${date.day}
    ${minute} =  Round 0_5  ${date.minute}
    ${minute} =  Convert To String  ${minute}
    Select From List By Value  css=#archetypes-fieldname-${fieldname} select[name='${fieldname}_year']  ${year}
    Select From List By Value  css=#archetypes-fieldname-${fieldname} select[name='${fieldname}_month']  ${month.zfill(2)}
    Select From List By Value  css=#archetypes-fieldname-${fieldname} select[name='${fieldname}_day']  ${day.zfill(2)}
    Select From List By Value  css=#archetypes-fieldname-${fieldname} select[name='${fieldname}_hour']  ${date.strftime('%I')}
    Select From List By Value  css=#archetypes-fieldname-${fieldname} select[name='${fieldname}_minute']  ${minute.zfill(2)}
    Select From List By Value  css=#archetypes-fieldname-${fieldname} select[name='${fieldname}_ampm']  ${date.strftime('%p')}

#------------------------------------------------------------------------------
# Start page keywords
#------------------------------------------------------------------------------

Check That A Session Is Active
    Page Should Contain Element  css=form.chat_login

Check That No Session Is Active
    Page Should Not Contain Element  css=form.chat_login
    Page Should Contain Element  css=p.chat_nosession

Check That Future Session Count Is
    [Arguments]  ${count}
    Locator Should Match X Times  css=table.future_sessions tbody tr  ${count}

Check That Password Field Is Visible
    Page Should Contain Element  css=form.chat_login input#password

Log In Into Chat Session
    [Arguments]  ${username}  ${password}=${EMPTY}
    Input Text  username  ${username}
    Run Keyword If  '${password}'  Input Text  password  ${password}
    Select Checkbox  agreement
    Click Button  submit

Try Chat Login And Check For Error
    [Arguments]  ${error_text}
    Wait Until Element Is Enabled  submit
    Click Button  submit
    Error Should Contain Text  ${error_text}

#------------------------------------------------------------------------------
# Chat keywords
#------------------------------------------------------------------------------

Chat Window Should Be Visible
    Wait Until Element Is Visible  css=#chat

Chat Window Should Not Be Visible
    Wait Until Element Is Not Visible  css=#chat

Check User Count
    [Arguments]  ${count}
    Locator Should Match X Times  css=#chatUser span.username  ${count}

Check Message Count
    [Arguments]  ${count}
    Locator Should Match X Times  css=#chatContent span.message_content  ${count}

Log Out From Chat Session
    Click Button  logout

Send Chat Message
    [Arguments]  ${message}
    Input Text  chatMsgValue  ${message}
    Click Button  chatMsgSubmit

Edit Chat Message
    [Arguments]  ${id}  ${new_message}
    Click Link  css=#chatEntry${id} a.edit
    Wait Until Element Is Visible  newMsg
    Input Text  newMsg  ${new_message}
    Click Button  css=.notification_button:first-child
    Wait Until Element Is Not Visible  css=.notification_button:first-child

Delete Chat Message
    [Arguments]  ${id}
    Click Link  css=#chatEntry${id} a.delete
    Wait Until Element Is Visible  css=.notification_button:first-child
    Click Button  css=.notification_button:first-child
    Wait Until Element Is Not Visible  css=.notification_button:first-child

Check That Message Text Is
    [Arguments]  ${id}  ${message}
    Element Text Should Be  css=#chatEntry${id} span.message  ${message}

Check That Message Contains No Text
    [Arguments]  ${id}
    Check That Message Text Is  ${id}  ${EMPTY}

#------------------------------------------------------------------------------
# Other keywords
#------------------------------------------------------------------------------

Close Menu
    [Documentation]  Close a menu identified by id attribute in DOM.
    [Arguments]  ${elementId}
    Element Should Be Visible  css=dl#${elementId} span
    Element Should Be Visible  css=dl#${elementId} dd.actionMenuContent
    Click link  css=dl#${elementId} dt.actionMenuHeader a
    Wait until keyword succeeds  1  5  Element Should Not Be Visible  css=dl#${elementId} dd.actionMenuContent

Close Add-Menu
    [Documentation]  Test if Add-Menu is visible and close it
    Close Menu  plone-contentmenu-factories

Is In Add-Menu
    [Arguments]  ${content_type}
    Open Add New Menu
    Capture Page Screenshot
    Page Should Contain Element  xpath=//a[@id='${content_type}']
    Close Add-Menu

Is Not In Add-Menu
    [Arguments]  ${content_type}
    Open Add New Menu
    Capture Page Screenshot
    Page Should Not Contain Element  xpath=//a[@id='${content_type}']
    Close Add-Menu

Information Should Contain Text
    [Documentation]  Check for a substring within info portal messages.
    [Arguments]  ${text}
    Page Should Contain Element  xpath=//dl[contains(@class, 'portalMessage') and contains(@class, 'info')]/dd[contains(text(), '${text}')]

Error Should Contain Text
    [Documentation]  Check for a substring within error portal messages.
    [Arguments]  ${text}
    Page Should Contain Element  xpath=//dl[contains(@class, 'portalMessage') and contains(@class, 'error')]/dd[contains(text(), '${text}')]

Round 0_5
    [Documentation]  Rounds rightmost digit to 0 or 5 (examples: 12 will be round to 10, 43 will be round to 45)
    [Arguments]  ${number}
    ${res} =  Evaluate  int(5 * round(float($number)/5))
    [Return]  ${res}
