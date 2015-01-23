from flask.ext.script import Manager, Command, Option

from config import POSTGRESQL_DBNAME, POSTGRESQL_PASSWORD, POSTGRESQL_USERNAME

import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('action')

set_password_cmd = \
  'sudo -u postgres psql -c "ALTER USER {username} WITH PASSWORD \'{password}\';"'

set_db_owner_cmd = \
  'sudo -u postgres psql -c "ALTER DATABASE {dbname} OWNER TO {new_owner}"'

def createuser():
    return subprocess.call(['sudo', '-u', 'postgres', 'createuser', '-s', '-e', POSTGRESQL_USERNAME])

def dropuser():
    return subprocess.call(['sudo', '-u', 'postgres', 'dropuser', POSTGRESQL_USERNAME])

def set_user_password():
    return subprocess.call(set_password_cmd.format(username=POSTGRESQL_USERNAME,
                                                   password=POSTGRESQL_PASSWORD),
                           shell=True)

def set_db_owner():
    return subprocess.call(set_db_owner_cmd.format(dbname=POSTGRESQL_DBNAME,
                                                   new_owner=POSTGRESQL_USERNAME),
                           shell=True)

def createdb():
    return subprocess.call(['sudo', '-u', 'postgres', 'createdb', POSTGRESQL_DBNAME, '-O', POSTGRESQL_USERNAME])

def dropdb():
    return subprocess.call(['sudo', '-u', 'postgres', 'dropdb', POSTGRESQL_DBNAME])

def service(action):
    return subprocess.call(['sudo', 'service', 'postgresql', action])

#def start(): return service('start')
#def stop(): return service('stop')

def dbserver(args):
    action = args.action
    if action in ['start', 'stop']:
        service(action)
    elif action == 'createdb':
        return createdb()
    elif action == 'dropdb':
        return dropdb()
    elif action == 'createuser':
        createuser()
        set_user_password()
    elif action == 'dropuser':
        dropuser()
    elif action == 'setup':
        service('start')
        # Try creating a user.
        createuser()
        # Set the new user password.
        set_user_password()
        # Try to create a new DB.
        createdb()
        set_db_owner()



    elif action is not None:
        print ("\n" +\
               "   Invalid command '{}'\n".format(args.action) +\
               "   'python dbserver.py --help' lists available commmands" +\
               "\n")


args = parser.parse_args()
dbserver(args)
