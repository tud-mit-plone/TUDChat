# tud.addons.chat

## Introduction
This repository contains the plone chat product. It allows you to set up time restricted chat sessions that can be moderated by privileged plone users.

Features:
*  Password protection for chat sessions
*  User limitation for chat sessions
*  Whisper messages
*  Show recent messages after entering a chat session
*  Chat session welcome message
*  Anonymized chat log
*  Moderation of chat sessions
    *  Kick and ban users with optional message
    *  Warn users with a message
    *  Edit and delete chat messages


## How to install
To use this product with the default database engine you have to install a [mysql](https://www.mysql.com/) server.
After database server installation create a database for chat purposes.

In order to install this product, copy the product files to the "src" directory and add the product in the buildout configuration:
```
eggs =
    ...
    tud.addons.chat

develop =
   ...
   src/tud.addons.chat
```

For plone 4 write `tud.addons.chat[plone4]` in 'eggs' area.

Furthermore "collective.beaker" has to be configured. A development configuration can look like this:
```
[instance]
...
zope-conf-additional =
    <product-config beaker>
    session.type file
    </product-config>
```
For more details see: http://beaker.readthedocs.io/en/latest/

Now you can start the buildout process.

To run chat specific tasks, like archiving chat sessions, you should execute the script [tud/addons/chat/cron.py](./tud/addons/chat/cron.py) once per day.
The following crontab template can be used (adapt it to use an instance that does not run regularly):
```
0 4 * * * ${installdir}/bin/${instance_bin} run ${installdir}/src/tud.addons.chat/tud/addons/chat/cron.py --do --site ${site_id} > /dev/null
```

After these steps you can start your instance and install the chat product.
Before you can add chat objects in plone, you have to add a database object (database object must be located in a sub-path of the chat objects, e.g. your site root):
*   Open the zope management interface at the position you want to add the object in your browser.
*   Add an object of type "Z MySQL Database Connection":
    *  Enter an id (is later needed for configuration of chat objects)
    *  Enter the "Database Connection String", which contains all data needed for database communication
    *  Enable "Unicode support"

Now you can add chat objects, which will refer to your newly created database object.

## Dependencies
The following dependencies are defined in the [setup.py](./setup.py) of this product
*   **plone.api** – provides simple and clear api for plone
*   **Products.ZMySQLDA** – allows communication with mysql databases
*   **collective.beaker** – provides session and cache handling
*   **python-dateutil** – provides extensions for standard datetime module
*   **jarn.jsi18n** – allows internationalization in javascript (optional, needed in plone 4)

## Tests
This product contains robot tests for browser based integration tests to ensure low production bug rates. If you want to run the tests you need a running mysql server.
The tests use this default database configuration
*  server: localhost
*  username: chattest
*  password: chattest
*  database name: chattest

To define your custom configuration you can set the following environment variables before running the tests
*  DB_SERVER
*  DB_USER
*  DB_PASSWORD
*  DB_NAME

## Documentation
To learn more about the product read the following documents:
*  [database](./docs/database.md)
*  [architecture](./docs/architecture.md)

## Credits
We use icons from Bdate Kaspar/Franziska Sponsel:
*  URL: http://findicons.com/pack/977/rrze
*  License:  Creative Commons Attribution (by)
