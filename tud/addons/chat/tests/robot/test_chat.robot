*** Settings ***

Resource  keywords.robot

Suite Setup  Setup Suite
Suite Teardown  Teardown Suite

Test Teardown  Teardown Test

*** Keywords ***

Setup Suite
    Open test browser
    Set Window Size  1024  768
    Enable autologin as  Manager
    Setup Dates
    Prepare database connection
    Reload Page

Teardown Suite
    Close all browsers

Teardown Test
    Capture Page Screenshot
    Clear database

Setup Dates
    ${today} =  Get Current Date
    ${DATE_FUTURE_1} =  Add Time To Date  ${today}  2 days   result_format=datetime
    ${DATE_FUTURE_2} =  Add Time To Date  ${today}  3 days   result_format=datetime
    ${DATE_PAST_1} =  Subtract Time From Date  ${today}  2 days  result_format=datetime
    ${DATE_PAST_2} =  Subtract Time From Date  ${today}  1 days  result_format=datetime
    Set Suite Variable  ${DATE_FUTURE_1}
    Set Suite Variable  ${DATE_FUTURE_2}
    Set Suite Variable  ${DATE_PAST_1}
    Set Suite Variable  ${DATE_PAST_2}

*** Test Cases ***

Test Add-menu
    Is In Add-Menu  chat
    Is Not In Add-Menu  chatsession

Test Chat Creation
    Create Chat  Test-Chat
    Set Textarea Field  introduction  Welcome to this chat!
    Save Edit Form
    Page Should Contain  Welcome to this chat!

Test Chat Session Creation
    Add Chat  Test-Chat
    Add Chat Session  Session-1  ${DATE_PAST_1}  ${DATE_FUTURE_1}
    Information Should Contain Text  Changes saved.

Test Showing Future Sessions
    ${location} =  Add Chat  Test-Chat
    Add Chat Session  Session-1  ${DATE_FUTURE_1}  ${DATE_FUTURE_2}
    Go To  ${location}
    Add Chat Session  Session-2  ${DATE_FUTURE_1}  ${DATE_FUTURE_2}
    Go To  ${location}
    Check That No Session Is Active
    Check That Future Session Count Is  2

Test Showing No Past Session
    ${location} =  Add Chat  Test-Chat
    Add Chat Session  Session-1  ${DATE_PAST_1}  ${DATE_PAST_2}
    Go To  ${location}
    Check That No Session Is Active
    Check That Future Session Count Is  0

Test Showing Current Session With Password
    ${location} =  Add Chat  Test-Chat
    Create Chat Session  Session-1  ${DATE_PAST_1}  ${DATE_FUTURE_1}
    Set Text Field  password  secret
    Save Edit Form
    Check That A Session Is Active
    Check That Password Field Is Visible

Test Session Preconditions
    ${location} =  Add Chat  Test-Chat
    Create Chat Session  Session-1  ${DATE_PAST_1}  ${DATE_FUTURE_1}
    Set Text Field  password  secret
    Save Edit Form
    Go To  ${location}
    Try Chat Login And Check For Error  privacy
    Capture Page Screenshot
    Select Checkbox  agreement
    Try Chat Login And Check For Error  password
    Capture Page Screenshot
    Input Text  password  secret
    Input Text  username  t
    Try Chat Login And Check For Error  username
    Capture Page Screenshot
    Input Text  username  test_user
    Wait Until Element Is Enabled  submit
    Click Button  submit
    Chat Window Should Be Visible
    Check User Count  1
    Log Out From Chat Session
    Chat Window Should Not Be Visible

Test Chat Message Manipulation
    ${location} =  Add Chat  Test-Chat
    Add Chat Session  Session-1  ${DATE_PAST_1}  ${DATE_FUTURE_1}
    Go To  ${location}
    Log In Into Chat Session  test_user
    Send Chat Message  test1
    Edit Chat Message  1  test2
    Check That Message Text Is  1  test2
    Delete Chat Message  1
    Check That Message Contains No Text  1
