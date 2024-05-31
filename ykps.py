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
import datetime
import zoneinfo

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
    with open("tokens.txt", "r") as fd:
        MY_TOKENS = [l.strip("\n") for l in fd if l]
else:
    # REDIRECT_URL = "https://ykps.runxiyu.org/auth"
    REDIRECT_URL = "https://sj.ykps.net/auth"
    with open("/srv/ykps/secret.txt", "r") as fd:
        CLIENT_SECRET = fd.read().strip("\n")
    UPLOAD_PATH = "/srv/ykps/uploads"
    SUBMISSION_PATH = "/srv/ykps/submissions"
    with open("/srv/ykps/tokens.txt", "r") as fd:
        MY_TOKENS = [l.strip("\n") for l in fd if l]


class nope(Exception):
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


@app.errorhandler(nope)
def handle_nope(
    exc: nope,
) -> response_t:
    tb = "".join(traceback.format_exception(exc, chain=True))
    return flask.Response(
        flask.render_template(
            "nope.html",
            msg=exc.args[1],
            error=tb,
        ),
        status=exc.args[0],
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


@app.errorhandler(413)
def handle_413(exc: BaseException) -> response_t:
    tb = "".join(traceback.format_exception(exc, chain=True))
    return flask.Response(
        flask.render_template(
            "nope.html",
            msg="The request is too large! I can only handle up to %d bytes."
            % MAX_REQUEST_SIZE,
            error=tb,
        ),
        status=413,
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
    return flask.Response(flask.render_template("index.html"), status=200)


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


@app.route("/nope", methods=["GET"])
def nope_test() -> response_t:
    raise nope(418, "Just ignore this error and get off this URL.")


@app.route("/sjdb/", methods=["GET"])
def sjdb_index() -> response_t:
    return flask.Response(flask.render_template("sjdb-index.html"), status=200)


@app.route("/sjdb/about", methods=["GET"])
def sjdb_about() -> response_t:
    return flask.Response(flask.render_template("sjdb-about.html"), status=200)


@app.route("/sjdb/acks", methods=["GET"])
def sjdb_ack() -> response_t:
    return flask.Response(flask.render_template("sjdb-acks.html"), status=200)


@app.route("/sjdb/rf/<fn>", methods=["GET"])
def sjdb_rf(fn: str) -> response_t:
    try:
        auth = flask.request.headers["Authorization"]
        assert (
            auth and auth.startswith("Bearer ") and auth[len("Bearer ") :] in MY_TOKENS
        )
    except (KeyError, AssertionError):
        raise nope(
            401,
            "You can't read uploaded files without proper authentication for security reasons",
        )
    return flask.send_from_directory(UPLOAD_PATH, fn, as_attachment=True)


@app.route("/sjdb/rs/<fn>", methods=["GET"])
def sjdb_rs_file(fn: str) -> response_t:
    try:
        auth = flask.request.headers["Authorization"]
        assert (
            auth and auth.startswith("Bearer ") and auth[len("Bearer ") :] in MY_TOKENS
        )
    except (KeyError, AssertionError):
        raise nope(
            401,
            "You can't read submissions without proper authentication for security reasons",
        )
    return flask.send_from_directory(SUBMISSION_PATH, fn)


@app.route("/sjdb/rs", methods=["GET"])
def sjdb_rs_dir() -> response_t:
    try:
        auth = flask.request.headers["Authorization"]
        assert (
            auth and auth.startswith("Bearer ") and auth[len("Bearer ") :] in MY_TOKENS
        )
    except (KeyError, AssertionError):
        raise nope(
            401,
            "You can't list submissions without proper authentication for security reasons",
        )
    return flask.Response(
        json.dumps(os.listdir(SUBMISSION_PATH), indent="\t"),
        mimetype="application/json",
    )


@app.route("/sjdb/submit", methods=["GET", "POST"])
@auth.login_required  # type: ignore
def sjdb_submit(context) -> response_t:
    display_name = context["user"]["name"]
    if flask.request.method == "GET":
        return flask.Response(
            flask.render_template(
                "sjdb-submit.html",
                max_request_size=MAX_REQUEST_SIZE,
                max_file_size=MAX_FILE_SIZE,
                display_name=display_name,
            ),
            status=200,
        )
    elif flask.request.method == "POST":
        # NOTE: Do not place duplicate keys in the form! The conversion will only yield the first one.
        try:
            type_ = flask.request.form["type"]
            origin = flask.request.form["origin"]
            anon = flask.request.form["anon"]
            text = flask.request.form["text"]
        except KeyError as e:
            raise nope(
                400, 'Your request does not contain the required field "%s"' % e.args[0]
            )
        if anon == "yes":
            uname = display_name
        elif anon == "no":
            uname = None
        elif anon == "axolotl":
            uname = "an axolotl"
        else:
            raise nope(
                400,
                '"%s" is not an acceptable value for the "anon" field in the submit form. It should be "yes", "no", or "axolotl".'
                % anon,
            )
        if "file" in flask.request.files and flask.request.files["file"].filename:
            if shutil.disk_usage(UPLOAD_PATH).free < 5 * (1024**3):
                raise nope(
                    507,
                    "Unfortunately, I don't have enough disk space to fulfill this request. There is something funny going on with the server; please notify the administrator!",
                )
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
            ) as fdf:
                fn = fdf.name
                file.save(fdf)
        else:
            file = None
            fn = None
        if not (text.strip() or fn):
            raise nope(400, "Your submission request is basically empty.")
        ts = datetime.datetime.now(tz=zoneinfo.ZoneInfo("UTC")).strftime("%s")
        with tempfile.NamedTemporaryFile(
            mode="w+",
            suffix=".json",
            prefix=ts,
            dir=SUBMISSION_PATH,
            delete=False,
            encoding="utf-8",
        ) as fdj:
            fdjn = fdj.name
            data = {
                "type": type_,
                "origin": origin,
                "uname": uname,
                "ts": ts,
                "text": text,
                "file": os.path.basename(fn) if fn else None,
                "sub": os.path.basename(fdjn),
            }
            json.dump(
                data,
                fdj,
                indent="\t",
            )
        return flask.Response(
            json.dumps(data, indent="\t"),
            mimetype="application/json",
            status=201,
        )


@app.route("/sjdb/unsub", methods=["GET"])
def unsub() -> response_t:
    raise nope(501, "Unsubscribing is not implemented yet. Email sjdb@runxiyu.org")


if __name__ == "__main__":
    app.run(port=8080, debug=True)
