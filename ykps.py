#!/usr/bin/env python3

# Although the above shebang line exists, you should probably run it in a
# production environment with something like gunicorn or uwsgi.
#
# SPDX-License-Identifier: AGPL-3.0-only
# https://git.runxiyu.org/ykps/current/ykps-wsgi.git
#


from flask import Flask, render_template, request, redirect, abort
from flask.wrappers import Response
import time, os, json

MAX_FILE_SIZE = 3000000  # only used in JS client-side validation
MAX_REQUEST_SIZE = 3145728  # only used in server-side validation
VERSION = """ykps-wsgi v0.1

License: GNU Affero General Public License v3.0 only
URLs: https://git.runxiyu.org/ykps/current/ykps-wsgi.git
      https://git.sr.ht/~runxiyu/ykps-wsgi.git"""

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_SIZE


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/version", methods=["GET"])
def version():
    return Response(VERSION, mimetype="text/plain")


@app.route("/sjdb/", methods=["GET"])
def sjdb_index():
    return render_template("sjdb-index.html")


@app.route("/sjdb/about", methods=["GET"])
def sjdb_about():
    return render_template("sjdb-about.html")


@app.route("/sjdb/acks", methods=["GET"])
def sjdb_ack():
    return render_template("sjdb-acks.html")


@app.route("/sjdb/submit", methods=["GET", "POST"])
def sjdb_submit():
    if request.method == "GET":
        return render_template(
            "sjdb-submit.html",
            max_request_size=MAX_REQUEST_SIZE,
            max_file_size=MAX_FILE_SIZE,
        )
    elif request.method == "POST":
        # NOTE: Do not place duplicate keys in the form! The conversion will only yield the first one.
        jd = json.dumps(request.form.to_dict())
        return Response(jd, mimetype="text/plain")
        # return render_template("sjdb-submit-post.html")
    else:
        return Response("Error 418: I'm a teapot", mimetype="text/plain", status=418)


if __name__ == "__main__":
    app.run(port=8080, debug=True)
