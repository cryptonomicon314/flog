from flask.ext.script import Manager, Command, Option

from config import POSTGRESQL_DBNAME, POSTGRESQL_PASSWORD, POSTGRESQL_USERNAME

import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('action')

def dbserver(args):
    action = args.action
    if action in ['start', 'stop']:
        subprocess.call(['sudo', 'service', 'postgresql', 'start'])
    elif action == 'create':
        subprocess.call(['sudo', '-u', 'postgres', 'createdb', POSTGRESQL_DBNAME, '-O', POSTGRESQL_USERNAME])
    elif action == 'delete':
        subprocess.call(['sudo', '-u', 'postgres', 'dropdb', POSTGRESQL_DBNAME])
    elif action is not None:
        print ("\n" +\
               "   Invalid command '{}'\n".format(args.action) +\
               "   'python dbserver.py --help' lists available commmands" +\
               "\n")

args = parser.parse_args()
dbserver(args)
