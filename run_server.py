#!/usr/bin/env python

import os
import json
import tinys3
from utils.io import load_json
from flask import Flask, render_template, request
from flask import flash, redirect, url_for
from werkzeug.utils import secure_filename

from utils.heatmap_utils import tcx_to_df

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'tcx'])

app = Flask(__name__)
app.secret_key = "super secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Todo: Improve buttons to regulate opacity and radius
# Todo: Store and retrieve file in S3 with nametxcfile_datetime format

# Google Map Api
config_google = load_json('config/config_google.json')
google_api_key = config_google['google_api_key']

# AWS S3
config_aws = load_json('config/config_aws.json')
AWS_ACCESS_KEY_ID = config_aws['access_key_id']
AWS_SECRET_ACCESS_KEY = config_aws['secret_access_key']
s3_conn = tinys3.Connection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def build_heatmap(coords, coords_center):
    center_map = {"lat": coords_center['latitude'], "lng": coords_center['longitude']}
    return render_template('heat_map_google.html', coords=json.dumps(coords), center_map=center_map,
                           api_key=google_api_key)


@app.route('/heatmap')
def uploaded_file():
    filename = request.args['filename']
    # Create heatmap
    tcx_file_path = os.path.join('uploads/', filename)
    df_coords = tcx_to_df(tcx_file_path)
    coords = df_coords[['latitude', 'longitude']].values.tolist()
    coords_median = df_coords.mean(axis=0)
    return build_heatmap(coords, coords_median)


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            s3_conn.upload(os.path.join('tcx_files/', filename), file, 'pedro62360')  # Upload file to S3
            return redirect(url_for('uploaded_file', filename=filename))
    return render_template('index.html')


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == "__main__":
    app.run(debug=True)