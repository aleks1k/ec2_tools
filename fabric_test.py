__author__ = 'Alexey'
# from fabric.api import run, local, env, put, roles
# env.roledefs['production'] = ["ec2-user@poisknomera.ru"]
# env.hosts = ["ec2-user@poisknomera.ru"]
# env.show = ['debug']
# # env.host = "ec2-user@poisknomera.ru"
# env.key_filename = 'D:\Documents\Dropbox\Backup\AWS2013.ppk'
#
# @roles('production')
# def deploy():
#     print "Deploying...";
#     run("ls")
#     put("fabtest.txt", "/tmp/fabtest.txt");
#     print "All Done...";
#
# deploy()

from fabric.api import env
from fabric.api import run

class FabricSupport:
    def __init__ (self, host):
        self.host = host
        pass

    def run(self, command):
        env.host_string = self.host
        env.key_filename = 'D:\Documents\Dropbox\Backup\AWS2013.pem'
        run(command)

myfab = FabricSupport("ec2-user@poisknomera.ru:22")

myfab.run('uname -a')
