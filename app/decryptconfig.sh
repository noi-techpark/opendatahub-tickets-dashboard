#!/bin/bash

# SPDX-FileCopyrightText: NOI Techpark <digital@noi.bz.it>
#
# SPDX-License-Identifier: CC0-1.0

read -sp 'Password: ' password
echo

base64 -d config.yaml.enc | gpg --batch -d --passphrase "$password" -o config.yaml
