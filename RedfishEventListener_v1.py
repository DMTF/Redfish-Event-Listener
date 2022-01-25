# Copyright Notice:
# Copyright 2017-2019 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfish-Event-Listener/blob/master/LICENSE.md

import socket
import traceback
import json
import ssl
from datetime import datetime
import sys
import re

import requests
import threading
from http_parser.http import HttpStream
from http_parser.reader import SocketReader

import logging
my_logger = logging.getLogger()
my_logger.setLevel(logging.DEBUG)
standard_out = logging.StreamHandler(sys.stdout)
standard_out.setLevel(logging.INFO)
my_logger.addHandler(standard_out)

tool_version = '1.0.3'

config = {
    'listenerip': '0.0.0.0',
    'listenerport': 443,
    'usessl': True,
    'certfile': 'cert.pem',
    'keyfile': 'server.key',
    'destination': 'https://contoso.com',
    'eventtypes': ['Alert'],
    'contextdetail': 'Public',
    'protocol': 'Redfish',
    'subscriptionURI': '/redfish/v1/EventService/Subscriptions',
    'serverIPs': [],
    'usernames': [],
    'passwords': [],
    'certcheck': True
}

### Function to perform GET/PATCH/POST/DELETE operation for REDFISH URI
def callResourceURI(ConfigURI, URILink, Method='GET', payload=None, header=None, LocalUser=None, LocalPassword=None):
    print("URI is: ", ConfigURI + URILink)
    certcheck = config['certcheck']
    try:
        startTime2 = datetime.now()
        response = statusCode = expCode = None
        if certcheck:
            if Method == 'GET':
                response = requests.get(ConfigURI + URILink, auth=(LocalUser, LocalPassword), timeout=30)
            elif Method == 'PATCH':
                response = requests.patch(ConfigURI + URILink, data=payload, auth=(LocalUser, LocalPassword),
                                          timeout=30)
            elif Method == 'POST':
                response = requests.post(ConfigURI + URILink, data=payload, auth=(LocalUser, LocalPassword), timeout=30)
        else:
            if header is None:
                if Method == 'GET':
                    response = requests.get(ConfigURI + URILink, verify=False, auth=(LocalUser, LocalPassword),
                                            timeout=30)
                elif Method == 'PATCH':
                    header = {"content-type": "application/json"}
                    response = requests.patch(ConfigURI + URILink, data=payload, verify=False,
                                              auth=(LocalUser, LocalPassword), headers=header, timeout=30)
                elif Method == 'POST':
                    header = {"content-type": "application/json"}
                    response = requests.post(ConfigURI + URILink, data=payload, verify=False,
                                             auth=(LocalUser, LocalPassword), headers=header, timeout=30)
                elif Method == 'CREATE':
                    header = {"content-type": "application/json"}
                    response = requests.post(ConfigURI + URILink, data=payload, verify=False, headers=header,
                                             timeout=30)
                elif Method == 'DELETE':
                    header = {"content-type": "application/json"}
                    response = requests.delete(ConfigURI + URILink, data=payload, verify=False,
                                               auth=(LocalUser, LocalPassword), headers=header, timeout=30)
            else:
                if Method == 'GET':
                    response = requests.get(ConfigURI + URILink, verify=False, headers=header, timeout=30)
                elif Method == 'PATCH':
                    response = requests.patch(ConfigURI + URILink, data=payload, verify=False, headers=header,
                                              timeout=30)
                elif Method == 'POST':
                    response = requests.post(ConfigURI + URILink, data=payload, verify=False, headers=header,
                                             timeout=30)
                elif Method == 'DELETE':
                    response = requests.delete(ConfigURI + URILink, data=payload, verify=False, headers=header,
                                               timeout=30)

        endTime2 = datetime.now()
        execTime2 = endTime2 - startTime2

        if response is not None:
            statusCode = response.status_code
        if Method == 'GET':
            expCode = 200
        elif Method == 'PATCH':
            expCode = [200, 204]
        elif Method == 'POST' or Method == 'CREATE':
            expCode = [200, 201, 204]
        elif Method == 'DELETE':
            expCode = [200, 201, 204]

        print('Method = {}, status = {}, expected status = {}'.format(Method, statusCode, expCode))

        try:
            decoded = response.json()
        except:
            decoded = ""
        if (Method == 'GET' and statusCode == expCode):
            return statusCode, True, decoded, response.headers, str(execTime2)
        elif (Method == 'PATCH' and statusCode in expCode):
            return statusCode, True, decoded, response.headers, str(execTime2)
        elif (Method == 'DELETE' and statusCode in expCode):
            return statusCode, True, decoded, response.headers, str(execTime2)
        elif Method == 'POST' and (statusCode in expCode):
            return statusCode, True, decoded, response.headers, str(execTime2)
        elif (Method == 'CREATE') and (statusCode in expCode):
            Token = response.headers['X-Auth-Token']
            print("Token value: ", Token)
            header = {"X-Auth-Token": Token}
            return statusCode, True, "", response.headers, str(execTime2)
        else:
            return statusCode, False, "", response.headers, str(execTime2)

    except Exception as err:
        print("Exception occurred in while performing subscription.")
        print(traceback.print_exc())
        return None, False, "", [], ""


