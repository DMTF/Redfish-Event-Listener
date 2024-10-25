# Copyright Notice:
# Copyright 2017-2024 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfish-Event-Listener/blob/main/LICENSE.md

import traceback
import logging
import json
import ssl
import sys
import signal
import re
from datetime import datetime
import argparse
from redfish import redfish_client
import redfish_utilities
from http.server import BaseHTTPRequestHandler, HTTPServer

my_logger = logging.getLogger()
my_logger.setLevel(logging.DEBUG)
standard_out = logging.StreamHandler(sys.stdout)
standard_out.setLevel(logging.INFO)
my_logger.addHandler(standard_out)

tool_version = '1.1.6'

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

event_count = {}

class RedfishEventListenerServer(BaseHTTPRequestHandler):
    """
    Redfish Event Listener Server
    Handles HTTP requests
    """

    def do_POST(self):
        # Check for the content length
        try:
            length = int(self.headers["content-length"])
        except:
            my_logger.error("{} - No Content-Length header".format(self.client_address[0]))
            self.send_response(411)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        # Read the data
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except:
            my_logger.error("{} - No data received or data is not JSON".format(self.client_address[0]))
            self.send_response(400)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        my_logger.info("")
        my_logger.info("Event received from {}".format(self.client_address[0]))

        # Print out the events
        if 'Events' in payload and config['verbose']:
            event_array = payload['Events']
            for event in event_array:
                my_logger.info("  EventType: %s", event.get('EventType'))
                my_logger.info("  MessageId: %s", event.get('MessageId'))
                if 'EventId' in event:
                    my_logger.info("  EventId: %s", event['EventId'])
                if 'EventGroupId' in event:
                    my_logger.info("  EventGroupId: %s", event['EventGroupId'])
                if 'EventTimestamp' in event:
                    my_logger.info("  EventTimestamp: %s", event['EventTimestamp'])
                if 'Severity' in event:
                    my_logger.info("  Severity: %s", event['Severity'])
                if 'MessageSeverity' in event:
                    my_logger.info("  MessageSeverity: %s", event['MessageSeverity'])
                if 'Message' in event:
                    my_logger.info("  Message: %s", event['Message'])
                if 'MessageArgs' in event:
                    my_logger.info("  MessageArgs: %s", event['MessageArgs'])
                if 'Context' in payload:
                    my_logger.info("  Context: %s", payload['Context'])
                my_logger.info("")
        if 'MetricValues' in payload and config['verbose']:
            metric_array = payload['MetricValues']
            my_logger.info("  Metric Report Name: %s", payload.get('Name'))
            for metric in metric_array:
                my_logger.info("  MetricId: %s", metric.get('MetricId'))
                my_logger.info("  MetricValue: %s", metric.get('MetricValue'))
                my_logger.info("  Timestamp: %s", metric.get('Timestamp'))
                if 'MetricProperty' in metric:
                    my_logger.info("  MetricProperty is: %s", metric['MetricProperty'])
                my_logger.info("\n")

        # Update the timestamp log
        with open("TimeStamp.log", 'a') as f:
            if 'EventTimestamp' in payload:
                try:
                    receTime = datetime.now()
                    sentTime = datetime.strptime(payload['EventTimestamp'], "%Y-%m-%d %H:%M:%S.%f")
                    f.write("%s    %s    %sms\n" % (
                        sentTime.strftime("%Y-%m-%d %H:%M:%S.%f"), receTime, (receTime - sentTime).microseconds / 1000))
                except:
                    f.write('Timestamp not in the correct format.\n')
            else:
                f.write('No available timestamp.\n')

        # Log the event
        outputfile = "Events_" + self.client_address[0] + ".txt"
        try:
            if event_count.get(self.client_address[0]):
                event_count[self.client_address[0]] = event_count[self.client_address[0]] + 1
            else:
                event_count[self.client_address[0]] = 1

            my_logger.info("Event Counter for Host %s = %s" % (self.client_address[0], event_count[self.client_address[0]]))
            my_logger.info("")
            fd = open(outputfile, "a")
            fd.write("Time:%s Count:%s\nHost IP:%s\nEvent Details:%s\n" % (
                datetime.now(), event_count[self.client_address[0]], self.client_address[0], json.dumps(payload)))
            fd.close()
        except Exception:
            my_logger.info(traceback.print_exc())

        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()


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
    # Note: Older versions of the tool contained a spelling error for 'Subscription'; need to support both variants to maintain compatibility with older config files
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
                my_logger.info("Subscription is successful for {}, {}".format(dest, my_location))
                unsub_id = None
                try:
                    # Response bodies are expected to have the event destination
                    unsub_id = response.dict['Id']
                except Exception:
                    # Fallback to determining the Id from the Location header
                    if my_location is not None:
                        unsub_id = my_location.strip('/').split('/')[-1]
                if unsub_id is None:
                    my_logger.error('{} did not provide a location for the subscription; cannot unsubscribe'.format(dest))
                else:
                    target_contexts.append((dest, my_ctx, unsub_id))
            except Exception:
                my_logger.info('Unable to subscribe for events with {}'.format(dest))
                my_logger.info(traceback.print_exc())

        my_logger.info("Continuing with Listener.")

    event_server = HTTPServer((config['listenerip'], config['listenerport']), RedfishEventListenerServer)
    def clean_subscriptions():
        for name, ctx, unsub_id in target_contexts:
            my_logger.info('\nClosing {}'.format(name))
            try:
                redfish_utilities.delete_event_subscription(ctx, unsub_id)
                ctx.logout()
            except Exception:
                my_logger.info('Unable to unsubscribe for events with {}'.format(ctx.get_base_url()))
                my_logger.info(traceback.print_exc())
    def sigterm_handler(signal_number, frame):
        my_logger.info("SIGTERM: Shutting down the Redfish Event Listener")
        event_server.server_close()
        clean_subscriptions()
        sys.exit(0)
    signal.signal(signal.SIGTERM, sigterm_handler)
    if config['usessl']:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=config['certfile'], keyfile=config['keyfile'])
        event_server.socket = context.wrap_socket(event_server.socket, server_side=True)

    my_logger.info("Listening for events...")
    my_logger.info('Press Ctrl-C to close program')
    try:
        event_server.serve_forever()
    except KeyboardInterrupt:
        pass
    my_logger.info("Shutting down the Redfish Event Listener")
    event_server.server_close()
    clean_subscriptions()
    sys.exit(0)
