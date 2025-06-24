# this file imports custom routes into the experiment server
from __future__ import generator_stop

from functools import wraps
from json import dumps, loads

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    jsonify,
    render_template,
    request,
)
from jinja2 import TemplateNotFound

# # Database setup
from psiturk.db import db_session, init_db
from psiturk.experiment_errors import ExperimentError, InvalidUsageError
from psiturk.models import Participant
from psiturk.psiturk_config import PsiturkConfig
from psiturk.user_utils import PsiTurkAuthorization, nocache
from sqlalchemy import or_

# load the configuration options
config = PsiturkConfig()
config.load_config()
# if you want to add a password protect route, uncomment and use this
# myauth = PsiTurkAuthorization(config)

# explore the Blueprint
custom_code = Blueprint(
    "custom_code", __name__, template_folder="templates", static_folder="static"
)


###########################################################
#  serving warm, fresh, & sweet custom, user-provided routes
#  add them here
###########################################################

import os

try:
    exp_condition = os.environ["EXP_CONDITION"]
except KeyError:
    exp_condition = "suppress"


@custom_code.route("/get_exp_condition")
def get_exp_condition():
    current_app.logger.info("Accessing /get_exp_condition")
    return exp_condition


# ----------------------------------------------
# example custom route
# ----------------------------------------------
# @custom_code.route('/my_custom_view')
# def my_custom_view():
#     # Print message to server.log for debugging
#     current_app.logger.info("Reached /my_custom_view")
#     try:
#         return render_template('custom.html')
#     except TemplateNotFound:
#         abort(404)

# ----------------------------------------------
# example using HTTP authentication
# ----------------------------------------------
# @custom_code.route('/my_password_protected_route')
# @myauth.requires_auth
# def my_password_protected_route():
#    try:
#        return render_template('custom.html')
#    except TemplateNotFound:
#        abort(404)

# ----------------------------------------------
# example accessing data
# ----------------------------------------------
# @custom_code.route('/view_data')
# @myauth.requires_auth
# def list_my_data():
#    users = Participant.query.all()
#    try:
#        return render_template('list.html', participants=users)
#    except TemplateNotFound:
#        abort(404)

# ----------------------------------------------
# example computing bonus
# ----------------------------------------------


# @custom_code.route('/compute_bonus', methods=['GET'])
# def compute_bonus():
#     # check that user provided the correct keys
#     # errors will not be that gracefull here if being
#     # accessed by the Javascrip client
#     if not 'uniqueId' in request.args:
#         # i don't like returning HTML to JSON requests...  maybe should change this
#         raise ExperimentError('improper_inputs')
#     uniqueId = request.args['uniqueId']

#     try:
#         # lookup user in database
#         user = Participant.query.\
#             filter(Participant.uniqueid == uniqueId).\
#             one()
#         user_data = loads(user.datastring)  # load datastring from JSON
#         bonus = 0

#         for record in user_data['data']:  # for line in data file
#             trial = record['trialdata']
#             if trial['phase'] == 'TEST':
#                 if trial['hit'] == True:
#                     bonus += 0.02
#         user.bonus = bonus
#         db_session.add(user)
#         db_session.commit()
#         resp = {"bonusComputed": "success"}
#         return jsonify(**resp)
#     except:
#         abort(404)  # again, bad to display HTML, but...
