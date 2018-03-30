# Copyright Notice:
# Copyright 2017 Distributed Management Task Force, Inc. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfish-Event-Listener/blob/master/LICENSE.md

import socket
import time
import traceback
import json
from datetime import datetime as DT
import configparser
import sys
import threading
import requests
from http_parser.http import HttpStream
from http_parser.reader import SocketReader
import signal
import ssl

### Print the tool banner
print('Redfish Event Listener v1.0.1')

### Initializing the global parameter
config = configparser.ConfigParser()
config.read('config.ini')
listenerip = config.get('SystemInformation', 'ListenerIP')
listenerport = config.get('SystemInformation', 'ListenerPort')
useSSL = config.getboolean('SystemInformation', 'UseSSL')
certfile = config.get('CertificateDetails', 'certfile')
keyfile = config.get('CertificateDetails', 'keyfile')

Destination = config.get('SubsciptionDetails', 'Destination')
EventType = config.get('SubsciptionDetails', 'EventTypes')
EventTypeString = [EventType]
EventTypes = json.dumps(EventTypeString)
print("EventTypes: ", EventTypes)
ContextDetail = config.get('SubsciptionDetails', 'Context')
Protocol = config.get('SubsciptionDetails', 'Protocol')
SubscriptionURI = config.get('SubsciptionDetails', 'SubscriptionURI')

ServerIPs = config.get('ServerInformation', 'ServerIPs')
UserNames = config.get('ServerInformation', 'UserNames')
Passwords = config.get('ServerInformation', 'Passwords')
certcheck = config.getboolean('ServerInformation', 'certcheck')

if useSSL:
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)

# exit gracefully on CTRL-C
signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))

### Bind socket connection and listen on the specified port
bindsocket = socket.socket()
bindsocket.bind((listenerip, int(listenerport)))
bindsocket.listen(5)
print('Listening on {}:{} via {}'.format(listenerip, listenerport, 'HTTPS' if useSSL else 'HTTP'))
event_count = {}


### Function to perform GET/PATCH/POST/DELETE operation for REDFISH URI
def callResourceURI(ConfigURI, URILink, Method='GET', payload=None, header=None, LocalUser=None, LocalPassword=None):
    print("URI is: ", ConfigURI + URILink)
    try:
        startTime2 = DT.now()
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

        endTime2 = DT.now()
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


def GetPostPayload(AttributeNameList, AttributeValueList, DataType="string"):
    payload = ""
    if DataType.lower() == "string":
        for i in range(0, len(AttributeNameList)):
            if i == len(AttributeNameList) - 1:
                payload = payload + "\"" + str(AttributeNameList[i]) + "\":\"" + str(AttributeValueList[i]) + "\""
            elif AttributeNameList[i] == "EventTypes":
                payload = payload + "\"" + str(AttributeNameList[i]) + "\":" + str(AttributeValueList[i]) + ","
            else:
                payload = payload + "\"" + str(AttributeNameList[i]) + "\":\"" + str(AttributeValueList[i]) + "\","

        payload = "{" + payload + "}"
        print("Payload details are ", payload)

    return payload


### Create Subsciption on the servers provided by users if any
def PerformSubscription():
    global ServerIPs, UserNames, Passwords, Destination, EventTypes, ContextDetail, Protocol, SubscriptionURI
    ServerIPList = ServerIPs.split(",")
    UserNameList = UserNames.split(",")
    PasswordList = Passwords.split(",")
    AttributeNameList = ['Destination', 'EventTypes', 'Context', 'Protocol']
    AttributeValueList = [Destination, EventTypes, ContextDetail, Protocol]

    if (len(ServerIPList) == len(UserNameList) == len(PasswordList)) and (len(ServerIPList) > 0) and (
    not (ServerIPs.strip() == "")):
        print("Count of Server is ", len(ServerIPList))
        payload = GetPostPayload(AttributeNameList, AttributeValueList, "string")
        for i in range(0, len(ServerIPList)):
            print("ServerIPList:::", ServerIPList[i])
            print("UserNameList:::", UserNameList[i])
            statusCode, Status, body, headers, ExecTime = callResourceURI(ServerIPList[i].strip(), SubscriptionURI,
                                                                          Method='POST', payload=payload, header=None,
                                                                          LocalUser=UserNameList[i].strip(),
                                                                          LocalPassword=PasswordList[i].strip())

            if Status:
                print("Subcription is successful for %s" % ServerIPList[i])

            else:
                print("Subcription is not successful for %s or it is already present." % ServerIPList[i])

    else:
        print("\nNo subscriptions are specified. Continuing with Listener.")

    print("\nContinuing with Listener.")


### Function to read data in json format using HTTP Stream reader, parse Headers and Body data, Response status OK to service and Update the output into file
def read_output_data(newsocketconn, fromaddr):
    if useSSL:
        connstreamout = context.wrap_socket(newsocketconn, server_side=True)
    else:
        connstreamout = newsocketconn
    ### Output File Name
    outputfile = "Events_" + str(fromaddr[0]) + ".txt"
    global event_count
    outdata = headers = HostDetails = ""
    try:
        try:
            ### Read the json response using Socket Reader and split header and body
            r = SocketReader(connstreamout)
            p = HttpStream(r)
            headers = p.headers()
            print("headers: ", headers)
            bodydata = p.body_file().read()
            bodydata = bodydata.decode("utf-8")
            print("bodydata: ", bodydata)
            for eachHeader in headers.items():
                if eachHeader[0] == 'Host' or eachHeader[0] == 'host':
                    HostDetails = eachHeader[1]

            ### Read the json response and print the output
            print("\n")
            print("Server IP Address is ", fromaddr[0])
            print("Server PORT number is ", fromaddr[1])
            print("Listener IP is ", HostDetails)
            outdata = json.loads(bodydata)
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

        except Exception as err:
            outdata = connstreamout.read()
            print("Data needs to read in normal Text format.")
            print(outdata)

        ### Check the context and send the status OK if context matches
        if outdata.get('Context', None) != ContextDetail:
            print("Context ({}) does not match with the server ({})."
                  .format(outdata.get('Context', None), ContextDetail))
        StatusCode = """HTTP/1.1 200 OK\r\n\r\n"""
        connstreamout.send(bytes(StatusCode, 'UTF-8'))

        try:
            if event_count.get(str(fromaddr[0])):
                event_count[str(fromaddr[0])] = event_count[str(fromaddr[0])] + 1
            else:
                event_count[str(fromaddr[0])] = 1

            print("Event Counter for Host %s is %s" % (str(fromaddr[0]), event_count[fromaddr[0]]))
            print("\n")
            fd = open(outputfile, "a")
            fd.write("Time:%s Count:%s\nHost IP:%s\nEvent Details:%s\n" % (
                time.ctime(), event_count[str(fromaddr[0])], str(fromaddr), outdata))
            fd.close()
        except Exception as err:
            print(traceback.print_exc())

    finally:
        connstreamout.shutdown(socket.SHUT_RDWR)
        connstreamout.close()


### Script starts here
### Perform the Subscription if provided
PerformSubscription()

### Accept the TCP connection using certificate validation using Socket wrapper


while True:
    try:
        ### Socket Binding
        newsocketconn, fromaddr = bindsocket.accept()
        try:
            ### Multiple Threads to handle different request from different servers
            threading.Thread(target=read_output_data, args=(newsocketconn, fromaddr)).start()
        except Exception as err:
            print(traceback.print_exc())
    except Exception as err:
        print("Exception occurred in socket binding.")
        print(traceback.print_exc())
