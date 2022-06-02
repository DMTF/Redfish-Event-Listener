# Copyright Notice:
# Copyright 2017-2022 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfish-Event-Listener/blob/master/LICENSE.md

import traceback
import logging
import json
import ssl
import sys, signal
import re
import socket
from datetime import datetime

import threading
from http_parser.http import HttpStream
from http_parser.reader import SocketReader

from redfish import redfish_client, AuthMethod
import redfish_utilities

my_logger = logging.getLogger()
my_logger.setLevel(logging.DEBUG)
standard_out = logging.StreamHandler(sys.stdout)
standard_out.setLevel(logging.INFO)
my_logger.addHandler(standard_out)

tool_version = '1.1.2'

config = {
    'listenerip': '0.0.0.0',
    'listenerport': 443,
    'usessl': True,
    'certfile': 'cert.pem',
    'keyfile': 'server.key',
    'destination': 'https://contoso.com',
    'eventtypes': None,
    'contextdetail': None,
    'serverIPs': [],
    'usernames': [],
    'passwords': [],
    "logintype": [],
    'verbose': False,
    'format': None,
    'expand': None,
    'resourcetypes': None,
    'registries': None
}

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
            my_logger.info("headers: %s", headers)

            if p.method() == 'POST':
                bodydata = p.body_file().read()
                bodydata = bodydata.decode("utf-8")
                my_logger.info("\n")
                my_logger.info("bodydata: %s", bodydata)
                data_buffer.append(bodydata)
                for eachHeader in headers.items():
                    if eachHeader[0] == 'Host' or eachHeader[0] == 'host':
                        HostDetails = eachHeader[1]

                ### Read the json response and print the output
                my_logger.info("\n")
                my_logger.info("Server IP Address is %s", fromaddr[0])
                my_logger.info("Server PORT number is %s", fromaddr[1])
                my_logger.info("Listener IP is %s", HostDetails)
                my_logger.info("\n")
                outdata = json.loads(bodydata)
                if 'Events' in outdata and config['verbose']:
                    event_array = outdata['Events']
                    for event in event_array:
                        my_logger.info("EventType is %s", event['EventType'])
                        my_logger.info("MessageId is %s", event['MessageId'])
                        if 'EventId' in event:
                            my_logger.info("EventId is %s", event['EventId'])
                        if 'EventGroupId' in event:
                            my_logger.info("EventGroupId is %s", event['EventGroupId'])
                        if 'EventTimestamp' in event:
                            my_logger.info("EventTimestamp is %s", event['EventTimestamp'])
                        if 'Severity' in event:
                            my_logger.info("Severity is %s", event['Severity'])
                        if 'MessageSeverity' in event:
                            my_logger.info("MessageSeverity is %s", event['MessageSeverity'])
                        if 'Message' in event:
                            my_logger.info("Message is %s", event['Message'])
                        if 'MessageArgs' in event:
                            my_logger.info("MessageArgs is %s", event['MessageArgs'])
                        if 'Context' in outdata:
                            my_logger.info("Context is %s", outdata['Context'])
                        my_logger.info("\n")
                if 'MetricValues' in outdata and config['verbose']:
                    metric_array = outdata['MetricValues']
                    my_logger.info("Metric Report Name is: %s", outdata.get('Name'))
                    for metric in metric_array:
                        my_logger.info("Member ID is: %s", metric.get('MetricId'))
                        my_logger.info("Metric Value is: %s", metric.get('MetricValue'))
                        my_logger.info("TimeStamp is: %s", metric.get('Timestamp'))
                        if 'MetricProperty' in metric:
                            my_logger.info("Metric Property is: %s", metric['MetricProperty'])
                        my_logger.info("\n")

                ### Check the context and send the status OK if context matches
                if config['contextdetail'] is not None and outdata.get('Context', None) != config['contextdetail']:
                    my_logger.info("Context ({}) does not match with the server ({})."
                          .format(outdata.get('Context', None), config['contextdetail']))
                res = "HTTP/1.1 200 OK\r\n" \
                      "Connection: close\r\n" \
                      "\r\n"
                connstreamout.send(res.encode())
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

                    my_logger.info("Event Counter for Host %s = %s" % (str(fromaddr[0]), event_count[fromaddr[0]]))
                    my_logger.info("\n")
                    fd = open(outputfile, "a")
                    fd.write("Time:%s Count:%s\nHost IP:%s\nEvent Details:%s\n" % (
                        datetime.now(), event_count[str(fromaddr[0])], str(fromaddr), json.dumps(outdata)))
                    fd.close()
                except Exception as err:
                    my_logger.info(traceback.print_exc())

            if p.method() == 'GET':
                # for x in data_buffer:
                #     my_logger.info(x)
                res = "HTTP/1.1 200 OK\n" \
                      "Content-Type: application/json\n" \
                      "\n" + json.dumps(data_buffer)
                connstreamout.send(res.encode())
                data_buffer.clear()

        except Exception as err:
            outdata = connstreamout.read()
            my_logger.info("Data needs to read in normal Text format.")
            my_logger.info(outdata)

    finally:
        connstreamout.shutdown(socket.SHUT_RDWR)
        connstreamout.close()

