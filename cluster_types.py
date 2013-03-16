# -*- coding: utf-8 -*-
__author__ = 'Alexey'

import traceback
from time import sleep
import pymongo
import sys
from datetime import datetime
import getopt

class Task:
    STATUS_NEW = 'new'
    STATUS_ASSIGN = 'assign'
    STATUS_INPROGRESS = 'inprocess'
    STATUS_COMPLETED = 'completed'
    STATUS_ERROR = 'error'

class NodeBase:
    STATUS_INIT = 'init'
    STATUS_IDLE = 'idle'
    STATUS_ASSIGN = 'assign'
    STATUS_INPROGRESS = 'inprocess'
    STATUS_STOP = 'stop'
    STATUS_DEAD = 'dead'
    STATUS_API_LIMIT = 'api_limit'

    db_ip = 'localhost'
    db_name = 'cluster_test'
    db_tasks_collection = 'cluster_tasks'
    db_nodes_collection = 'cluster_nodes'

    db = None
    node_id = None
    nodes = None
    tasks = None

    def get_curr_node(self):
        curr_node = self.nodes.find_one({'_id': self.node_id})
        return curr_node

    def update_curr_node_status(self, status, message = None):
        curr_node = self.get_curr_node()
        if message != None:
            curr_node['logs'].append('%s:%s' % (datetime.now().strftime("%H:%M:%S"), message))
        curr_node['logs'].append('%s:%s->%s' % (datetime.now().strftime("%H:%M:%S"), curr_node['status'], status))
        curr_node['status'] = status
        self.nodes.save(curr_node)

    def work(self, params):
        pass

    def make_task(self, task):
        task_params = task['params']
        result = self.work(task_params)
        task['result'].append(result)
        task['status'] = Task.STATUS_COMPLETED
        self.tasks.save(task)
        return True

    def run_task(self, task_id):
        # update task (node_id, status -> inprocess)
        task = self.tasks.find_one({'_id': task_id})
        task['status'] = Task.STATUS_INPROGRESS
        task['node_id'] = self.node_id
        self.tasks.save(task)

        try:
            res =  self.make_task(task)
            task['status'] = Task.STATUS_COMPLETED
            self.tasks.save(task)
            return res
        except:
            # update task (status -> completed, results -> addresses)
            task['result'].append(traceback.format_exc())
            task['status'] = Task.STATUS_ERROR
            self.tasks.save(task)
            # update node (status -> idle, task_id -> None)
            self.update_curr_node_status(NodeBase.STATUS_API_LIMIT, traceback.format_exc())
            return False

    def usage(self):
        print "-i", "--dbIp", "mongoDB ip address"
        print "-d", "--dbName", "database name"
        print "-t", "--dbTasks", "collection name for tasks"
        print "-n", "--dbNodes", "collection name for nodes"

    def getopt(self, argv):
        try:
            opts, args = getopt.getopt(argv[1:], "hi:d:t:n:v", ["help", "dbIp=", 'dbName=', 'dbTasks=', 'dbNodes='])
        except getopt.GetoptError as err:
            # print help information and exit:
            print str(err) # will print something like "option -a not recognized"
            self.usage()
            sys.exit(2)
        verbose = False
        for o, a in opts:
            if o == "-v":
                verbose = True
            elif o in ("-h", "--help"):
                self.usage()
                sys.exit()
            elif o in ("-i", "--dbIp"):
                self.db_ip = a
            elif o in ("-d", "--dbName"):
                self.db_name = a
            elif o in ("-t", "--dbTasks"):
                self.db_tasks_collection = a
            elif o in ("-n", "--dbNodes"):
                self.db_nodes_collection = a
            else:
                print "unhandled option", o

        print self.db_ip, self.db_name, self.db_tasks_collection, self.db_nodes_collection

    def init(self):
        self.mongoConn = pymongo.MongoClient(self.db_ip, 27017)

        self.db = self.mongoConn[self.db_name]
        self.tasks = self.db[self.db_tasks_collection]
        self.nodes = self.db[self.db_nodes_collection]

        curr_node = {
            'task_ids': [],
            'status': NodeBase.STATUS_INIT,
            'logs': ['%s: create node' % str(datetime.now())]
        }
        self.node_id = self.nodes.insert(curr_node)

    def run(self):
        self.init()
        while True:
            curr_node = self.get_curr_node()
            status = curr_node['status']
            if status == NodeBase.STATUS_ASSIGN:
                self.update_curr_node_status(NodeBase.STATUS_INPROGRESS)
                for task_id in curr_node['task_ids']:
                    if not self.run_task(task_id):
                        return
                self.update_curr_node_status(NodeBase.STATUS_IDLE)
            elif status == NodeBase.STATUS_STOP:
                break
            elif status == NodeBase.STATUS_INIT:
                self.update_curr_node_status(NodeBase.STATUS_IDLE)
            sleep(0.1)

        self.update_curr_node_status(NodeBase.STATUS_DEAD)
        self.mongoConn.close()
