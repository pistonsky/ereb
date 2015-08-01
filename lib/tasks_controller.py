import os
import time
import datetime
import sys
import subprocess
import json
import glob
import re
import uuid
from crontab import CronTab
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado import gen
import logging


from lib.tasks_scheduler import TasksScheduler

class TaskController():
    def __init__(self, tasks_dir="etc"):
        self.tasks_dir = tasks_dir
        self.task_scheduler = TasksScheduler(tasks_dir)

    def update_config(self):
        return self.task_scheduler.update_config()

    def start(self):
        self.task_scheduler.start()

    def start_task_loop(self):
        self.task_scheduler.start_task_loop()

    def stop_task_loop(self):
        self.task_scheduler.stop_task_loop()

    def get_status(self):
        result = {}
        if self.task_scheduler.is_task_loop_running:
            result['state'] = 'running'
        else:
            result['state'] = 'stopped'

        result['next_run'], result['next_tasks'] = self.get_next_tasks()
        result['planned_task_run_uuids'] = self.task_scheduler.planned_task_run_uuids

        return result

    def get_next_tasks(self):
        return self.task_scheduler.get_next_tasks()

    def get_task_list(self):
        return self.task_scheduler.tasks_list

    def get_recent_history(self, limit):
        task_run_files = glob.glob('./var/*/*/state')
        result = []
        regexp = re.compile('./[^/]+/([^/]+)/([^/]+)/state', re.IGNORECASE)
        for f in task_run_files:
            matched = regexp.search(f)
            task_id, task_run_id = matched.group(1), matched.group(2)


            with open(f) as task_run_file:
                state = json.load(task_run_file)
            state['task_id'], state['task_run_id'] = task_id, task_run_id
            result.append(state)

        return sorted(result, key=lambda k: k['started_at'], reverse=True)[:limit]

    def get_task_by_id(self, task_id):
        result = None
        for task in self.task_scheduler.tasks_list:
            if task['name'] == task_id:
                return task
        return result

    def set_task_by_id(self, task_id, task_config):
        f = open(self.tasks_dir + '/%s.json' % task_id, 'w')
        f.write(json.dumps(task_config))
        f.close()
        self.task_scheduler.check_config()
        return True

    def delete_task_by_id(self, task_id):
        f = self.tasks_dir + '/%s.json' % task_id
        os.remove(f)
        self.task_scheduler.check_config()
        return True

    def get_task_runs_for_task_id(self, task_id, limit=20):
        task_run_files = glob.glob('./var/%s/*/state' % task_id)
        result = []
        regexp = re.compile('./[^/]+/[^/]+/([^/]+)/state', re.IGNORECASE)
        for f in task_run_files:
            task_run_id = regexp.search(f).group(1)
            with open(f) as task_run_file:
                task_run = json.load(task_run_file)
                task_run['id'] = task_run_id
                result.append(task_run)
        return sorted(result, key=lambda k: k['started_at'], reverse=True)[:limit]

    def get_detailed_history_for_task_id(self, task_id, limit=20):
        task_run_dirs = glob.glob('./var/%s/*' % task_id)
        result = []
        regexp = re.compile('./[^/]+/[^/]+/([^/]+)$', re.IGNORECASE)
        for f in task_run_dirs:
            task_run_id = regexp.search(f).group(1)
            task_run = {
                'id': task_run_id
            }

            with open(f + '/state') as file_content:
                task_run['state'] = json.load(file_content)
            for x in ['stdout', 'stderr', 'pid']:
                with open(f + '/' + x) as file_content:
                    task_run[x] = file_content.read()
            result.append(task_run)

        return sorted(result, key=lambda k: k['state']['started_at'], reverse=True)[:limit]

    def get_detailed_task_run_info(self, task_id, task_run_id):
        task_run_dirs = glob.glob('./var/%s/%s' % (task_id, task_run_id))

        if len(task_run_dirs) == 0:
            return None

        task_run_dir = task_run_dirs[0]
        task_run = {
            'id': task_run_id
        }

        with open(task_run_dir + '/state') as file_content:
            task_run['state'] = json.load(file_content)
        for x in ['stdout', 'stderr', 'pid']:
            with open(task_run_dir + '/' + x) as file_content:
                task_run[x] = file_content.read()

        return task_run

    def run_task_by_task_id(self, task_id):
        task = self.get_task_by_id(task_id)
        logging.info('MANUAL RUN | Running %s task' % task['name'])
        self.task_scheduler.run_task_by_name_and_cmd(task['name'], task['cmd'])

    def get_tasks_config(self):
        return self.task_scheduler.get_tasks_config()

    def validate_config(self, config):
        return self.task_scheduler.validate_config(config)
