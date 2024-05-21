#!/usr/bin/env python3
#
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
import pathlib
import tempfile
import shutil

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
if ENV.upper() == "DEVELOPMENT":
    REDIRECT_URL = "http://localhost:8080/auth"
    with open("secret.txt", "r") as fd:
        CLIENT_SECRET = fd.read().strip("\n")
    UPLOAD_PATH = "uploads"
    SUBMISSION_PATH = "submissions"
else:
    REDIRECT_URL = "https://ykps.runxiyu.org/auth"
    with open("/srv/ykps/secret.txt", "r") as fd:
        CLIENT_SECRET = fd.read().strip("\n")
    UPLOAD_PATH = "/srv/ykps/uploads"
    SUBMISSION_PATH = "/srv/ykps/submissions"


class Teapot(Exception):
    pass
class RunxiError(Exception):
    pass


app = flask.Flask(__name__)
app.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(  # type: ignore
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_SIZE
app.config["SESSION_TYPE"] = "filesystem"


@app.errorhandler(Exception)
def error(
    exc: BaseException,
) -> response_t:
    tb = "".join(traceback.format_exception(exc, chain=True))
    return flask.Response(
        flask.render_template(
            "oops.html",
            error=tb,
        ),
        status=500,
    )


@app.errorhandler(Teapot)
def teapot(
    exc: Teapot,
) -> response_t:
    tb = "".join(traceback.format_exception(exc, chain=True))
    return flask.Response(
        flask.render_template(
            "teapot.html",
            msg=exc.args[0],
            error=tb,
        ),
        status=418,
    )


@app.errorhandler(404)
def handle_404(exc: BaseException) -> response_t:
    msg = "".join(traceback.format_exception(exc, chain=True))
    return flask.Response(
        flask.render_template(
            "404.html",
            err=msg,
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
    return flask.Response(json.dumps(context, indent="\t"), mimetype="application/json")


# @app.route("/login", methods=["GET"])
# def login() -> response_t:
#     return flask.Response("", mimetype="text/plain")

# @app.route("/auth", methods=["GET", "POST"])
# def auth() -> response_t:
#     return flask.Response("", mimetype="text/plain")


@app.route("/error", methods=["GET"])
def error_test() -> response_t:
    raise Exception("THIS IS ONLY A TEST FOR THE EXCEPTION HANDLER. THIS IS NOT A BUG.")


@app.route("/teapot", methods=["GET"])
def teapot_test() -> response_t:
    raise Teapot("TEAPOTS!")


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
    display_name = context["user"]["name"]
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
        if anon not in ["yes", "no", "axolotl"]:
            raise Teapot(
                '"%s" is not an acceptable value for the "anon" field in the submit form. It should be "yes", "no", or "axolotl".'
                % anon
            )
        text = flask.request.form["text"]
        if "file" in flask.request.files and flask.request.files["file"].filename:
            if shutil.disk_usage(UPLOAD_PATH).free < 5 * (1024**3):
                raise RunxiError("Not enough disk space")
            file = flask.request.files["file"]
            if not file.filename:
                raise TypeError(
                    "I didn't think it's possible for the filename to suddenly become None again!!!"
                )
            fnr, fne = os.path.splitext(os.path.basename(file.filename))
            with tempfile.NamedTemporaryFile(
                mode="w+b",
                suffix=fne,
                prefix=fnr + ".",
                dir=UPLOAD_PATH,
                delete=False,
                delete_on_close=False,
            ) as fd:
                fn = fd.name
                file.save(fd)
        else:
            file = None
            fn = None
        jd = json.dumps(
            {"type": type_, "origin": origin, "anon": anon, "text": text, "file": fn},
            indent="\t",
        )
        return flask.Response(jd, mimetype="application/json", status=NOT_IMPLEMENTED)
        # return flask.render_template("sjdb-submit-post.html")


if __name__ == "__main__":
    app.run(port=8080, debug=True)
