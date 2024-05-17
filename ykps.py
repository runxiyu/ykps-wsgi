#!/usr/bin/env python3

# Although the above shebang line exists, you should probably run it in a
# production environment with something like gunicorn or uwsgi.
#
# SPDX-License-Identifier: AGPL-3.0-only
# https://git.runxiyu.org/ykps/current/ykps-wsgi.git
#


from flask import Flask, render_template, request, redirect, abort
from flask.wrappers import Response
import time, os
app = Flask(__name__)

MAX_FILE_SIZE = 3000000  # only used in client-side validation
MAX_REQUEST_SIZE = 3145728  # only used in server-side validation
VERSION = """ykps-wsgi v0.1

License: GNU Affero General Public License v3.0 only
URL: https://git.runxiyu.org/ykps/current/ykps-wsgi.git"""

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")

@app.route('/version', methods=['GET'])
def version():
    return Response(__VERSION__, mimetype="text/plain")

@app.route('/sjdb/', methods=['GET'])
def sjdb_index():
    return render_template("sjdb-about.html")

@app.route('/sjdb/acks', methods=['GET'])
def sjdb_ack():
    return render_template("sjdb-acks.html")

@app.route('/sjdb/submit', methods=['GET'])
def sjdb_submit():
    return render_template("sjdb-submit.html", max_request_size = MAX_REQUEST_SIZE, max_file_size = MAX_FILE_SIZE)

if __name__ == "__main__":
    app.run(port=8080, debug=True)
