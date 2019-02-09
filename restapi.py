#!/usr/bin/python3
import os
import sys
import simplejson as json
from flask import Flask, request, g
from podcomm.pdm import Pdm
from podcomm.pod import Pod
from podcomm.packet import Packet
from podcomm.rileylink import RileyLink
from podcomm.crc import crc8
from decimal import *
import base64

app = Flask(__name__)

def get_pdm():
    pod = Pod.Load("pod.json")
    pdm = Pdm(pod)
    return pdm

def respond_ok(d = {}):
    return json.dumps({ "success": True, "result:": d})

def respond_error(msg = "Unknown"):
    return json.dumps({ "success": False, "error:": msg})

def verify_auth(request):
    t = request.args.get('token')
    if t is not None:
        token = base64.b64decode(t)
        delete_token(token)
        return
    raise ValueError("Authentication failed")

def delete_token(token):
    with open(".tokens", "a+b") as tokens:
        tokens.seek(0, 0)
        found = False
        while True:
            read_token = tokens.read(32)
            if len(read_token) < 32:
                break
            if read_token == token:
                found = True
                break

        if found:
            while True:
                read_token = tokens.read(32)
                if len(read_token) < 32:
                    tokens.seek(-32 - len(read_token), 1)
                    break
                tokens.seek(-64, 1)
                tokens.write(read_token)
                tokens.seek(32, 1)
            tokens.truncate()

    if not found:
        raise ValueError("Invalid token")

@app.route("/pdm/test")
def test():
    try:
        verify_auth(request)
        return respond_ok("goooood")
    except:
        return respond_error(msg = str(sys.exc_info()))

@app.route("/pdm/token")
def create_token():
    try:
        with open(".tokens", "a+b") as tokens:
            token = bytes(os.urandom(32))
            tokens.write(token)
        return respond_ok(base64.b64encode(token))
    except:
        return respond_error(msg = str(sys.exc_info()))

@app.route("/pdm/status")
def get_status():
    try:
        verify_auth(request)
        pdm = get_pdm()
        pdm.updatePodStatus()
        return respond(True, pdm.pod.__dict__)
    except:
        return respond_error(msg = sys.exc_info()[0])

@app.route("/pdm/newpod")
def grab_pod():
    try:
        verify_auth(request, g)
        pod = Pod()
        pod.lot = request.args.get('lot')
        pod.tid = request.args.get('tid')

        r = RileyLink()
        r.connect()
        r.init_radio()
        p = None
        while True:
            data = r.get_packet(30000)
            if data is not None and len(data) > 2:
                calc = crc8(data[2:-1])
                if data[-1] == calc:
                    p = Packet(0, data[2:-1])
                    break
        r.disconnect()

        if p is None:
            respond_error("No pdm packet detected")

        pod.address = p.address
        pod.Save("pod.json")
        return respond_ok({"address": p.address})
    except:
        return respond_error(msg = sys.exc_info()[0])

@app.route("/pdm/bolus")
def bolus():
    try:
        verify_auth(request, g)
        pdm = get_pdm()
        amount = Decimal(request.args.get('amount'))
        pdm.bolus(amount, False)
        return respond(True, pdm.pod.__dict__)
    except:
        return respond_error(msg = sys.exc_info()[0])

@app.route("/pdm/cancelbolus")
def cancelbolus():
    try:
        verify_auth(request, g)
        pdm = get_pdm()
        pdm.cancelbolus()
        return respond(True, pdm.pod.__dict__)
    except:
        return respond_error(msg = sys.exc_info()[0])

@app.route("/pdm/tempbasal")
def tempbasal():
    try:
        verify_auth(request, g)
        pdm = get_pdm()
        amount = Decimal(request.args.get('amount'))
        hours = Decimal(request.args.get('hours'))
        pdm.setTempBasal(amount, hours, False)
        return respond(True, pdm.pod.__dict__)
    except:
        return respond_error(msg = sys.exc_info()[0])

@app.route("/pdm/canceltempbasal")
def canceltempbasal():
    try:
        verify_auth(request, g)
        pdm = get_pdm()
        pdm.cancelTempBasal()
        return respond(True, pdm.pod.__dict__)
    except:
        return respond_error(msg = sys.exc_info()[0])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4444)
