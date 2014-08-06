#!/usr/bin/env python

""" Does database storage for node.js server """

import argparse
import sys
import sqlite3
import time
import json
import datetime
import subprocess
from subprocess import Popen

conn = sqlite3.connect('dataset.db')
compile_path = '../../submodules/raco/c_test_environment/'
dataset_path = compile_path + 'datasets/'
scheme_path = compile_path + 'schema/'


def parse_options(args):
    parser = argparse.ArgumentParser()

    parser.add_argument('function', metavar='f', type=str,
                        help='function to call for db storing/retrieving')

    parser.add_argument('-p', nargs='+',
                        help='params for the function')

    ns = parser.parse_args(args)
    return ns


# params: filename url qid
def process_query(params):
    relkey = params[0].split(':')
    qid = params[2]
    c = conn.cursor()
    cur_time = time.time()
    query = 'INSERT INTO dataset VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    param_list = (relkey[0], relkey[1], relkey[2], qid, cur_time, params[1],
                  'ACCEPTED', cur_time, None, 0, 0, "")
    c.execute(query, param_list)
    conn.commit()
    conn.close()


# params: filename qid plan
def write_file(params):
    f = open(compile_path + params[0] + '.cpp', 'w')
    f.write(params[2])
    f.close()


# params: qid
def update_query_run(params):
    query = 'UPDATE dataset SET status = "RUNNING" WHERE queryId = ?'
    c = conn.cursor()
    c.execute(query, (params[0],))
    conn.commit()
    conn.close()


def run_query(params):
    backend = params[0]
    filename = params[1]
    cmd = 'python run_query.py ' + backend + ' '
    if backend == 'grappa':
        cmd += 'grappa_'
    cmd += filename
    try:
        p = subprocess.check_call(cmd, cwd=compile_path)
    except Exception as e:
        print e


# params: qid
def update_query_error(params):
    query = 'UPDATE dataset SET status = "ERROR" WHERE queryId = ?'
    c = conn.cursor()
    c.execute(query, (params[0],))
    conn.commit()
    conn.close()


# params: qid
def update_query_success(params):
    qid = params[0]
    stop = time.time()
    sel_query = 'SELECT startTime FROM dataset WHERE queryId = ?'
    upd_query = 'UPDATE dataset SET status = "SUCCESS", endTime = ?,' + \
                'elapsed = ? WHERE queryId = ?'
    c = conn.cursor()
    c.execute(sel_query, (qid,))
    start = c.fetchone()[0]
    elapsed = (stop - start) * 1000000000  # turn to nanoseconds
    params_list = (stop, elapsed, qid)
    c.execute(upd_query, params_list)
    conn.commit()
    conn.close()


# params: filename qid
def update_catalog(params):
    filename = dataset_path + params[0]
    p1 = Popen(['cat', filename], stdout=subprocess.PIPE)
    p2 = Popen(['wc', '-l'], stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
    output = p2.communicate()[0]
    c = conn.cursor()
    query = 'UPDATE dataset SET numTuples = ? WHERE queryId = ?'
    c.execute(query, (output, params[1]))
    conn.commit()
    conn.close()


# params: filename qid
def update_scheme(params):
    f = open(scheme_path + params[0], 'r')
    data = f.read().split('\n')
    schema = {'columnNames': data[0], 'columnTypes': data[1]}
    query = 'UPDATE dataset SET schema = ? WHERE queryId = ?'
    c = conn.cursor()
    c.execute(query, (json.dumps(schema), params[1]))
    conn.commit()
    conn.close()


# params: qid
def get_query_status(params):
    c = conn.cursor()
    query = 'SELECT * FROM dataset WHERE queryId= ?'
    c.execute(query, (params[0],))
    row = c.fetchone()
    if not row[8]:
        fin = 'None'
        elapsed = time.time()
    else:
        fin = datetime.datetime.fromtimestamp(row[8]).isoformat()
        elapsed = row[9]
    res = {"status": row[6], "queryId": row[3], "url": row[5],
           "startTime": datetime.datetime.fromtimestamp(row[7]).isoformat(),
           "finishTime": fin, "elapsedNanos": elapsed}
    conn.close()
    print json.dumps(res)


def main(args):
    opt = parse_options(args)
    func = opt.function
    params = opt.p
    if func == 'process_query':
        process_query(params)
    elif func == 'get_query_status':
        get_query_status(params)
    elif func == 'update_query_run':
        update_query_run(params)
    elif func == 'run_query':
        run_query(params)
    elif func == 'update_query_error':
        update_query_error(params)
    elif func == 'update_query_success':
        update_query_success(params)
    elif func == 'update_catalog':
        update_catalog(params)
    elif func == 'update_scheme':
        update_scheme(params)
    elif func == 'write_file':
        write_file(params)


if __name__ == "__main__":
    main(sys.argv[1:])
