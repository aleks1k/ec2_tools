# The most important data structure we use is a persistent shelf which
# is used to represent all the clusters.  The keys in this shelf are
# the `cluster_names`, and the values will be ec2_classes.Cluster
# objects, which represent named EC2 clusters.
#
# The shelf will be stored at "AWS_HOME/.ec2-shelf"
USER = "ubuntu"
import tempfile
import os
print tempfile.gettempdir() # prints the current temporary directory
AWS_HOME = os.path.join(tempfile.gettempdir(), 'ec2home')
AWS_KEYPAIR = "EC2_Cluster_Key_2"

# Form http://cloud-images.ubuntu.com/locator/ec2/
#
# ap-northeast-1	raring	13.04	amd64	ebs	20130423	ami-6b26ab6a	aki-44992845
# ap-southeast-1	raring	13.04	amd64	ebs	20130423	ami-2b511e79	aki-fe1354ac
# eu-west-1	raring	13.04	amd64	ebs	20130423	ami-3d160149	aki-71665e05
# sa-east-1	raring	13.04	amd64	ebs	20130423	ami-28e43e35	aki-c48f51d9
# us-east-1	raring	13.04	amd64	ebs	20130423	ami-c30360aa	aki-88aa75e1
# us-west-1	raring	13.04	amd64	ebs	20130423	ami-d383af96	aki-f77e26b2
# ap-southeast-2	raring	13.04	amd64	ebs	20130423	ami-84a333be	aki-31990e0b
# us-west-2	raring	13.04	amd64	ebs	20130423	ami-bf1d8a8f	aki-fc37bacc

regions = [
    {
        'name': 'eu-west-1',
        'amis': {'t1.micro': 'ami-3d160149'},
        # 'keypair': "cluster_key",
        'id': 7
    },
    {
        'name': 'us-east-1',
        'amis': {'t1.micro': 'ami-c30360aa'},
        # 'keypair': "ec2cluster",
        'id': 3
    },
    {
        'name': 'us-west-1',
        'amis': {'t1.micro': 'ami-d383af96'},
        # 'keypair': "westcluster",
        'id': 5
    },
    {
        'name': 'us-west-2',
        'amis': {'t1.micro': 'ami-bf1d8a8f'},
        # 'keypair': "cluster_key",
        'id': 2
    },
    ]
