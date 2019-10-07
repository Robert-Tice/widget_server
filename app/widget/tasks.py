from celery import Celery, states
from celery.exceptions import Ignore

import json
import logging
import os
import pylxd
import traceback


celery = Celery(__name__, autofinalize=False)
logger = logging.getLogger()

def recursive_put(container, src, dst):
    norm_src = os.path.normpath(src)
    if not os.path.isdir(norm_src):
        raise NotADirectoryError(
            "'src' parameter must be a directory "
        )

    idx = len(norm_src)

    for path, dirname, files in os.walk(norm_src):
        dst_path = os.path.normpath(
            os.path.join(dst, path[idx:].lstrip(os.path.sep)))
        container.execute(["mkdir", dst_path])

        # copy files
        for f in files:
            filepath = os.path.join(dst_path, f)

            src_file = os.path.join(path, f)
            with open(src_file, 'r') as fp:
                data = fp.read()

            logger.debug("Copying {} to {}".format(src_file, filepath))
            container.files.put(filepath, data)


@celery.task(bind=True)
def run_program(self, tempd, run_cmd):
    try:
        client = pylxd.Client()
        container = client.containers.get("safecontainer")
        logger.debug("Celery worker attached to lxd safecontainer")

        tmp_name = os.path.basename(os.path.normpath(tempd))

        # This is not supported yet, but is in the latest docs
        # container.files.recursive_put(tempd, os.path.join("safecontainer", "workspace", "sessions", tmp_name))

        # Temp workaround until recursive_put is released
        recursive_put(container, tempd, os.path.join(os.path.sep, "workspace", "sessions", tmp_name))
        logger.debug("Celery worker transferred files to safecontainer")

        container.execute(["chown", "-R", "runner", os.path.join(os.path.sep, "workspace", "sessions", os.path.basename(tempd))])
        container.execute(["chmod", "-R", "a+rx", os.path.join(os.path.sep, "workspace", "sessions", os.path.basename(tempd))])

    except Exception as e:
        logger.error("Celery worker failed to transfer program to safecontainer: {}: {}".format(e, traceback.print_exc()))
        self.update_state(state=states.FAILURE,
                          meta="Error transferring the program to container")
        raise Ignore()

    logger.debug("Celery worker running {} in safecontainer".format(run_cmd))
    code, stdout, stderr = container.execute(["su", "runner", "-c", run_cmd])
    logger.debug("Celery worker completed with code {}. stdout={} stderr={}".format(code, stdout, stderr))

    return {'output': [json.loads(s) for s in stdout.splitlines()],
            'status': code,
            'completed': True,
            'message': 'completed'}
