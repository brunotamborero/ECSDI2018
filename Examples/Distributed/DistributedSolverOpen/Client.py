"""
.. module:: Client

Client
*************

:Description: Client

    Cliente del resolvedor distribuido

:Authors: bejar
    

:Version: 

:Created on: 06/02/2018 8:21 

"""

from __future__ import print_function
from multiprocessing import Process
import socket
import argparse
from FlaskServer import shutdown_server
import requests
from flask import Flask, request, render_template, url_for, redirect

__author__ = 'bejar'

app = Flask(__name__)

problems = {}
probcounter = 0
clientid = ''
diraddress = ''


@app.route("/message", methods=['GET', 'POST'])
def message():
    """
    Entrypoint para todas las comunicaciones

    :return:
    """
    global problems

    if request.form.has_key('message'):
        send_message(request.form['problem'], request.form['message'])
        return redirect(url_for('.iface'))
    else:
        # Respuesta del solver SOLVED|PROBID,SOLUTION
        mess = request.args['message'].split('|')
        if len(mess) == 2:
            messtype, messparam = mess
            if messtype == 'SOLVED':
                solution = messparam.split(',')
                if len(solution) == 2:
                    probid, sol = solution
                    if probid in problems:
                        problems[probid][2] = sol
                    else:  # Para el script de test de stress
                        problems[probid] = ['DUMMY', 'DUMMY', sol]
        return 'OK'


@app.route('/info')
def info():
    """
    Entrada que da informacion sobre el agente a traves de una pagina web
    """
    global problems

    return render_template('clientproblems.html', probs=problems)


@app.route('/iface')
def iface():
    """
    Interfaz con el cliente a traves de una pagina de web
    """
    probtypes = ['ARITH', 'MFREQ']
    return render_template('iface.html', types=probtypes)


@app.route("/stop")
def stop():
    """
    Entrada que para el agente
    """
    shutdown_server()
    return "Parando Servidor"


def send_message(probtype, problem):
    """
    Envia un request a un solver

    mensaje:

    SOLVE|TYPE,PROBLEM,PROBID,CLIENTID

    :param probid:
    :param probtype:
    :param proble:
    :return:
    """
    global probcounter
    global clientid
    global diraddress
    global port
    global problems

    probid = '%s-%2d' % (clientid, probcounter)
    probcounter += 1

    solveradd = requests.get(diraddress + '/message', params={'message': 'SEARCH|SOLVER'}).text
    print(solveradd)
    if 'OK' in solveradd:
        # Le quitamos el OK de la respuesta
        solveradd = solveradd[4:]

        problems[probid] = [probtype, problem, 'PENDING']
        clientaddress = 'http://%s:%d' % (clientid, port)
        mess = 'SOLVE|%s,%s,%s,%s' % (probtype, clientaddress, probid, sanitize(problem))
        resp = requests.get(solveradd + '/message', params={'message': mess}).text
        if 'ERROR' not in resp:
            problems[probid] = [probtype, problem, 'PENDING']
        else:
            problems[probid] = [probtype, problem, 'FAILED SOLVER']
    else:
        problems[probid] = (probtype, problem, 'FAILED DS')


def sanitize(prob):
    """
    remove problematic punctuation signs from the string of the problem
    :param prob:
    :return:
    """
    return prob.replace(',', '*')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--open', help="Define si el servidor esta abierto al exterior o no", action='store_true',
                        default=False)
    parser.add_argument('--port', default=None, type=int, help="Puerto de comunicacion del agente")
    parser.add_argument('--directory', default=None, help="Direccion del servicio de directorio")

    # parsing de los parametros de la linea de comandos
    args = parser.parse_args()

    # Configuration stuff
    if args.port is None:
        port = 9001
    else:
        port = args.port

    if args.open:
        hostname = '0.0.0.0'
        clientid = 'localhost'
    else:
        clientid = hostname = socket.gethostname()

    if args.directory is None:
        diraddress = 'http://polaris.cs.upc.edu:9000'
    else:
        diraddress = args.directory

    # Ponemos en marcha el servidor Flask
    app.run(host=hostname, port=port, debug=True, use_reloader=False)
