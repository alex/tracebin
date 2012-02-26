from fabric.api import local


def deploy():
    local("./manage.py development collectstatic --noinput")
    local("epio upload")
