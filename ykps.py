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

VERSION = """ykps-wsgi v0.1

License: GNU Affero General Public License v3.0 only
URL: https://git.runxiyu.org/ykps/current/ykps-wsgi.git"""

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")

@app.route('/sjdb/', methods=['GET'])
def sjdb_index():
    return render_template("sjdb-about.html")

@app.route('/sjdb/ack', methods=['GET'])
def sjdb_ack():
    return render_template("sjdb-ack.html")

if __name__ == "__main__":
    app.run(port=8080)
