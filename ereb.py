from tornado.ioloop import IOLoop
import tornado.web
from lib.tasks_controller import TaskController
import time
import json
import logging

class TasksHandler(tornado.web.RequestHandler):
    def initialize(self, task_controller):
        self.task_controller = task_controller

    def get(self, task_id, action, task_run_id):
        result = '404'
        if task_id == '' and action == '':
            result = json.dumps(self.task_controller.get_task_list(with_history=True))
        elif task_id != '':
            task = self.task_controller.get_task_by_id(task_id)
            if not task:
                self.raise_404('task %s not found' % task_id)
            if action == '':
                result = json.dumps({
                    'config': task,
                    'runs': self.task_controller.get_task_runs_for_task_id(task_id)
                })
            elif action == 'run':
                self.task_controller.run_task_by_task_id(task_id)
                result = 'task_run'
            elif action == 'task_runs' and task_run_id != '':
                detailed_task_run = self.task_controller.get_detailed_task_run_info(task_id, task_run_id)
                if not detailed_task_run:
                    self.raise_404('Task run %s/%s not found' % (task_id, task_run_id))
                else:
                    result = json.dumps(detailed_task_run)

        self.set_header('Access-Control-Allow-Origin', '*')
        self.write(result)

    def post(self, task_id, action, task_run_id):
        result = '404'
        config = json.loads(self.request.body.decode())

        if task_id == '' and action == '':
            is_valid_config = self.task_controller.validate_config(config)
            if not is_valid_config:
                self.raise_500('Cannot update task with config: %s' % json.dumps(config))
            else:
                task = self.task_controller.set_task_by_id(config['task_id'], config)
                result = 'Success'
                self.set_header('Access-Control-Allow-Origin', '*')
                self.write(result)
        elif task_id != '':
            is_valid_config = self.task_controller.validate_config(config)

            if not is_valid_config:
                self.raise_500('Cannot update task with config: %s' % json.dumps(config))
            else:
                task = self.task_controller.set_task_by_id(task_id, config)
                result = 'Success'
                self.set_header('Access-Control-Allow-Origin', '*')
                self.write(result)

    def delete(self, task_id, action, task_run_id):
        result = '404'
        if task_id == '' and action == '':
            self.raise_404('Unknown route')
        elif task_id != '':
            task = self.task_controller.delete_task_by_id(task_id)
            if not task:
                self.raise_500('Cannot delete task with config: %s' % json.dumps(config))
            else:
                result = 'Success'
        self.set_header('Access-Control-Allow-Origin', '*')
        self.write(result)

    def options(self, task_id, action, task_run_id):
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, DELETE')

        self.write('')

    def raise_404(self, message):
        self.clear()
        self.set_status(404)
        self.set_header('Access-Control-Allow-Origin', '*')
        self.finish(message)

    def raise_500(self, message):
        self.clear()
        self.set_status(500)
        self.set_header('Access-Control-Allow-Origin', '*')
        self.finish(message)


class RunnerHandler(tornado.web.RequestHandler):
    def initialize(self, task_controller):
        self.task_controller = task_controller

    def get(self, cmd):
        if cmd == '':
            result = json.dumps(self.task_controller.get_status())
            self.set_header('Access-Control-Allow-Origin', '*')
            self.write(result)
        if cmd == 'recent_history':
            result = json.dumps(self.task_controller.get_recent_history(20))
            self.set_header('Access-Control-Allow-Origin', '*')
            self.write(result)
        elif cmd == 'start':
            self.task_controller.start_task_loop()
            self.set_header('Access-Control-Allow-Origin', '*')
            self.write('Success')
        elif cmd == 'stop':
            self.task_controller.stop_task_loop()
            self.set_header('Access-Control-Allow-Origin', '*')
            self.write('Success')

if __name__ == "__main__":
    from tornado.options import define, options
    define("port", default=8888, type=int, help="port to listen on")
    define("tasks_dir", default="./etc", type=str, help="directory with tasks config files")
    define("history_dir", default="./var", type=str, help="directory for history storage")
    tornado.options.parse_command_line()
    task_controller = TaskController(options.tasks_dir, options.history_dir)

    logging.info("Starting EREB on http://{}:{}".format('0.0.0.0', options.port))

    application = tornado.web.Application([
        (r"/tasks/?([^/]*)/?([^/]*)/?([^/]*)$", TasksHandler, dict(task_controller=task_controller)),
        (r"/status/?(.*)$", RunnerHandler, dict(task_controller=task_controller))
    ])

    task_controller.start()

    application.listen(options.port)
    IOLoop.instance().start()
