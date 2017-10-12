"""Admin management service."""
from sql.utils import create_all_tables, session_scope
from sql.tables import Users


class Admins(object):
    """
    Admin management Service.

    Service for listing and setting current system
    administrators.
    """

    exposed = True

    def __init__(self, dburl, template_env):
        """
        Initialisation.

        Args:
            dburl (str): The URL of the users DB
            template_env (jinja2.Environment): The jinja2 html templating engine
                                               environment. This contains the html
                                               root dir with the templates below it.
        """
        self._users_dburl = create_all_tables(dburl)
        self._template_env = template_env

    def GET(self):  # pylint: disable=invalid-name
        """
        REST GET Method.

        Returns:
            str: The rendered HTML containing the users admin status as toggles.
        """
        with session_scope(self._users_dburl) as session:
            return self._template_env.get_template('html/admins.html')\
                                     .render({'users': [session.query(Users).all()]})

    def PUT(self, user_id, admin):  # pylint: disable=invalid-name
        """
        REST PUT Method.

        Args:
            user_id (str): The id number of the user to modify
            admin (str): The status of the admin flag true/false
                         (note passed through un-capitalised.)
        """
        print "IN PUT(Admins)", user_id, admin
        # could use ast.literal_eval(admin.capitalize()) but not sure if I trust it yet
        admin = (admin.lower() == 'true')
        with session_scope(self._users_dburl) as session:
            session.query(Users).filter_by(id=int(user_id)).update({'admin': admin})
