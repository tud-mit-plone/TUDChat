from _mysql_exceptions import OperationalError

from zope.component.hooks import getSite
from transaction import commit

from plone.app.robotframework.remote import RemoteLibrary

class DatabaseHelper(RemoteLibrary):
    """
    This class provides helper methods to create a database object and to clear a database.
    """

    def zmysql_add_object(self, zmysql_id, db_server, db_user, db_password, db_name):
        """
        Adds zmysql object inside plone site root to provide database access.

        :param zmysql_id: id of zmysql object, which have to be created
        :type zmysql_id: str
        :param db_server: address of database server
        :type db_server: str
        :param db_user: name of database user
        :type db_user: str
        :param db_password: password of given database user
        :type db_password: str
        :param db_name: name of database
        :type db_name: str
        """

        title = 'Z MySQL Database Connection'
        connection_string = "{}@{} {} {}".format(db_name, db_server, db_user, db_password)

        site = getSite()
        try:
            site.manage_addProduct['ZMySQLDA'].manage_addZMySQLConnection(zmysql_id, title, connection_string, check = True, use_unicode = True, auto_create_db = True)
        except OperationalError as e:
            msg = e.args[1] + "\n"
            msg += "Hint: You can define environment variables DB_SERVER, DB_USER, DB_PASSWORD and DB_NAME to configure your database connection."
            raise Exception(msg)

        commit()

    def zmysql_clear_database(self, zmysql_id):
        """
        Removes all tables in database of zmysql object, which is determined from given zmysql id.

        :param zmysql_id: id of zmysql object, whose database is to be cleared
        :type zmysql_id: str
        """
        site = getSite()
        zmysql = getattr(site, zmysql_id, None)
        if zmysql is None:
            raise Exception('Z MySQL object not found!')

        dbc = zmysql()

        tables = [table['table_name'] for table in dbc.tables() if table['table_type'] == 'table']

        for table in tables:
            dbc.query('DROP TABLE {}'.format(table.encode('utf-8')))
