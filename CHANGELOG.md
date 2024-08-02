# Change Log

## [1.1.5] - 2024-08-02
- Fixed length check when reading data from incoming events

## [1.1.4] - 2024-06-28
- Updated embedded TLS certificate to no longer be expired
- Updated tool to no longer require 'http_parser' module that is no longer maintained

## [1.1.3] - 2023-02-24
- Modified the listener to respond with HTTP 204 in favor of HTTP 200 since no response body is sent

## [1.1.2] - 2022-06-02
- Corrected usage of 'lower' method for the authentication type

## [1.1.1] - 2022-04-08
- Added 'Connection: close' header to responses

## [1.1.0] - 2022-02-28
- Added IPv6 support
- Replaced internal HTTP calls with the 'redfish-utilities' module
- Added support for newer event subscription parameters, such as subscribing based on registries and resource types
- Added support for configuring the event format to receive

## [1.0.2] - 2019-03-26
- Added support for receiving Metric Reports

## [1.0.1] - 2018-03-30
- Added missing CRLF in the HTTP response
- Added option to control the use of HTTP or HTTPS
- Added option to specify the listening port

## [1.0.0] - 2017-10-25
- Initial Public Release
