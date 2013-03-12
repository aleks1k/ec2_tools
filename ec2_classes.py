"""
ec2_classes.py
~~~~~~~~~~~~~~

Defines the Cluster and Instance classes used by `ec2.py`.  
"""

# Why are these classes stored in a separate module from ec2.py?
#
# These classes are put in a separate module because ec2.py stores
# instances of these classes by pickling (through shelves).  Pickling
# classes defined within ec2.py creates namespace problems that can be
# solved by putting the class definitions into a separate module. See:
#
# http://stackoverflow.com/questions/3614379/attributeerror-when-unpickling-an-object

#### Cluster and Instance classes
import paramiko


class Cluster():
    """
    Cluster objects represent a named EC2 cluster.  This class does
    relatively little, it exists mostly to encapsulate the data
    structures used to represent clusters.
    """

    def __init__(self, cluster_name, instance_type, boto_instances):
        self.cluster_name = cluster_name
        self.instance_type = instance_type
        self.instances = [Instance(boto_instance) 
                          for boto_instance in boto_instances]

    def add(self, boto_instances):
        """
        Add extra instances to the cluster.
        """
        self.instances.extend(
            [Instance(boto_instance) for boto_instance in boto_instances])

class Instance():
    """
    Instance objects represent EC2 instances in a Cluster object.  As
    with Cluster, this class does relatively little, it exists mostly
    to encapsulate the data structures used to represent instances.
    """

    def __init__(self, boto_instance):
        self.id = boto_instance.id
        self.public_dns_name = boto_instance.public_dns_name
        self.transport = None

    def init_ssh(self, username, keypair):
        if self.transport == None:
            self.username = username
            self.keypair = keypair

            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(hostname=self.public_dns_name, username=self.username, key_filename=self.keypair)
            self.ssh.exec_command('uname')
            self.transport = self.ssh.get_transport()
            self.sftp = paramiko.SFTPClient.from_transport(self.transport)

        return self.transport

    def ssh_cmd(self, cmd):
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        data = stdout.read() + stderr.read()
        return data

    def scp_put(self, localpath, remotepath):
        return self.sftp.put(localpath, remotepath)

    def scp_get(self, remotepath, localpath):
        return self.sftp.get(remotepath, localpath)
