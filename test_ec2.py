from time import sleep

__author__ = 'Alexey'

import ec2
import os

CLASTER_NAME = "alpha"
CLASTER_INS_COUNT = 1

# MAIN_SCRIPT = 'D:\Projects\OpenInclude\scrapers\stackoverflow\stackpylib.py'
MAIN_SCRIPT = 'D:/Projects/ec2_tools/test_python.py'
# ec2.create(CLASTER_NAME, CLASTER_INS_COUNT, 't1.micro')

cluster = None
while cluster == None:
    cluster = ec2.get_cluster(CLASTER_NAME)
    if cluster == None:
        print 'cluster is creating...'
        sleep(5)

# ec2.scp_all(CLASTER_NAME, MAIN_SCRIPT)

# d = ec2.ssh_all(CLASTER_NAME, 'ls -la')
ec2.scp_all(CLASTER_NAME, MAIN_SCRIPT,)
d2 = ec2.ssh_all(CLASTER_NAME, 'python ./' + os.path.basename(MAIN_SCRIPT))
print str(d2)
ec2.shutdown(CLASTER_NAME)
