<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Privacy

The suite's initial Bazzite Test app reads local system details. It does not send them over the network.

Xbox Remote Play uses Microsoft's device-code sign-in and sends authentication and streaming requests to Microsoft
and Xbox services. It keeps the account's refresh token and app settings locally under
`~/.config/ps5-xbox-remoteplay`; it does not send them to a Bazzite Console service. The app masks tokens and
network addresses in its logs.