import argparse

if __name__ == '__main__':
    """
    Main program
    """

    # Print the tool banner
    logging.info('Redfish Event Listener v{}'.format(tool_version))

    argget = argparse.ArgumentParser(description='Redfish Event Listener (v{}) is a tool that deploys an HTTP(S) server to read and record events from Redfish services.'.format(tool_version))

    # config
    argget.add_argument('-c', '--config', type=str, default='./config.ini', help='Location of the configuration file; default: "./config.ini"')
    argget.add_argument('-v', '--verbose', action='count', default=0, help='Verbose output')
    args = argget.parse_args()

    # Initiate Configuration File
    from configparser import ConfigParser
    parsed_config = ConfigParser()
    parsed_config.read(args.config)

    # Inline helper to help parse lists into arrays
    def parse_list(string: str):
        string = string.strip()
        if re.fullmatch(r'\[\s*\]', string.strip()) or len(string.strip()) == 0:
            return []
        if string[0] == '[' and string[-1] == ']':
            string = string.strip('[]')
        return [x.strip().strip("'\"") for x in string.split(',')]

    # Host Info
    config['listenerip'] = parsed_config.get('SystemInformation', 'ListenerIP')
    config['listenerport'] = parsed_config.getint('SystemInformation', 'ListenerPort')
    config['usessl'] = parsed_config.getboolean('SystemInformation', 'UseSSL')

    # Cert Info
    if config['usessl']:
        config['certfile'] = parsed_config.get('CertificateDetails', 'certfile')
        config['keyfile'] = parsed_config.get('CertificateDetails', 'keyfile')

    # Subscription Details
    if parsed_config.has_section("SubsciptionDetails") and parsed_config.has_section("SubscriptionDetails"):
        my_logger.error('Use either SubsciptionDetails or SubscriptionDetails in config, not both.')
        sys.exit(1)
    my_config_key = "SubsciptionDetails" if parsed_config.has_section("SubsciptionDetails") else "SubscriptionDetails"
    config['destination'] = parsed_config.get(my_config_key, 'Destination')
    if parsed_config.has_option(my_config_key, 'Context'):
        config['contextdetail'] = parsed_config.get(my_config_key, 'Context')
    if parsed_config.has_option(my_config_key, 'EventTypes'):
        config['eventtypes'] = parse_list(parsed_config.get(my_config_key, 'EventTypes'))
    if parsed_config.has_option(my_config_key, 'Format'):
        config['format'] = parsed_config.get(my_config_key, 'Format')
    if parsed_config.has_option(my_config_key, 'Expand'):
        config['expand'] = parsed_config.get(my_config_key, 'Expand')
    if parsed_config.has_option(my_config_key, 'ResourceTypes'):
        config['resourcetypes'] = parse_list(parsed_config.get(my_config_key, 'ResourceTypes'))
    if parsed_config.has_option(my_config_key, 'Registries'):
        config['registries'] = parse_list(parsed_config.get(my_config_key, 'Registries'))
    for k in ['format', 'expand', 'resourcetypes', 'registries', 'contextdetail', 'eventtypes']:
        if config[k] in ['', [], None]:
            config[k] = None

    # Subscription Targets
    config['serverIPs'] = parse_list(parsed_config.get('ServerInformation', 'ServerIPs'))
    config['usernames'] = parse_list(parsed_config.get('ServerInformation', 'UserNames'))
    config['passwords'] = parse_list(parsed_config.get('ServerInformation', 'Passwords'))
    config['logintype'] = ['Session' for x in config['serverIPs']]
    if parsed_config.has_option('ServerInformation', 'LoginType'):
        config['logintype'] = parse_list(parsed_config.get('ServerInformation', 'LoginType'))
        config['logintype'] += ['Session'] * (len(config['serverIPs']) - len(config['logintype']))

    # Other Info
    config['verbose'] = args.verbose
    if config['verbose']:
        print(json.dumps(config, indent=4))

    # Perform the Subscription if provided
    target_contexts = []
    if not (len(config['serverIPs']) == len(config['usernames']) == len(config['passwords'])):
        my_logger.error("Number of ServerIPs does not match UserNames, Passwords, or LoginTypes")
        sys.exit(1)
    elif len(config['serverIPs']) == 0:
        my_logger.info("No subscriptions are specified. Continuing with Listener.")
    else:
        # Create the subscriptions on the Redfish services provided
        for dest, user, passwd, logintype in zip(config['serverIPs'], config['usernames'], config['passwords'], config['logintype']):
            try:
                # Log in to the service
                my_logger.info("ServerIP:: {}".format(dest))
                my_logger.info("UserName:: {}".format(user))
                my_ctx = redfish_client(dest, user, passwd, timeout=30)
                my_ctx.login(auth=logintype.lower())

                # Create the subscription
                response = redfish_utilities.create_event_subscription(my_ctx, config['destination'],
                                                                       client_context=config['contextdetail'],
                                                                       event_types=config['eventtypes'],
                                                                       format=config['format'],
                                                                       expand=config['expand'],
                                                                       resource_types=config['resourcetypes'],
                                                                       registries=config['registries'])

                # Save the subscription info for deleting later
                my_location = response.getheader('Location')
                my_logger.info("Subcription is successful for {}, {}".format(dest, my_location))
                unsub_id = None
                try:
                    # Response bodies are expected to have the event destination
                    unsub_id = response.dict['Id']
                except:
                    # Fallback to determining the Id from the Location header
                    if my_location is not None:
                        unsub_id = my_location.strip('/').split('/')[-1]
                if unsub_id is None:
                    my_logger.error('{} did not provide a location for the subscription; cannot unsubscribe'.format(dest))
                else:
                    target_contexts.append((dest, my_ctx, unsub_id))
            except Exception as e:
                my_logger.info('Unable to subscribe for events with {}'.format(dest))
                my_logger.info(traceback.print_exc())

        my_logger.info("Continuing with Listener.")

    # Accept the TCP connection using certificate validation using Socket wrapper
    useSSL = config['usessl']
    if useSSL:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=config['certfile'], keyfile=config['keyfile'])

    # Bind socket connection and listen on the specified port
    my_host = (config['listenerip'], config['listenerport'])
    my_logger.info('Listening on {}:{} via {}'.format(config['listenerip'], config['listenerport'], 'HTTPS' if useSSL else 'HTTP'))
    event_count = {}
    data_buffer = []

    my_logger.info('Press Ctrl-C to close program')

    # Check if the listener is IPv4 or IPv6; defaults to IPv4 if the lookup fails
    try:
        family = socket.getaddrinfo(config['listenerip'], config['listenerport'])[0][0]
    except:
        family = socket.AF_INET
    socket_server = socket.create_server(my_host, family=family)
    socket_server.listen(5)
    socket_server.settimeout(3)

    def handler_end(sig, frame):
        my_logger.error('\nPress Ctrl-C again to skip unsubscribing and logging out.\n')
        signal.signal(signal.SIGINT, lambda x, y: sys.exit(1))

    def handler(sig, frame):
        my_logger.info('Closing all our subscriptions')
        signal.signal(signal.SIGINT, handler_end)
        socket_server.close()

        for name, ctx, unsub_id in target_contexts:
            my_logger.info('\nClosing {}'.format(name))
            try:
                redfish_utilities.delete_event_subscription(ctx, unsub_id)
                ctx.logout()
            except:
                my_logger.info('Unable to unsubscribe for events with {}'.format(ctx.get_base_url()))
                my_logger.info(traceback.print_exc())

        sys.exit(0)
    signal.signal(signal.SIGINT, handler)

    while True:
        newsocketconn = None
        try:
            ### Socket Binding
            newsocketconn, fromaddr = socket_server.accept()
            try:
                ### Multiple Threads to handle different request from different servers
                my_logger.info('\nSocket connected::')
                threading.Thread(target=process_data, args=(newsocketconn, fromaddr)).start()
            except Exception as err:
                my_logger.info(traceback.print_exc())
        except socket.timeout:
            print('.', end='', flush=True)
        except Exception as err:
            my_logger.info("Exception occurred in socket binding.")
            my_logger.info(traceback.print_exc())
