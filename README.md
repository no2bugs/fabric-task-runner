# Remote Task Runner

**This script runs a task on remote host/s using Python fabric synchroneously (prevents concurrency)**


#### Features:
* Reads all options from config file
* Runs a task on randomly assigned host from specified list
* Prevents task from running concurrently
* Notifies Slack and posts status to Datadog
* Sends task output to syslog on remote host



#### External module dependencies:
1. fabric
2. datadog

#### Getting Started:
1. `pip install fabric`  
2. `pip install datadog`
3. Set values in config.json

```
{
    "ssh_user":     "ec2-user",
    "task":         "job.sh",
    "auto_retry":   "False",
    "retry_sec":    "300",
    "slack":        "Enable",
    "slack_api":    "https://hooks.slack.com/services/a/b/token",
    "datadog":      "Enable",
    "dd_api_key":   "api_key",
    "dd_app_key":   "app_key",
    "hosts": [
                    "node1",
                    "node2",
                    "node3",
                    "node4",
                    "node5",
                    "node6",
                    "node7",
                    "node8",
                    "node9",
                    "node10"

    ]
} 
```

- **ssh_user**: *remote ssh user for running task*
- **task**: *Replace job.sh with the actual task script*
- **auto_retry**: *set to **True** to keep retrying task if concurrent run is detected*
- **retry_sec**: *seconds to wait before retry (only if **auto_retry** is set to **True**)*
- **slack**: *lets you **Enable** or **Disable** Slack notifications*
- **slack_api**: *Slack's webhook URL*
- **datadog**: *lets you **Enable** or **Disable** posts to Datadog*
- **dd_api_key**: *Datadog's API key*
- **dd_app_key**: *Datadog's APP key*
- **hosts**: *host/s for task to run on*

#### Running Task

- without local log file
```
shell#: fab run_task
```
- with local log file
```
shell#: fab run_task 2>&1 | tee -a log.txt
```
- redirect to syslog
```
shell#: fab run_task | logger -s -t task
```

#### Scheduling
*Add fab task to cron*

- with log file
```bash
# run job every hour
0 * * * * fab run_task 2>&1 | tee -a log.txt

```

- to syslog
```bash
# run job every hour
0 * * * * fab run_task | logger -s -t task

```