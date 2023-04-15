from flask import Flask, Response, request, url_for, render_template
from datetime import datetime, timedelta
from email_sender import send_email_api
from students_resource import StudentsResource
import json
from flask_cors import CORS
import jwt
import os
from werkzeug.security import generate_password_hash, check_password_hash
from util_token import generate_confirmation_token, confirm_token
from google.oauth2 import id_token
from pip._vendor import cachecontrol
import google.auth.transport.requests
import requests

secrets_file = "google_client_secret.json"
with open(secrets_file, "r") as file:
    secrets = json.load(file)

    GOOGLE_CLIENT_ID = secrets['web']['client_id']
    GOOGLE_CLIENT_SECRET = secrets['web']['client_secret']
    GOOGLE_DISCOVERY_URL = (
        "https://accounts.google.com/.well-known/openid-configuration"
    )

# Create the Flask application object.
application = Flask(__name__, template_folder="templates")

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# NEVER HARDCODE YOUR CONFIGURATION IN YOUR CODE
# TODO: INSTEAD CREATE A .env FILE AND STORE IN IT
application.config['SECRET_KEY'] = 'longer-secret-is-better'
CORS(application)


@application.route("/", methods = ['GET'])
def init():
    return "hello world"

@application.get("/api/health")
def get_health():
    t = str(datetime.now())
    msg = {
        "name": "Students-login-Backend",
        "health": "Good",
        "at time": t
    }
    result = Response(json.dumps(msg), status=200, content_type="application/json")
    return result


@application.route("/students/signup", methods=['POST'])
def signup():
    if request.is_json:
        try:
            request_data = request.get_json()
        except ValueError:
            return Response("[SIGNUP] UNABLE TO RETRIEVE REQUEST", status=400, content_type="text/plain")
    else:
        return Response("[SIGNUP] INVALID POST FORMAT: SHOULD BE JSON", status=400, content_type="text/plain")

    if not request_data:
        rsp = Response("[SIGNUP] INVALID INPUT FOR SIGNUP SHEET", status=404, content_type="text/plain")
        return rsp
    inputs = ['uni', 'email', 'password', 'last_name', 'first_name']
    for element in inputs:
        if element not in request_data:
            rsp = Response(f"[SIGNUP] MISSING INPUT {element.upper()}", status=404, content_type="text/plain")
            return rsp

    uni = request_data['uni']
    email = request_data['email']
    password = request_data['password']
    last_name = request_data['last_name']
    first_name = request_data['first_name']
    middle_name = None
    if 'middle_name' in request_data:
        middle_name = request_data['middle_name']

    user = StudentsResource.get_by_uni_email(uni, email)
    if user:
        rsp = Response("[SIGNUP] USER ALREADY EXISTS, PLEASE LOG IN", status=404, content_type="text/plain")
    else:
        password = generate_password_hash(password)
        result = StudentsResource.insert_student(uni, email, password, last_name, first_name, middle_name)
        if result:
            rsp = Response("[SIGNUP] STUDENT CREATED", status=200, content_type="text/plain")
            send_confirm_email(uni, email, "activate.html")
            print("Email Sent")
        else:
            rsp = Response("[SIGNUP] SIGNUP FAILED", status=404, content_type="text/plain")
    return rsp


@application.route("/students/resend", methods=["POST"])
def resend_confirmation():
    if request.is_json:
        try:
            request_data = request.get_json()
        except ValueError:
            return Response("[RESEND CONFIRMATION] UNABLE TO RETRIEVE REQUEST", status=400, content_type="text/plain")
    else:
        return Response("[RESEND CONFIRMATION] INVALID POST FORMAT: SHOULD BE JSON", status=400,
                        content_type="text/plain")

    if not request_data:
        rsp = Response("[RESEND CONFIRMATION] INVALID INPUT FOR SIGNUP SHEET", status=404, content_type="text/plain")
        return rsp

    inputs = ['uni', 'password']
    for element in inputs:
        if element not in request_data:
            rsp = Response(f"[RESEND CONFIRMATION] MISSING INPUT {element.upper()}", status=404,
                           content_type="text/plain")
            return rsp

    uni = request_data['uni']
    password = request_data['password']
    user = StudentsResource.get_by_uni_email(uni=uni)
    if not user:
        return Response(f"[RESEND CONFIRMATION] THIS UNI DOES NOT EXIST!", status=404, content_type="text/plain")
    elif not check_password_hash(user.get('password'), password):
        return Response(f"[RESEND CONFIRMATION] WRONG PASSWORD!", status=404, content_type="text/plain")
    elif user.get('status') == 'Verified':
        return Response(f"[RESEND CONFIRMATION] EMAIL HAS BEEN VERIFIED!", status=404, content_type="text/plain")
    email = user.get('email')
    send_confirm_email(uni, email, "activate.html")
    return Response(f"[RESEND CONFIRMATION] EMAIL HAS BEEN RE-SENT!", status=200, content_type="text/plain")


