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
import sys
import traceback

# import configparser

import flask
import werkzeug
import werkzeug.middleware.proxy_fix
import identity.flask  # type: ignore

response_t: typing.TypeAlias = typing.Union[werkzeug.Response, flask.Response, str]

NOT_IMPLEMENTED = 501

MAX_FILE_SIZE = 3000000  # only used in JS client-side validation
MAX_REQUEST_SIZE = 3145728  # only used in server-side validation
VERSION = """ykps-wsgi v0.1

License: GNU Affero General Public License v3.0 only
URLs: https://git.runxiyu.org/ykps/current/ykps-wsgi.git
      https://git.sr.ht/~runxiyu/ykps-wsgi.git"""
ENV = os.environ.get("ENV", "PRODUCTION")

AUTHORITY = "https://login.microsoftonline.com/ddd3d26c-b197-4d00-a32d-1ffd84c0c295"
CLIENT_ID = "651eef7e-8670-4b68-b7ed-d2d7885187e4"
SCOPE = ["https://graph.microsoft.com/.default"]
if ENV == "DEVELOPMENT":
    REDIRECT_URL = "http://localhost:8080/auth"
else:
    REDIRECT_URL = "https://ykps.runxiyu.org/auth"

for fn in ["/srv/ykps/secret.txt", "secret.txt"]:
    try:
        with open(fn, "r") as fd:
            CLIENT_SECRET = fd.read().strip("\n")
        break
    except FileNotFoundError:
        pass
else:
    raise FileNotFoundError("secret.txt")
# with open("thumb.txt", "r") as fd:
#     THUMBPRINT = fd.read().strip("\n")
# with open("server.pem", "r") as fd:
#     PRIVATE_KEY = fd.read()


app = flask.Flask(__name__)
app.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(  # type: ignore
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_SIZE
app.config["SESSION_TYPE"] = "filesystem"


@app.errorhandler(Exception)
def handle_global_error(exc):
    msg = "".join(traceback.format_exception(exc, chain=True))
    return flask.Response(
        flask.render_template(
            "oops.html",
            msg="This error is really unexpected in the sense that no specific error handlers were set up to display this:",
            error=msg,
        ),
        status=500,
    )


@app.errorhandler(404)
def handle_404(exc):
    msg = "".join(traceback.format_exception(exc, chain=True))
    return flask.Response(
        flask.render_template(
            "404.html",
            e=msg,
        ),
        status=404,
    )


auth = identity.flask.Auth(
    app,
    CLIENT_ID,
    client_credential=CLIENT_SECRET,
    redirect_uri=REDIRECT_URL,
    authority=AUTHORITY,
)


@app.route("/", methods=["GET"])
def index() -> response_t:
    return flask.render_template("index.html")


@app.route("/version", methods=["GET"])
def version() -> response_t:
    return flask.Response(VERSION, mimetype="text/plain")


@app.route("/uinfo", methods=["GET"])
@auth.login_required  # type: ignore
def uinfo(context) -> response_t:
    return flask.Response(json.dumps(context), mimetype="application/json")


# @app.route("/login", methods=["GET"])
# def login() -> response_t:
#     return flask.Response("", mimetype="text/plain")

# @app.route("/auth", methods=["GET", "POST"])
# def auth() -> response_t:
#     return flask.Response("", mimetype="text/plain")


@app.route("/error", methods=["GET"])
def error_test() -> response_t:
    raise Exception("THIS IS ONLY A TEST.")


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
@auth.login_required  # type: ignore
def sjdb_submit(context) -> response_t:
    try:
        display_name = context["user"]["name"]
    except KeyError:
        return flask.Response(
            flask.render_template(
                "oops.html",
                subproject="sjdb",
                msg="I cannot obtain your display name. There might be an issue while you were logging in.",
                error=traceback.format_exc(),
            ),
            status=500,
        )
    if flask.request.method == "GET":
        return flask.render_template(
            "sjdb-submit.html",
            max_request_size=MAX_REQUEST_SIZE,
            max_file_size=MAX_FILE_SIZE,
            display_name=display_name,
        )
    elif flask.request.method == "POST":
        # NOTE: Do not place duplicate keys in the form! The conversion will only yield the first one.
        type_ = flask.request.form["type"]
        origin = flask.request.form["origin"]
        anon = flask.request.form["anon"]
        text = flask.request.form["text"]
        if "file" in flask.request.files and flask.request.files["file"].filename:
            file = flask.request.files["file"]
        else:
            file = None
        jd = json.dumps(
            {"type": type_, "origin": origin, "anon": anon, "text": text, "file": file}
        )
        return flask.Response(jd, mimetype="text/plain", status=NOT_IMPLEMENTED)
        # return flask.render_template("sjdb-submit-post.html")
    else:
        return flask.Response(
            "HTCPCP/1.0 418 I'm a teapot\nSee IETF RFC 2324 for details.",
            mimetype="text/plain",
            status=418,
        )


if __name__ == "__main__":
    app.run(port=8080, debug=True)
