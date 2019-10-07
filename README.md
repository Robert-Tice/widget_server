# widget_server

Server code for learn.adacore.com widgets

## Requirements

Vagrant, Virtual box

## Getting started

To setup run:
```
$ vagrant up
$ vagrant ssh

# From the vagrant VM run:

$ cd /vagrant
$ source venv/bin/activate

# The next 3 commands should be run simultaneously. I use three terminal windows for this:

$ ./run_redis.sh
$ flask run --host=0.0.0.0
$ celery worker -A celery_worker.celery -E --loglevel=DEBUG
```

