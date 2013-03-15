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

    def __init__(self, cluster_name, instance_type, boto_instances, username = None, keypair = None):
        self.cluster_name = cluster_name
        self.instance_type = instance_type
        self.instances = [Instance(boto_instance, username, keypair)
                          for boto_instance in boto_instances]

    def add(self, boto_instances):
        """
        Add extra instances to the cluster.
        """
        self.instances.extend(
            [Instance(boto_instance) for boto_instance in boto_instances])

    def show(self):
        """
        Print the details of cluster `cluster_name` to stdout.
        """
        print "Displaying instances from cluster: %s" % self.cluster_name
        print "Instances of type: %s" % self.cluster.instance_type
        print "{0:8}{1:13}{2:35}".format(
            "index", "EC2 id", "public dns name")
        for (j, instance) in enumerate(self.instances):
            print "{0:8}{1:13}{2:35}".format(
                str(j), instance.id, instance.public_dns_name)

    def ssh(self, cmd, background=False):
        """
        Run `cmd` on all instances in `cluster_name`.
        """
        output = ''
        for inst in self.instances:
            print inst.public_dns_name, cmd
            output += inst.ssh(cmd, background)
        return output


    def scp_put(self, localpath, remotepath):
        for inst in self.instances:
            print inst.public_dns_name, remotepath
            inst.scp_put(localpath, remotepath)

    def scp_get(self, remotepath, localpath):
        for inst in self.instances:
            print inst.public_dns_name, remotepath
            inst.scp_get(remotepath, localpath)

class Instance():
    """
    Instance objects represent EC2 instances in a Cluster object.  As
    with Cluster, this class does relatively little, it exists mostly
    to encapsulate the data structures used to represent instances.
    """

    def __init__(self, boto_instance, username = None, keypair = None):
        self.id = boto_instance.id
        self.public_dns_name = boto_instance.public_dns_name
        self.transport = None
        self.username = username
        self.keypair = keypair

    def init_ssh(self):
        if self.transport == None:
            self.sshClient = paramiko.SSHClient()
            self.sshClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.sshClient.connect(hostname=self.public_dns_name, username=self.username, key_filename=self.keypair)
            # self.sshClient.exec_command('uname')
            self.transport = self.sshClient.get_transport()
            self.sftp = paramiko.SFTPClient.from_transport(self.transport)
        return self.transport

    def ssh(self, cmd, background=False):
        self.init_ssh()
        bg = ''
        if background:
            self.sshClient.exec_command(cmd + ' &')
            return ''
        else:
            stdin, stdout, stderr = self.sshClient.exec_command(cmd)
            data = stdout.read() + stderr.read()
            return data

    def scp_put(self, localpath, remotepath):
        self.init_ssh()
        self.sftp.put(localpath, remotepath)

    def scp_get(self, remotepath, localpath):
        self.init_ssh()
        self.sftp.get(remotepath, localpath)
