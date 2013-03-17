# -*- coding: utf-8 -*-
from datetime import datetime
import os
from time import sleep
import sys

__author__ = 'Alexey'

import pymongo
from cluster_types import Task, NodeBase

from ec2_tools.ec2 import ClusterManager
from aws_settings.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

def we_are_frozen():
    # All of the modules are built-in to the interpreter, e.g., by py2exe
    return hasattr(sys, "frozen")

def module_path():
    encoding = sys.getfilesystemencoding()
    if we_are_frozen():
        return os.path.dirname(unicode(sys.executable, encoding))
    return os.path.dirname(unicode(__file__, encoding))

class MasterNodeBase():
    db_ip = 'localhost'
    db_name = 'cluster_test'
    db_tasks_collection = 'cluster_tasks'
    db_nodes_collection = 'cluster_nodes'

    my_path = module_path()

    node_script = my_path + '/cluster_types.py'

    NODE_SCRIPTS = [node_script]
    SSH_INIT_COMMAND = 'sudo aptitude -y install python-setuptools; sudo easy_install pymongo'

    CLUSTER_NAME = "alpha"
    cluster_manager = ClusterManager(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    cluster = None

    db = None
    nodes = None
    tasks = None

    def init(self):
        pass

    def __init__(self, db_ip, db_name, nodes_count):
        self.db_ip = db_ip
        self.db_name = db_name

        self.init()

        self.NODE_SCRIPT_PARAMS = '--dbIp=%s --dbName=%s --dbTasks=%s --dbNodes=%s' % \
                                  (self.db_ip, self.db_name, self.db_tasks_collection, self.db_nodes_collection)

        self.CLUSTER_NODES_COUNT = nodes_count

        self.mongoConn = pymongo.MongoClient(self.db_ip, 27017)
        self.db = self.mongoConn[self.db_name]
        self.tasks = self.db[self.db_tasks_collection]
        self.nodes = self.db[self.db_nodes_collection]

    def create_task(self, tasks_collection, task_params):
        task = {
            'params': task_params,
            'node_id': '',
            'status': Task.STATUS_NEW, # assign, inprocess, completed, error
            'result': []
        }
        tasks_collection.insert(task)

    def add_tasks(self, tasks_collection):
        pass

    def create_tasks(self):
        self.db.drop_collection(self.db_tasks_collection)
        self.tasks = self.db[self.db_tasks_collection]
        self.add_tasks(self.tasks)

    def run_cluster(self, create=True):
        self.cluster = self.cluster_manager.create(self.CLUSTER_NAME, self.CLUSTER_NODES_COUNT, 't1.micro')
        if create:
            inited = False
            while not inited:
                try:
                    self.cluster.ssh(self.SSH_INIT_COMMAND, background=False)
                    inited = True
                except socket.error as ex:
                    print 'Can\'t connect to node %s' % str(ex)
        for f in self.NODE_SCRIPTS:
            self.cluster.scp_put(f, './' + os.path.basename(f))

        self.db.drop_collection(self.db_nodes_collection)
        self.nodes = self.db[self.db_nodes_collection]

        self.cluster.ssh('python ./' + os.path.basename(self.NODE_SCRIPTS[0]) + ' ' + self.NODE_SCRIPT_PARAMS, background=True)
        print 'Ran cluster %s from %d nodes' % (self.CLUSTER_NAME, self.CLUSTER_NODES_COUNT)

    def stop_cluster(self):
        # if self.cluster == None:
        #     self.cluster = self.cluster_manager.get_cluster(self.CLUSTER_NAME)
        self.cluster_manager.shutdown(self.CLUSTER_NAME)

    def make_final_result(self):
        pass

    def get_nodes(self, statuses):
        return self.nodes.find({
            'status': {
                '$in': statuses
            }
        })

    def get_tasks(self, statuses, limit = None):
        if limit != None:
            return self.tasks.find({
                'status': {
                    '$in': statuses
                }
            }).limit(limit)
        else:
            return self.tasks.find({
                'status': {
                    '$in': statuses
                }
            })

    def assign_task(self, node, tasks):
        task_ids = []
        for task in tasks:
            task_ids.append(task['_id'])
            task['node_id']  = node['_id']
            task['status'] = Task.STATUS_ASSIGN
            self.tasks.save(task)
        node['task_ids'] = task_ids
        node['status'] = NodeBase.STATUS_ASSIGN
        self.nodes.save(node)
        print 'Assign tasks -> node %s' % node['_id'],
        return len(task_ids)

    def init_all_nodes(self):
        self.nodes.update({
                              'status': {
                                  '$in': [NodeBase.STATUS_IDLE, NodeBase.STATUS_ASSIGN,
                                          NodeBase.STATUS_INPROGRESS, NodeBase.STATUS_API_LIMIT]
                              }}, {
                              '$set': {
                                  'status': NodeBase.STATUS_INIT}})

    def run(self, tasks_for_node_count = 1):
        self.init_all_nodes()
        qus_count = self.get_tasks([Task.STATUS_COMPLETED]).count()
        while True:
            nodes_list = self.get_nodes([NodeBase.STATUS_IDLE])
            count = nodes_list.count()
            if count > 0:
                tasks_list = self.get_tasks([Task.STATUS_NEW], count)
                if tasks_list.count() > 0:
                    i=0
                    for node in nodes_list:
                        print '\n', qus_count,
                        tasks_for_node = []
                        for j in range(i, tasks_list.count()):
                            tasks_for_node.append(tasks_list[j])
                            if j > i + tasks_for_node_count:
                                break
                        ntask = self.assign_task(node, tasks_for_node)
                        qus_count += ntask
                        i += ntask
                        if i >= tasks_list.count():
                            break
                else:
                    tasks_list = self.get_tasks([Task.STATUS_NEW, Task.STATUS_ASSIGN, Task.STATUS_INPROGRESS], 1)
                    nodes_list = self.get_nodes([NodeBase.STATUS_ASSIGN, NodeBase.STATUS_INPROGRESS])
                    if tasks_list.count() == 0 and nodes_list.count() == 0:
                        print '\nall tasks completed'
                        break
            else:
                nodes_list = self.get_nodes([NodeBase.STATUS_IDLE,
                                             NodeBase.STATUS_ASSIGN, NodeBase.STATUS_INPROGRESS])
                if nodes_list.count() == 0:
                    print '----'
                    sleep(5)
                    nodes_list = self.get_nodes([NodeBase.STATUS_IDLE,
                                                 NodeBase.STATUS_ASSIGN, NodeBase.STATUS_INPROGRESS])
                    if nodes_list.count() == 0:
                        print '\nall nodes died'
                        break
                        # TODO kill nodes with status 'api_limit' and run new
            print '.',
            sleep(0.1)

        self.make_final_result()

        self.mongoConn.close()
