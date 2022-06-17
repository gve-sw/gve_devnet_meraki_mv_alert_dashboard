# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (c) 2022 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
               https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

__author__ = "Simon Fang <sifang@cisco.com>"
__copyright__ = "Copyright (c) 2022 Cisco and/or its affiliates."
__license__ = "Cisco Sample Code License, Version 1.1"

# Import Section
from flask import Flask, render_template, request, make_response
from flask_sqlalchemy import SQLAlchemy
import json
import requests
from config import SQL_DB_NAME

# Global variables
app = Flask(__name__)

# Database settings
app.config["SQLALCHEMY_DATABASE_URI"] = SQL_DB_NAME
db = SQLAlchemy(app)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.String, nullable=True)
    site_camera = db.Column(db.String, nullable=True)
    time = db.Column(db.String, nullable=True)
    recap_image = db.Column(db.String, nullable=True)
    video_url = db.Column(db.String, nullable=True)

db.create_all()
db.session.commit()

# Methods
def get_alerts_from_db():
    alerts_list = []
    alerts = Alert.query.all()
    for alert in alerts:
        alerts_dict = {}
        alerts_dict['id'] = alert.id
        alerts_dict['date'] = alert.date
        alerts_dict['site_camera'] = alert.site_camera
        alerts_dict['time'] = alert.time
        alerts_dict['recap_image'] = alert.recap_image
        alerts_dict['video_url'] = alert.video_url
        alerts_list.append(alerts_dict)
    return alerts_list

def add_alert_to_db(motion_alert):
    print("*** We are going to add an Alert to the database ***")
    try:
        date = motion_alert["occurredAt"][:10]
        site_camera = motion_alert["deviceName"]
        time = motion_alert["occurredAt"][11:]
        recap_image = f"{motion_alert['occurredAt']}_{motion_alert['deviceSerial']}.jpg"
        timestamp = motion_alert['alertData']['timestamp']
        timestamp_converted = str(1000*float(timestamp))
        video_url = f"{motion_alert['deviceUrl']}?timestamp={timestamp_converted}"
        db.session.add(Alert(date=date, site_camera=site_camera, time=time, recap_image=recap_image, video_url=video_url))
        db.session.commit()
        print("*** The alert has been added to the database ***")
    except Exception as e:
        print("An exception has occurred")
        print(e)

def download_image(motion_alert_response):
    print("*** We are going to download the image ***")
    session = requests.Session()
    image_name = f"{motion_alert_response['occurredAt']}_{motion_alert_response['deviceSerial']}"
    image_url = motion_alert_response["alertData"]["imageUrl"]
    attempts = 1
    while attempts <= 30:
        r = session.get(image_url, stream=True)
        if r.ok:
            print(f'Retried {attempts} times until successfully retrieved {image_url}')
            destination_image = f'{app.root_path}/static/images/recap_images/{image_name}.jpg'
            with open(destination_image, 'wb') as f:
                for chunk in r:
                    f.write(chunk)
            print("*** We have successfully downloaded the image ***")
            return destination_image
        else:
            attempts += 1
    print(f'Unsuccessful in 30 attempts retrieving {image_url}')
    return None
            
# Routes
## Main page
@app.route('/')
def main():
    alerts = get_alerts_from_db()
    return render_template('dashboard.html', alerts=alerts)

## Webhook Listener
@app.route('/webhook_listener', methods=['GET', 'POST'])
def webhook_listener():
    try:
        meraki_alert = request.get_json()
        print(json.dumps(meraki_alert, indent=2))
        if meraki_alert["alertTypeId"] == "motion_alert":
            # Download image
            download_image(meraki_alert)

            # Add alert to DB
            add_alert_to_db(meraki_alert)

        return "success", 200
    except Exception as e:
        print(e)
        return "exception", 500

# Run app
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5001, debug=True) #https://127.0.0.1:5001
