from time import sleep

__author__ = 'Alexey'

import ec2

CLASTER_NAME = "alpha"
CLASTER_INS_COUNT = 2

# MAIN_SCRIPT = 'D:\Projects\OpenInclude\scrapers\stackoverflow\stackpylib.py'
MAIN_SCRIPT = 'D:/Projects/ec2_tools/test_python.py'
# ec2.create(CLASTER_NAME, CLASTER_INS_COUNT, 'm1.small')

cluster = None
while cluster == None:
    cluster = ec2.get_cluster(CLASTER_NAME)
    if cluster == None:
        print 'cluster is creating...'
        sleep(5)

ec2.scp_all(CLASTER_NAME, MAIN_SCRIPT)

ec2.ssh_all(CLASTER_NAME, 'python ./test_python.py')

ec2.shutdown(CLASTER_NAME)
