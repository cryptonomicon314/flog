import yaml
import os
import subprocess
import argparse

basedir = os.path.dirname(os.path.realpath(__file__))
local_secrets_output = os.path.dirname(basedir) + '/data/app/secrets'

secrets_dirpath = os.path.join(basedir, 'secrets')
remote_secrets_path = os.path.join(secrets_dirpath, 'remote.yaml')
local_secrets_path = os.path.join(secrets_dirpath, 'local.yaml')

appname = yaml.safe_load(open(remote_secrets_path).read())['appname']

rhc_ssh = 'rhc ssh {appname} "mkdir -p app-root/data/app/secrets/"'.format(appname=appname)
rhc_scp = 'rhc scp {appname} upload {remote_secrets_path} app-root/data/app/secrets/'.format(
               appname=appname, remote_secrets_path=remote_secrets_path)

def deploy_remote():
    print "Deploying remote secrets..."
    print "Create secrets dir (if it doesn't exist)..."
    out = subprocess.check_output(rhc_ssh, shell=True)
    print out
    print "Copy remote secrets..."
    out = subprocess.check_output(rhc_scp, shell=True)
    print out

def deploy_local():
    print "Deploy local secrets"
    subprocess.call(['mkdir', '-p', local_secrets_output])
    subprocess.call(['cp', local_secrets_path, local_secrets_output])

parser = argparse.ArgumentParser(description="Deploy the app secrets.")
parser.add_argument('--remote', action='store_const', const=True, default=False)
parser.add_argument('--local',  action='store_const', const=True, default=False)


if __name__ == "__main__":
    args = parser.parse_args()
    remote, local = args.remote, args.local
    # either both true or both false:
    if remote == local:
        deploy_local()
        deploy_remote()
    elif remote:
        deploy_remote()
    elif local:
        deploy_local()
