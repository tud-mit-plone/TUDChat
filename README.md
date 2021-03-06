# tud.addons.chat

## Introduction
This repository contains tud.addons.chat, which is a chat Add-On for [Plone](https://plone.org/). It allows you to setup time restricted chat sessions, which can be moderated by privileged Plone users.
The product can be used either with archetypes content types or with dexterity content types.

Features:
*  Password protection for chat sessions
*  User count limit for chat sessions
*  Whisper messages
*  Show recent messages after entering a chat session
*  Chat session welcome message
*  Anonymized chat log
*  Moderation of chat sessions
  *  Kick and ban users with an optional message
  *  Warn users with a message
  *  Edit and delete chat messages


## How to install
To use this product with the default database engine you have to install a [MySQL](https://www.mysql.com/) server.
After the database server installation create a new database.

In order to install this product, copy the product files to the "src" directory and add the product in the buildout configuration:
```
eggs =
    ...
    tud.addons.chat

develop =
   ...
   src/tud.addons.chat
```

To install the Plone 4 version write `tud.addons.chat[plone4]` in the 'eggs' area.

Furthermore "collective.beaker" has to be configured. Here is an example configuration:
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

To run chat specific tasks like archiving chat sessions you should execute the script [tud/addons/chat/cron.py](./tud/addons/chat/cron.py) once a day.
The following crontab template could be used (it is advisable to use an instance that does not run regularly):
```
0 4 * * * ${installdir}/bin/${instance_bin} run ${installdir}/src/tud.addons.chat/tud/addons/chat/cron.py --do --site ${site_id} > /dev/null
```

After these steps you can start your instance and install the chat product. For the installation are an archetypes and a dexterity profile available.
Before you can add chat objects in Plone, you have to add a database connection object (inside the ZODB the database object must be located above the chat objects, e.g. your site root):
*   Open the Zope Management Interface at the position you want to add the object in your browser.
*   Add an object of type "Z MySQL Database Connection":
  *  Enter an id (which is later needed for configuration of chat objects)
  *  Enter the "Database Connection String", which contains all data needed for the database communication
  *  Enable "Unicode support"

Now you can add chat objects, which refer to your newly created database object.

## Dependencies
The following dependencies are defined in the [setup.py](./setup.py) of the product
*   **plone.api** – provides simple and clear API for Plone
*   **Products.ZMySQLDA** – allows communication with MySQL databases
*   **collective.beaker** – provides session and cache handling
*   **python-dateutil** – provides extensions for standard datetime module
*   **jarn.jsi18n** – allows internationalization in JavaScript (optional, needed in Plone 4)

## Tests
This product contains robot tests for browser based integration tests to ensure low production bug rates. If you want to run the tests, you need a running MySQL server.
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

Currently no tests exist for dexterity content types.

## Documentation
To learn more about the product you can read the following documents:
*  [database.md](./docs/database.md)
*  [architecture.md](./docs/architecture.md)

## Credits
We use icons from Bdate Kaspar/Franziska Sponsel:
*  URL: http://findicons.com/pack/977/rrze
*  License:  Creative Commons Attribution (by)