def send_confirm_email(uni, email, template_path, first_name=""):
    token = generate_confirmation_token(email)
    confirm_url = url_for('confirm_email', token=token, uni=uni, email=email, _external=True)
    html = render_template(template_path, confirm_url=confirm_url)
    subject = "Welcome To Team-matcher!"
    # send_mail(email, subject, html)
    send_email_api(email, first_name, subject, html)


@application.route("/students/loginwithgoogle", methods=['GET', 'POST'])
def login_with_google():
    credentials = json.loads(request.data)["credentials"]
    print("credential is " + credentials)

    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )
    print(id_info)
    if id_info.get("email_verified"):
        last_name = id_info["family_name"]
        first_name = id_info["given_name"]
        email = id_info["email"]
        picture = id_info["picture"]
        # uni = email.split("@")[0]
        uni = "N/A"
    else:
        return Response("[GOOGLE LOGIN] User email not available or not verified by Google",
                        status=400, content_type="text/plain")

    user = StudentsResource.get_by_uni_email(email=email)
    if not user:
        result = StudentsResource.insert_student(uni, email, "", last_name, first_name, None)
        if not result:
            return Response("[GOOGLE LOGIN] USER SIGNUP FAILED", status=404, content_type="text/plain")
        verified = StudentsResource.update_student_status(uni, email)
        if not verified:
            return Response("[GOOGLE LOGIN] EMAIL VERIFICATION FAILED", status=404, content_type="text/plain")
    else:
        uni = user['uni']
        if user['status'] == 'Pending':
            # update student_status if they exist but not verified
            StudentsResource.update_student_status(uni, email)

    exp = datetime.utcnow() + timedelta(minutes=30)
    token = jwt.encode({
        'uni': uni,
        'email': email,
        'exp': exp
    }, application.config['SECRET_KEY'],
        algorithm="HS256")
    return Response(json.dumps({'token': token, 'uni': uni, 'email': email, 'picture': picture}),
                    status=200, content_type="application.json")


@application.route("/students/login", methods=['POST'])
def login():
    request_data = request.get_json()
    if 'uni' not in request_data or 'password' not in request_data:
        return Response("[LOGIN] LOGIN FAILED: MISSING UNI OR PASSWORD", status=400, content_type="text/plain")
    uni = request_data['uni']
    password = request_data['password']

    user = StudentsResource.get_by_uni_email(uni)
    if not user:
        return Response("[LOGIN] LOGIN FAILED: USER DOES NOT EXIST", status=404, content_type="text/plain")

    if not check_password_hash(user.get('password'), password):
        return Response("[LOGIN] LOGIN FAILED: WRONG PASSWORD", status=401, content_type="text/plain")

    is_pending = StudentsResource.student_is_pending(uni)
    if is_pending:
        return Response("[LOGIN] USER ACCOUNT NOT VERIFIED", status=400, content_type="text/plain")

    # For this step, verify uni and pwd successfully and not pending, generate jwt token
    exp = datetime.utcnow() + timedelta(minutes=30)
    token = jwt.encode({
        'uni': user.get('uni'),
        'email': user.get('email'),
        'exp': exp
    }, application.config['SECRET_KEY'],
        algorithm="HS256")
    return Response(json.dumps({'token': token, 'uni': uni}), status=200, content_type="application.json")


