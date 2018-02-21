"""
.. module:: LetterCounter

WordCounter
*************

:Description: LetterCounter

    Calcula la frecuencia de las letras de un string y retorna las 10 mas frecuentes

:Authors: bejar
    

:Version: 

:Created on: 06/02/2018 15:58 

"""

from __future__ import print_function
import socket
import argparse
from FlaskServer import shutdown_server
import requests
from flask import Flask, request
from requests import ConnectionError
from multiprocessing import Process
from collections import Counter

__author__ = 'bejar'

app = Flask(__name__)

problems = {}
solvers = []
probcounter = 0


@app.route("/message")
def message():
    """
    Entrypoint para todas las comunicaciones

    :return:
    """
    mess = request.args['message']

    if '|' not in mess:
        return 'ERROR: INVALID MESSAGE'
    else:
        # Sintaxis de los mensajes "TIPO|PARAMETROS"
        messtype, messparam = mess.split('|')

        if messtype not in ['SOLVE']:
            return 'ERROR: INVALID REQUEST'
        else:
            # parametros mensaje SOLVE = "SOLVERADDRESS,PROBID,PROB"
            if messtype == 'SOLVE':
                param = messparam.split(',')
                if len(param) == 3:
                    solveraddress, probid, prob = param
                    p1 = Process(target=solver, args=(solveraddress, probid, prob))
                    p1.start()
                    return 'OK'
                else:
                    return 'ERROR: WRONG PARAMETERS'


@app.route("/stop")
def stop():
    """
    Entrada que para el agente
    """
    shutdown_server()
    return "Parando Servidor"


def solver(saddress, probid, prob):
    """
    Hace la resolucion de un problema

    :param param:
    :return:
    """
    try:
        res = ''.join([x for x, _ in Counter(prob).most_common(10)])
    except Exception:
        res = 'ERROR: NON ASCII CHARACTERS'
    requests.get(saddress + '/message', params={'message': 'SOLVED|%s,%s' % (probid, res)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--open', help="Define si el servidor esta abierto al exterior o no", action='store_true',
                        default=True)
    parser.add_argument('--port', type=int, help="Puerto de comunicacion del agente")
    parser.add_argument('--directory', default=None, help="Direccion del servicio de directorio")

    # parsing de los parametros de la linea de comandos
    args = parser.parse_args()

    # Configuration stuff
    if args.port is None:
        port = 9020
    else:
        port = args.port

    if args.open:
        hostname = '0.0.0.0'
    else:
        hostname = socket.gethostname()

    if args.directory is None:
        diraddress = 'http://polaris.cs.upc.edu:9000'
    else:
        diraddress = args.directory

    # El solver aritmetico busca en el servicio de directorio 2 solvers con los que asociarse
    solveradd = 'http://%s:%d' % (socket.gethostname(), port)
    solverid = socket.gethostname().split('.')[0] + '-' + str(port)
    mess = 'SEARCH|SOLVER,2'

    done = False
    while not done:
        try:
            resp = requests.get(diraddress + '/message', params={'message': mess}).text
            done = True
        except ConnectionError:
            pass

    # Si tenemos respuesta preguntamos a los solvers si nos podemos registrar con ellos
    if 'OK' in resp:
        laddr = resp[4:].split(',')  # Obtenemos las direcciones de los solvers
        reg = []
        for addr in laddr:
            mess = 'CONTRACT|MFREQ,%s,%s' % (solverid, solveradd)
            done = False
            while not done:
                try:
                    resp = requests.get(addr + '/message', params={'message': mess}).text
                    done = True
                except ConnectionError:
                    pass
            if 'OK' in resp:
                reg.append(addr)

    # Si nos hemos podido registrar con alguien
    if len(reg) != 0:
        # Guardamos las direcciones de los solvers asignados
        solvers = reg

        # Ponemos en marcha el servidor Flask
        app.run(host=hostname, port=port, debug=True, use_reloader=False)
        for soladd in solvers:
            mess = 'FIRED|%s' % (solverid)
            requests.get(soladd + '/message', params={'message': mess})
    else:
        print('NO SOLVERS AVAILABLE FOR HIRE')