#!/usr/bin/env python3

# Although the above shebang line exists, you should probably run it in a
# production environment with something like gunicorn or uwsgi.
#
# SPDX-License-Identifier: AGPL-3.0-only
# https://git.runxiyu.org/ykps/current/ykps-wsgi.git
#

from __future__ import annotations
import typing
import time
import os
import json

import flask
import werkzeug
import msal  # type: ignore

response_t: typing.TypeAlias = typing.Union[werkzeug.Response, flask.Response, str]

MAX_FILE_SIZE = 3000000  # only used in JS client-side validation
MAX_REQUEST_SIZE = 3145728  # only used in server-side validation
VERSION = """ykps-wsgi v0.1

License: GNU Affero General Public License v3.0 only
URLs: https://git.runxiyu.org/ykps/current/ykps-wsgi.git
      https://git.sr.ht/~runxiyu/ykps-wsgi.git"""

app = flask.Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_SIZE


@app.route("/", methods=["GET"])
def index() -> response_t:
    return flask.render_template("index.html")


@app.route("/version", methods=["GET"])
def version() -> response_t:
    return flask.Response(VERSION, mimetype="text/plain")


@app.route("/sjdb/", methods=["GET"])
def sjdb_index() -> response_t:
    return flask.render_template("sjdb-index.html")


@app.route("/sjdb/about", methods=["GET"])
def sjdb_about() -> response_t:
    return flask.render_template("sjdb-about.html")


@app.route("/sjdb/acks", methods=["GET"])
def sjdb_ack() -> response_t:
    return flask.render_template("sjdb-acks.html")


@app.route("/sjdb/submit", methods=["GET", "POST"])
def sjdb_submit() -> response_t:
    if flask.request.method == "GET":
        return flask.render_template(
            "sjdb-submit.html",
            max_request_size=MAX_REQUEST_SIZE,
            max_file_size=MAX_FILE_SIZE,
        )
    elif flask.request.method == "POST":
        # NOTE: Do not place duplicate keys in the form! The conversion will only yield the first one.
        jd = json.dumps(flask.request.form.to_dict())
        return flask.Response(jd, mimetype="text/plain")
        # return flask.render_template("sjdb-submit-post.html")
    else:
        return flask.Response(
            "Error 418: I'm a teapot", mimetype="text/plain", status=418
        )


if __name__ == "__main__":
    app.run(port=8080, debug=True)
