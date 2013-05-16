# -*- coding: utf-8 -*-
"""
ec2.py
~~~~~~

Simple EC2 cluster management with Python, designed to make it easy to
name and work with clusters, and to integrate with `fabric`.  

For usage information see README.md.
"""

#### Library imports

# Standard library
import os
import shelve
import subprocess
import sys
import time

# Third party libraries
from boto.ec2.connection import EC2Connection
import boto.ec2
import paramiko
# My libraries
import ec2_classes
import aws_settings
#### Constants and globals
class ClusterManager():
    regions = aws_settings.regions
    USER = aws_settings.USER
    AWS_HOME = aws_settings.AWS_HOME
    AWS_KEYPAIR = aws_settings.AWS_KEYPAIR
    AWS_ACCESS_KEY_ID  = ""
    AWS_SECRET_ACCESS_KEY = ""

    def __init__(self, key_id, access_key, region_id = 0):
        if not os.path.exists(self.AWS_HOME):
            os.mkdir(self.AWS_HOME)
        self.AWS_ACCESS_KEY_ID = key_id
        self.AWS_SECRET_ACCESS_KEY = access_key
        region = self.regions[region_id]
        if 'keypair' in region:
            self.AWS_KEYPAIR = region['keypair']
        self.AMIS = region['amis']
        print 'Use %s region' % region['name']

        # EC2 connection object
        ec2_regions = boto.ec2.regions(aws_access_key_id=self.AWS_ACCESS_KEY_ID, aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY)
        self.ec2_conn = ec2_regions[region['id']].connect(aws_access_key_id=self.AWS_ACCESS_KEY_ID, aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY)

        self.get_key(self.AWS_KEYPAIR)

        self.clusters = None
        self.cluster_db_file = "%s/.ec2-%s-shelf" % (self.AWS_HOME, region['name'])

    def get_key(self, key_name):
    # Check to see if specified keypair already exists.
    # If we get an InvalidKeyPair.NotFound error back from EC2,
    # it means that it doesn't exist and we need to create it.
        try:
            key = self.ec2_conn.get_all_key_pairs(keynames=[key_name])[0]
        except self.ec2_conn.ResponseError, e:
            if e.code == 'InvalidKeyPair.NotFound':
                print 'Creating keypair: %s' % key_name
                # Create an SSH key to use when logging into instances.
                key = self.ec2_conn.create_key_pair(key_name)

                # Make sure the specified key_dir actually exists.
                # If not, create it.
                # key_dir = os.expanduser(key_dir)
                # key_dir = os.expandvars(key_dir)
                # if not os.path.isdir(key_dir):
                #     os.mkdir(key_dir, 0700)

                # AWS will store the public key but the private key is
                # generated and returned and needs to be stored locally.
                # The save method will also chmod the file to protect
                # your private key.
                key.save(self.AWS_HOME)
            else:
                raise
        return key

    #### The following are the functions corresponding to the command line
    #### API calls: create, show, show_all etc.
    def create(self, cluster_name, n, instance_type = 't1.micro'):
        """
        Create an EC2 cluster with name `cluster_name`, and `n` instances
        of type `instance_type`.  Update the `clusters` shelf to include a
        description of the new cluster.
        """
        # Parameter check
        if self.exists(cluster_name):
            print ("A cluster with name %s already exists.  Exiting."
                   % cluster_name)
            return self.get_cluster(cluster_name)
        if n < 1 or n > 20:
            print "Clusters must contain between 1 and 20 instances.  Exiting."
            return None

        clusters = self.get_clusters()
        if not instance_type in self.AMIS:
            print "Instance type not recognized, setting it to be 'm1.small'."
            instance_type = 't1.micro'
        # Create the EC2 instances
        instances = self.create_ec2_instances(n, instance_type)
        keypair_filename = "%s/%s.pem" % (self.AWS_HOME, self.AWS_KEYPAIR)
        # Update clusters
        clusters[cluster_name] = ec2_classes.Cluster(cluster_name, instance_type, instances, username = self.USER, keypair = keypair_filename)
        clusters.sync()
        return clusters[cluster_name]

    def show(self):
        """
        Print the details of all clusters to stdout.
        """
        clusters = self.get_clusters()
        if len(clusters) == 0:
            print "No clusters present."
        else:
            print "Showing all clusters."
            for cluster in clusters:
                cluster.show()

    def shutdown(self, cluster_name):
        """
        Shutdown all EC2 instances in ``cluster_name``, and remove
        ``cluster_name`` from the shelf of clusters.
        """
        if not self.exists(cluster_name):
            print "No cluster with that name."
            return
        print "Shutting down cluster %s." % cluster_name
        clusters = self.get_clusters()
        self.ec2_conn.terminate_instances(
            [instance.id for instance in clusters[cluster_name].instances])
        del clusters[cluster_name]
        clusters.sync()

    def shutdown_all(self):
        """
        Shutdown all EC2 instances in all clusters, and remove all
        clusters from the `clusters` shelf.
        """
        clusters = self.get_clusters()
        if len(clusters) == 0:
            print "No clusters to shut down.  Exiting."
            clusters.sync()
        for cluster_name in clusters:
            self.shutdown(cluster_name)
        clusters.sync()

    def kill(self, cluster_name, instance_index):
        """
        Shutdown instance `instance_index` in cluster `cluster_name`, and
        remove from the clusters shelf.  If we're killing off the last
        instance in the cluster then it runs `shutdown(cluster_name)`
        instead.
        """
        cluster = self.get_cluster(cluster_name)
        instance = cluster.instances[instance_index]
        if len(cluster.instances) == 1:
            print "Last machine in cluster, shutting down entire cluster."
        print ("Shutting down instance %s on cluster %s." %
               (instance_index, cluster_name))
        self.ec2_conn.terminate_instances([instance.id])
        del cluster.instances[instance_index]
        clusters = self.get_clusters()
        clusters[cluster_name] = cluster
        clusters.sync()

    def add(self, cluster_name, n):
        """
        Add `n` instances to `cluster_name`, of the same instance type as
        the other instances already in the cluster.
        """
        cluster = self.get_cluster(cluster_name)
        if n < 1:
            print "Must be adding at least 1 instance to the cluster.  Exiting."
            sys.exit()
        # Create the EC2 instances
        instances = self.create_ec2_instances(n, cluster.instance_type)
        # Update clusters
        cluster.add(instances)
        clusters = self.get_clusters()
        clusters[cluster_name] = cluster
        clusters.sync()

    #### Helper functions
    def create_ec2_instances(self, n, instance_type):
        """
        Create an EC2 cluster with `n` instances of type `instance_type`.
        Return the corresponding boto `reservation.instances` object.
        This code is used by both the `create` and `add` functions, which
        is why it was factored out.
        """
        ami = self.AMIS[instance_type]
        image = self.ec2_conn.get_all_images(image_ids=[ami])[0]
        reservation = image.run(
            n, n, self.AWS_KEYPAIR, instance_type=instance_type)
        for instance in reservation.instances:  # Wait for the cluster to come up
            while instance.update()== u'pending':
                time.sleep(1)
        return reservation.instances

    def get_clusters(self):
        if self.clusters == None:
            self.clusters = shelve.open(self.cluster_db_file, writeback=True)
        return self.clusters

    def get_cluster(self, cluster_name):
        """
        Check that a cluster with name `cluster_name` exists, and return
        the corresponding Cluster object if so.
        """
        clusters = self.get_clusters()
        if cluster_name not in clusters:
            print "No cluster with the name %s exists.  Exiting." % cluster_name
            # clusters.close()
            return None
        cluster = clusters[cluster_name]
        # clusters.close()
        return cluster

    def exists(self, cluster_name):
        """
        Return ``True`` if an EC2 cluster with name ``cluster_name`` exists, and
        ``False`` otherwise.
        """
        value = cluster_name in self.get_clusters()
        return value

    def size(self, cluster_name):
        """
        Return the size of the cluster with name ``cluster_name``.
        """
        return len(self.get_cluster(cluster_name).instances)