### Create Subsciption on the servers provided by users if any
def PerformSubscription(payload, dest, user, passwd, header=None):
    print("ServerIP:::", dest)
    print("UserName:::", user)
    statusCode, Status, body, headers, ExecTime = callResourceURI(dest, SubscriptionURI,
                                                                    Method='POST', payload=payload, header={},
                                                                    LocalUser=user,
                                                                    LocalPassword=passwd)
    if Status:
        print("Subcription is successful for %s" % dest)
    else:
        print("Subcription is not successful for %s or it is already present." % dest)


### Function to read data in json format using HTTP Stream reader, parse Headers and Body data, Response status OK to service and Update the output into file
def process_data(newsocketconn, fromaddr):
    if useSSL:
        connstreamout = context.wrap_socket(newsocketconn, server_side=True)
    else:
        connstreamout = newsocketconn
    ### Output File Name
    outputfile = "Events_" + str(fromaddr[0]) + ".txt"
    logfile = "TimeStamp.log"
    global event_count, data_buffer
    outdata = headers = HostDetails = ""
    try:
        try:
            ### Read the json response using Socket Reader and split header and body
            r = SocketReader(connstreamout)
            p = HttpStream(r)
            headers = p.headers()
            print("headers: ", headers)

            if p.method() == 'POST':
                bodydata = p.body_file().read()
                bodydata = bodydata.decode("utf-8")
                print("\n")
                print("bodydata: ", bodydata)
                data_buffer.append(bodydata)
                for eachHeader in headers.items():
                    if eachHeader[0] == 'Host' or eachHeader[0] == 'host':
                        HostDetails = eachHeader[1]

                ### Read the json response and print the output
                print("\n")
                print("Server IP Address is ", fromaddr[0])
                print("Server PORT number is ", fromaddr[1])
                print("Listener IP is ", HostDetails)
                print("\n")
                outdata = json.loads(bodydata)
                if 'Events' in outdata and verbose:
                    event_array = outdata['Events']
                    for event in event_array:
                        print("EventType is ", event['EventType'])
                        print("MessageId is ", event['MessageId'])
                        if 'EventId' in event:
                            print("EventId is ", event['EventId'])
                        if 'EventTimestamp' in event:
                            print("EventTimestamp is ", event['EventTimestamp'])
                        if 'Severity' in event:
                            print("Severity is ", event['Severity'])
                        if 'Message' in event:
                            print("Message is ", event['Message'])
                        if 'MessageArgs' in event:
                            print("MessageArgs is ", event['MessageArgs'])
                        if 'Context' in outdata:
                            print("Context is ", outdata['Context'])
                        print("\n")
                if 'MetricValues' in outdata and verbose:
                    metric_array = outdata['MetricValues']
                    print("Metric Report Name is: ", outdata.get('Name'))
                    for metric in metric_array:
                        print("Member ID is: ", metric.get('MetricId'))
                        print("Metric Value is: ", metric.get('MetricValue'))
                        print("TimeStamp is: ", metric.get('Timestamp'))
                        if 'MetricProperty' in metric:
                            print("Metric Property is: ", metric['MetricProperty'])
                        print("\n")

                ### Check the context and send the status OK if context matches
                if outdata.get('Context', None) != ContextDetail:
                    print("Context ({}) does not match with the server ({})."
                          .format(outdata.get('Context', None), ContextDetail))
                StatusCode = """HTTP/1.1 200 OK\r\n\r\n"""
                connstreamout.send(bytes(StatusCode, 'UTF-8'))
                with open(logfile, 'a') as f:
                    if 'EventTimestamp' in outdata:
                        receTime = datetime.now()
                        sentTime = datetime.strptime(outdata['EventTimestamp'], "%Y-%m-%d %H:%M:%S.%f")
                        f.write("%s    %s    %sms\n" % (
                            sentTime.strftime("%Y-%m-%d %H:%M:%S.%f"), receTime, (receTime - sentTime).microseconds / 1000))
                    else:
                        f.write('No available timestamp.')

                try:
                    if event_count.get(str(fromaddr[0])):
                        event_count[str(fromaddr[0])] = event_count[str(fromaddr[0])] + 1
                    else:
                        event_count[str(fromaddr[0])] = 1

                    print("Event Counter for Host %s = %s" % (str(fromaddr[0]), event_count[fromaddr[0]]))
                    print("\n")
                    fd = open(outputfile, "a")
                    fd.write("Time:%s Count:%s\nHost IP:%s\nEvent Details:%s\n" % (
                        datetime.now(), event_count[str(fromaddr[0])], str(fromaddr), json.dumps(outdata)))
                    fd.close()
                except Exception as err:
                    print(traceback.print_exc())

            if p.method() == 'GET':
                # for x in data_buffer:
                #     print(x)
                res = "HTTP/1.1 200 OK\n" \
                      "Content-Type: application/json\n" \
                      "\n" + json.dumps(data_buffer)
                connstreamout.send(res.encode())
                data_buffer.clear()


        except Exception as err:
            outdata = connstreamout.read()
            print("Data needs to read in normal Text format.")
            print(outdata)

    finally:
        connstreamout.shutdown(socket.SHUT_RDWR)
        connstreamout.close()

