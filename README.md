# Redfish Event Listener

Copyright 2017-2019 DMTF. All rights reserved.

## About

The Redfish Event Listener is a lightweight HTTP(S) server that can be deployed to read and record events from Redfish services.  It can also subscribe to multiple services.

## Pre Requisites:

The Redfish Event Listener is based on Python 3 and the client system is required to have the Python framework installed before the tool can be installed and executed on the system.  Additionally, the following packages are required to be installed and accessible from the python environment:
* http_parser
* redfish
* redfish_utilities

To install the required packages, use either command:
`pip install <package name>`
`pip install -r requirements.txt`

To upgrade already installed packages, use the command:
`pip install --upgrade <package name>`

The target Redfish service(s) must also be configured to send Redfish events.

## Configuration

The following details will need to be entered in the config.ini file:

1. SSL Certificate Details if required; the tool comes with a default self signed certificate
2. Review and update the [SystemInformation] as required:
    * ListenerIP: the interface to listen on for event messages (typically 0.0.0.0)
    * ListenerPort: the port number to listen on for event messages
    * UseSSL: 'on' to use HTTPS (SSL), 'off' to use HTTP for incoming event messages
3. Subscription details if you require this tool to perform subscription, which consist of the following:
    * Subscription details of Destination, EventTypes, ContextDetail, Protocol, SubscriptionURI in config.ini file
    * Server information contains lists with IP, Username and password. Keep all these field as empty lists [] if subscription is taken care manually
4. If the service is subscribed manually, the context needs to be set same as mentioned in the config file (Public by default)

## Running the Tool

Execute using `python RedfishEventListener_v1.py`

Received event details will be captured on the console and recorded into a file named Events_<Service IP>.txt in the working directory.  Individual files will be generated for each subscribed service.

The tool can be stopped by issuing a keyboard interrupt (CTRL-C).

## Limitations

* The EventType and Context will remain same for all the subscriptions initiated from the tool
* The event counter will restart in the event file each time the tool is restarted