# #### External interface TODO
if __name__ == "__main__":
    args = sys.argv[1:]
    l = len(args)
    try:
        cmd = args[0]
    except:
        cmd = None
    if "AWS_ACCESS_KEY_ID" in os.environ and "AWS_SECRET_ACCESS_KEY" in os.environ:
        ec2 = ClusterManager(os.environ["AWS_ACCESS_KEY_ID"], os.environ["AWS_SECRET_ACCESS_KEY"])
    else:
        print "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY not found"
        exit()
    if "AWS_HOME" in os.environ:
        ec2.AWS_HOME = os.environ["AWS_HOME"]
    if "USER" in os.environ:
        ec2.USER = os.environ["USER"]
    if "AWS_KEYPAIR" in os.environ:
        ec2.AWS_KEYPAIR = os.environ["AWS_KEYPAIR"]
    if cmd=="create" and l==4:
        ec2.create(args[1], int(args[2]), args[3])
    elif cmd=="show" and l==2:
        ec2.get_cluster(args[1]).show()
    elif cmd=="show_all" and l==1:
        ec2.show()
    elif cmd=="shutdown" and l==2:
        ec2.shutdown(args[1])
    elif cmd=="shutdown_all" and l==1:
        ec2.shutdown_all()
    # elif cmd=="login" and l==2:
    #     login(args[1], 0)
    # elif cmd=="login" and l==3:
    #     login(args[1], int(args[2]))
    elif cmd=="kill" and l==3:
        ec2.kill(args[1], int(args[2]))
    elif cmd=="add" and l==3:
        ec2.add(args[1], int(args[2]))
    # elif cmd=="ssh" and l==4:
    #     ssh(args[1], int(args[2]), args[3])
    elif cmd=="ssh_all" and l==3:
        ec2.get_cluster(args[1]).ssh(args[2])
    # elif cmd=="scp" and l==4:
    #     scp(args[1], int(args[2]), args[3])
    # elif cmd=="scp" and l==5:
    #     scp(args[1], int(args[2]), args[3], args[4])
    elif cmd=="scp_all" and l==3:
        ec2.get_cluster(args[1]).scp_put(args[2])
    elif cmd=="scp_all" and l==4:
        ec2.get_cluster(args[1]).scp_put(args[2], args[3])
    else:
        print ("Command not recognized. "
               "For usage information, see README.md.")