import argparse

if __name__ == '__main__':
    """
    Main program
    """

    ### Print the tool banner
    logging.info('Redfish Event Listener v{}'.format(tool_version))

    argget = argparse.ArgumentParser(description='Redfish Event Listener (v{}) is a tool that deploys an HTTP(S) server to read and record events from Redfish services.'.format(tool_version))

    # config
    argget.add_argument('-c', '--config', type=str, default='./config.ini', help='Specifies the location of our configuration file (default: ./config.ini)')
    argget.add_argument('-v', '--verbose', action='count', default=0, help='Verbosity of tool in stdout')
    args = argget.parse_args()

    ### Initializing the global parameter
    from configparser import ConfigParser
    parsed_config = ConfigParser()
    parsed_config.read(args.config)

    def parse_list(string: str):
        if re.fullmatch(r'\[\]|\[.*\]', string):
            string = string.strip('[]')
        return [x.strip("'\"").strip() for x in string.split(',')]

    config['listenerip'] = parsed_config.get('SystemInformation', 'ListenerIP')
    config['listenerport'] = parsed_config.getint('SystemInformation', 'ListenerPort')
    config['usessl'] = parsed_config.getboolean('SystemInformation', 'UseSSL')

    config['certfile'] = parsed_config.get('CertificateDetails', 'certfile')
    config['keyfile'] = parsed_config.get('CertificateDetails', 'keyfile')

    config['destination'] = parsed_config.get('SubsciptionDetails', 'Destination')
    config['contextdetail'] = parsed_config.get('SubsciptionDetails', 'Context')
    config['protocol'] = parsed_config.get('SubsciptionDetails', 'Protocol')
    config['subscriptionURI'] = parsed_config.get('SubsciptionDetails', 'SubscriptionURI')
    config['eventtypes'] = parse_list(parsed_config.get('SubsciptionDetails', 'EventTypes'))

    config['serverIPs'] = parse_list(parsed_config.get('ServerInformation', 'ServerIPs'))
    config['usernames'] = parse_list(parsed_config.get('ServerInformation', 'UserNames'))
    config['passwords'] = parse_list(parsed_config.get('ServerInformation', 'Passwords'))

    config['certcheck'] = parsed_config.getboolean('ServerInformation', 'certcheck')
    config['verbose'] = args.verbose

    ### Perform the Subscription if provided
    SubscriptionURI, Protocol, ContextDetail, EventTypes, Destination = config['subscriptionURI'], config['protocol'], config['contextdetail'], config['eventtypes'], config['destination']

    payload = {
        'Destination': config['destination'],
        'EventTypes': config['eventtypes'],
        'Context': config['contextdetail'],
        'Protocol': config['protocol']
    }

    if not (len(config['serverIPs']) == len(config['usernames']) == len(config['passwords'])):
        my_logger.info("Number of ServerIPs does not match UserNames and Passwords")
    elif len(config['serverIPs']) == 0:
        my_logger.info("No subscriptions are specified. Continuing with Listener.")
    else:
        for dest, user, passwd in zip(config['serverIPs'], config['usernames'], config['passwords']):
            PerformSubscription(payload, dest, user, passwd)
        my_logger.info("Continuing with Listener.")

    ### Accept the TCP connection using certificate validation using Socket wrapper
    useSSL = config['usessl']
    if useSSL:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=config['certfile'], keyfile=config['keyfile'])

    # exit gracefully on CTRL-C
    import signal
    signal.signal(signal.SIGINT, lambda: sys.exit(0))

    ### Bind socket connection and listen on the specified port
    bindsocket = socket.socket()
    bindsocket.bind((config['listenerip'], config['listenerport']))
    bindsocket.listen(5)
    my_logger.info('Listening on {}:{} via {}'.format(config['listenerip'], config['listenerport'], 'HTTPS' if useSSL else 'HTTP'))
    event_count = {}
    data_buffer = []

    while True:
        try:
            ### Socket Binding
            newsocketconn, fromaddr = bindsocket.accept()
            try:
                ### Multiple Threads to handle different request from different servers
                threading.Thread(target=process_data, args=(newsocketconn, fromaddr)).start()
            except Exception as err:
                print(traceback.print_exc())
        except Exception as err:
            print("Exception occurred in socket binding.")
            print(traceback.print_exc())
