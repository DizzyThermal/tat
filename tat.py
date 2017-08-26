#!/usr/bin/env python2

import logging
import logging.handlers
import os
import subprocess
import sys

from third_party.py import gflags

FLAGS = gflags.FLAGS

gflags.DEFINE_boolean('debug', False,
                      'Turn on debugging')
gflags.DEFINE_string('log_file', os.path.expanduser('~/.tat/log'),
                     'Path to the log file')
gflags.DEFINE_integer('log_max_size', 5,
                      'Max log file size in MB')
gflags.DEFINE_string('tmux_bin', '/usr/bin/tmux',
                     'Path to the tmux binary to use')


def touch_file(file_path):
    file_handler = open(file_path, 'a')
    try:
        os.utime(file_path, None)
    finally:
        file_handler.close()


def _init_arguments(argv=None):
    try:
        argv = FLAGS(argv)
    except gflags.FlagsError as ex:
        print '\n'.join([
            ex,
            'Usage: {} ARGS'.format(sys.argv[0]),
            FLAGS])
        logging.exception(ex)
        sys.exit(1)

    return argv


def _init_logging():
    root_logger = logging.getLogger()

    if FLAGS.debug:
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.WARNING)

    logFormat = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - '
                                  '%(message)s')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logFormat)

    log_dir, _ = os.path.split(FLAGS.log_file)

    # Check if log file exists, create if it does not.
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    if not os.path.isfile(FLAGS.log_file):
        touch_file(FLAGS.log_file)

    file_handler = logging.handlers.RotatingFileHandler(
        FLAGS.log_file,
        maxBytes=(1048576*FLAGS.log_max_size),
        backupCount=7)
    file_handler.setFormatter(logFormat)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def _list_sessions():
    console_pipe = subprocess.Popen([FLAGS.tmux_bin, 'list-sessions'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
    output, error = console_pipe.communicate()
    error_code = console_pipe.returncode

    # If error contains an error message, the output is blank, or the return
    # code is not 0, there was an problem calling tmux.
    if error_code:
        logging.error('\n'.join(['Unable to list tmux sessions.', '%s']), error)
        sys.exit(1)

    if output:
        sessions = output.strip().splitlines()
        return sessions

    return None


def _print_active_sessions(sessions):
    print 'Active tmux sessions:'
    for i in range(len(sessions)):
        session_name = sessions[i].split(':')[0]
        print '  [{}]: {}'.format((i+1), session_name)

    print ''


def _get_user_selection():
    selection = raw_input('Which tmux session would you like to resume?: ')
    try:
        selection_number = int(selection)
    except ValueError as ex:
        logging.exception(ex)
        sys.exit(1)

    return selection_number


def main(argv):
    argv = _init_arguments(argv)
    _init_logging()

    sessions = _list_sessions()
    if sessions:
        _print_active_sessions(sessions)
        selection = _get_user_selection()

        if selection in list(range(1, len(sessions)+1)):
            session_name = sessions[selection-1].split(':')[0]
            logging.info('Attempting to resume tmux session: %s', session_name)
            subprocess.call([FLAGS.tmux_bin,
                             'attach-session',
                             '-t', sessions[selection-1].split(':')[0]])
        else:
            print 'Invalid session number, choose a valid session number.'
            sys.exit(1)


if __name__ == '__main__':
    main(sys.argv)
