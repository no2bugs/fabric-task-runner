from fabric.api import *
import random
import time
from datetime import timedelta
import sys
import json
import requests
from datadog import initialize, api


def config():
    try:
        with open('config.json', 'r') as fr:
            conf = json.loads(fr.read())
    except FileNotFoundError:
        print('Error: config.json file not found')
        sys.exit(1)

    return conf


def notify_slack(msg):
    if config()['slack'] == 'Enable':
        try:
            webhook_url = config()['slack_api']
            slack_data = {'text': msg}

            response = requests.post(
                webhook_url, data=json.dumps(slack_data),
                headers={'Content-Type': 'application/json'}
            )
            if response.status_code != 200:
                raise ValueError(response.status_code, response.text)
        except Exception as e:
            print('Error: Something went wrong when connecting to slack\n', e)
    else:
        pass


# status: -1 = failed, 0 = warning, 1 = success
def post_datadog(status):
    if config()['datadog'] == 'Enable':
        options = {
            'api_key': config()['dd_api_key'],
            'app_key': config()['dd_app_key']
        }

        try:
            initialize(**options)

            now = time.time()

            api.Metric.send(metric='task.status', tags=[config()['task']], points=(now, status))
        except Exception as e:
            print('Error: Unable to post status to Datadog\n', e)
    else:
        pass


# check if local fab job is already running
def check_local_fab():
    with settings(warn_only=True), hide('output', 'running'):
        local_fab_running = local("ps aux | grep \"fab run_task\" | grep -v grep | wc -l", capture=True)

        if int(local_fab_running) > 1:
            print('Local fabric job is already running\n', local("ps aux | grep \"fab run_task\" | grep -v grep | awk '{if(NR>1)print}'", capture=True))
            notify_slack('Local fabric job is already running')
            sys.exit(0)


# checks if task is already running on any remote host
# if backoff is set to True, it will auto-retry every 5 minutes
def check_remote_task(servers, backoff, job):
    try:
        for each in servers:
            with settings(host_string=each, warn_only=True), hide('output', 'running'):
                task_running = run('if ps aux | grep "' + job + '" | grep -v grep > /dev/null; then echo True; fi').stdout.strip()
                if task_running and backoff == 'True':
                    while task_running:
                        print(time.strftime("%m/%d/%Y %H:%M:%S"))
                        task = run('ps aux | grep "' + job + '" | grep -v grep').stdout.strip()
                        print('Found ' + job + ' running on:', each)
                        notify_slack('Found ' + job + ' running on: ' + each)
                        print('auto_retry:', 'True')
                        print(task)
                        print('Will retry in ' + config()['retry_sec'] + ' seconds...\n')
                        notify_slack('Will retry in ' + config()['retry_sec'] + ' seconds...')
                        post_datadog(0)
                        time.sleep(int(config()['retry_sec']))
                        task_running = run('if ps aux | grep "' + job + '" | grep -v grep > /dev/null; then echo True; fi').stdout.strip()
                        check_remote_task(servers=config()['hosts'],
                                          backoff=config()['auto_retry'],
                                          job=config()['task'])

                if task_running and backoff == 'False':
                    print(time.strftime("%m/%d/%Y %H:%M:%S"))
                    print('Found ' + job + ' running on:', each)
                    notify_slack('Found ' + job + ' running on: ' + each)
                    task = run('ps aux | grep "' + job + '" | grep -v grep').stdout.strip()
                    print('auto_retry:', 'False')
                    print(task)
                    print('Exiting...')
                    notify_slack('Exiting...')
                    post_datadog(0)
                    sys.exit(1)
    except Exception as e:
        print(time.strftime("%m/%d/%Y %H:%M:%S"))
        print('Error: Something went wrong on', each)
        notify_slack('Error: Something went wrong on ' + each)
        print(e)
        print('Exiting...')
        post_datadog(-1)
        sys.exit(1)


def execute(h_ls, job):
    rand_host = random.choice(h_ls) # randomize to prevent task from always running on the same host

    try:
        with settings(host_string=rand_host, warn_only=True), hide('output','running'):
            print('\nSTART:', time.strftime("%m/%d/%Y %H:%M:%S"))
            notify_slack('START:    ' + str(time.strftime("%m/%d/%Y %H:%M:%S")))
            notify_slack('Running ' + job + ' on: ' + rand_host)
            print('Running ' + job + ' on:', rand_host)
            put(job, '~/')
            run('chmod 750 ~/' + job)

            start_task = time.time()
            out = run('~/' + job + ' | logger -s -t \'' + job + '\'').stdout.strip() # logger will write output to syslog
            finish_task = time.time()
            t_diff = float(finish_task) - float(start_task)
            t_finish = timedelta(seconds=int(t_diff))

            print('OS:        ', out.split('\n')[1])
            print('Kernel:    ',out.split('\n')[2])
            print('Disk Util: ', out.split('\n')[3])
            print('FINISH:', time.strftime("%m/%d/%Y %H:%M:%S"))
            print('Duration:', t_finish)
            notify_slack('FINISH:    ' + str(time.strftime("%m/%d/%Y %H:%M:%S")))
            notify_slack('Duration:  ' + str(t_finish))
            post_datadog(1)
    except Exception as error:
        print('Error: Something went wrong on', rand_host, error)
        notify_slack('Error: Something went wrong on ' + rand_host + error)
        post_datadog(-1)


def run_task():
    try:
        env.user = config()['ssh_user']
        h_list = config()['hosts']
        job_name = config()['task']
        auto_retry = config()['auto_retry']
    except Exception as error:
        print('Error: Unable to load config\n', error)
        sys.exit(1)

    notify_slack('BEGIN TASK: ' + job_name)
    check_local_fab()
    check_remote_task(h_list, backoff=auto_retry, job=job_name)
    execute(h_list, job=job_name)
    notify_slack('END TASK: ' + job_name)
