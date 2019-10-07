from flask import Blueprint, make_response, request
from flask import current_app as app
from flask_cors import CORS

import glob
import logging
import os
import codecs
import shutil

import tempfile

from . import tasks

widget_bp = Blueprint('widget_bp', __name__)
CORS(widget_bp)


def compose_response(obj, code):
    response = make_response(obj, code)
    return response


def get_example():
    """Return the default Inline code example directory path"""
    ex_dir = os.path.join(app.config['TEMPLATE_DIR'], "inline_code")
    logging.debug("Example directory is {}".format(ex_dir))
    return ex_dir


def prep_example_directory(example, request):
    """Prepare the directory in which the example can be run.
       Return a tuple with
          - the name of the directory created if it exists
          - the error message if not
    """
    # Create a temporary directory
    tempd = tempfile.mkdtemp()
    logging.debug("Creating tmp dir {}".format(tempd))

    # Copy the original resources in a sandbox directory
    for g in glob.glob(os.path.join(example, '*')):
        if not os.path.isdir(g):
            logging.debug("Copying {} to {}".format(g, tempd))
            shutil.copy(g, tempd)

    # Overwrite with the user-contributed files
    for file in request['files']:
        if len(file['contents']) > app.config['RECEIVED_FILE_CHAR_LIMIT']:
            logging.error("File {} exceeded char limit: size {}".format(file['basename'], len(file['contents'])))
            shutil.rmtree(tempd)
            return (None, "file contents exceeds size limits")
        logging.debug("Writing file {} to {}".format(file['basename'], tempd))
        with codecs.open(os.path.join(tempd, file['basename']),
                         'w', 'utf-8') as f:
            f.write(file['contents'])

    return (tempd, None)


@widget_bp.route('/run_program/', methods=['POST'])
def run_program():
    data = request.get_json()    
    e = get_example()
    if not e:
        return compose_response({'identifier': '', 'message': "example not found"}, 500)

    tempd, message = prep_example_directory(e, data)
    if message:
        return compose_response({'identifier': '', 'message': message}, 500)

    logging.debug(data)
    mode = data['mode']

    # Check whether we have too many processes running
    #if not resources_available():
    #    return make_response({'identifier': '', 'message': "the machine is busy processing too many requests"},
    #                         500,
    #                         headers=get_headers())

    # Run the command(s)
    run_cmd = "python /workspace/run.py /workspace/sessions/{} {}".format(
                os.path.basename(tempd), mode)

    if 'lab' in data:
        lab = data['lab']
        run_cmd += " {}".format(lab)


    # Push the code to the container in Celery task
    task = tasks.run_program.apply_async(kwargs={'tempd':tempd, 'run_cmd':run_cmd})
    logging.debug('Starting Celery task with id={}'.format(task.id))
    logging.debug('Running cmd in container: {}'.format(run_cmd))

    return compose_response({'identifier': task.id, 'message': "Running program"}, 200)


@widget_bp.route('/check_output/', methods=['POST'])
def check_output():
    data = request.get_json()
    logging.debug(data)  

    identifier = data['identifier']
    logging.debug('Checking Celery task with id={}'.format(identifier))
    task = tasks.run_program.AsyncResult(identifier)

    logging.debug("Task state is {}".format(task.state))

    if task.state == 'PENDING':
        # job has not started yet
        response = {'output': [],
                    'status': 0,
                    'completed': False,
                    'message': "Pending"} 
    elif task.state == 'FAILURE':
        logging.error('Task id={} failed. Response={}'.format(task.id, task.info))
        return compose_response(task.info, 500)
    elif task.state == 'SUCCESS':
        logging.debug("Task info {}".format(task.info))
        response = task.info
        

    logging.debug('Responding with response={}'.format(response))
    return compose_response(response, 200)