@application.route("/students/account", methods=["POST"])
def update_account_info(email):
    if request.is_json:
        try:
            request_data = request.get_json()
        except ValueError:
            return Response("[UPDATE ACCOUNT] UNABLE TO RETRIEVE REQUEST", status=400, content_type="text/plain")
    else:
        return Response("[UPDATE ACCOUNT] INVALID POST FORMAT: SHOULD BE JSON", status=400, content_type="text/plain")

    if not request_data:
        rsp = Response("[UPDATE ACCOUNT] INVALID INPUT", status=404, content_type="text/plain")
        return rsp
    inputs = ['uni', 'password']
    for element in inputs:
        if element not in request_data:
            return Response(f"[UPDATE ACCOUNT] MISSING INPUT {element.upper()}", status=404, content_type="text/plain")

    #email = curr_user['email']
    uni = request_data['uni']
    user_with_uni = StudentsResource.get_by_uni_email(uni=uni, email="")
    if user_with_uni:
        # Detect user with same uni but different email address
        StudentsResource.delete_by_email(email)
        original_email = user_with_uni['email']
        return Response(f"[UPDATE ACCOUNT] USER UNI {uni} ALREADY EXISTS, PLEASE LOG IN with {original_email}",
                        status=404, content_type="text/plain")

    password = generate_password_hash(request_data['password'])
    result = StudentsResource.update_account(uni, email, password)
    send_confirm_email(uni, email, "welcome.html")
    if result:
        rsp = Response("[UPDATE ACCOUNT] STUDENT ACCOUNT UPDATED", status=200, content_type="text/plain")
    else:
        rsp = Response("[UPDATE ACCOUNT] ACCOUNT UPDATE FAILED", status=404, content_type="text/plain")
    return rsp


@application.route("/students/account", methods=["GET"])
def get_student_by_input(uni="", email=""):
    if "uni" in request.args:
        uni = request.args["uni"]
    if "email" in request.args:
        email = request.args["email"]
    result = StudentsResource.get_by_uni_email(uni, email)

    if result:
        rsp = Response(json.dumps(result), status=200, content_type="application.json")
    else:
        rsp = Response("NOT FOUND", status=401, content_type="text/plain")
    return rsp


@application.route("/students/confirm", methods=["GET"])
def confirm_email():
    if "email" not in request.args or "uni" not in request.args or "token" not in request.args:
        return Response("[ACCOUNT VERIFICATION] INVALID POST FORMAT: MISSING FIELD", status=400,
                        content_type="text/plain")

    usr_email = request.args['email']
    uni = request.args['uni']
    token = request.args['token']
    try:
        email = confirm_token(token)
    except:
        return Response('[EMAIL VERIFICATION] The confirmation link is invalid or has expired!',
                        status=404,
                        content_type="text/plain")
    if usr_email != email:
        return Response('[EMAIL VERIFICATION] The confirmation link is invalid: wrong email address!',
                        status=404,
                        content_type="text/plain")
    is_pending = StudentsResource.student_is_pending(uni)
    if not is_pending:
        return Response('[EMAIL VERIFICATION] Account has already been confirmed!',
                        status=404,
                        content_type="text/plain")
    verified = StudentsResource.update_student_status(uni, email)
    if verified:
        rsp = Response("[EMAIL VERIFICATION] STUDENT VERIFIED", status=200, content_type="text/plain")
    else:
        rsp = Response("[EMAIL VERIFICATION] VERIFICATION FAILED", status=404, content_type="text/plain")
    return rsp


@application.route("/students/profile", methods=["POST"])
def update_profile():
    if request.is_json:
        try:
            request_data = request.get_json()
        except ValueError:
            return Response("[UPDATE PROFILE] UNABLE TO RETRIEVE REQUEST", status=400, content_type="text/plain")
    else:
        return Response("[UPDATE PROFILE] INVALID POST FORMAT: SHOULD BE JSON", status=400, content_type="text/plain")

    if not request_data:
        return Response("[UPDATE PROFILE] INVALID INPUT", status=404, content_type="text/plain")
    inputs = ['timezone', 'major', 'gender', 'message']
    for element in inputs:
        if element not in request_data:
            return Response(f"[UPDATE PROFILE] MISSING INPUT {element.upper()}", status=400, content_type="text/plain")
    uni = request_data['uni']
    user = StudentsResource.get_by_uni_email(uni)
    if user:
        message = request_data['message'] if 'message' in request_data else ""
        result = StudentsResource.update_profile(uni, request_data['timezone'], request_data['major'],
                                                 request_data['gender'], message)
        if result:
            rsp = Response("[UPDATE PROFILE] PROFILE UPDATED", status=200, content_type="text/plain")
        else:
            rsp = Response("[UPDATE PROFILE] PROFILE UPDATE FAILED", status=404, content_type="text/plain")
    else:
        rsp = Response("[UPDATE PROFILE] USER DOES NOT EXISTS", status=404, content_type="text/plain")

    return rsp


@application.route("/students/profile", methods=["GET"])
def get_profile_by_uni():
    request_data = request.get_json()
    uni = request_data['uni']
    result = StudentsResource.get_profile(uni)
    if result:
        rsp = Response(json.dumps(result), status=200, content_type="application.json")
    else:
        rsp = Response("NOT FOUND", status=404, content_type="text/plain")
    return rsp



application.run(host="0.0.0.0", port=8000)
