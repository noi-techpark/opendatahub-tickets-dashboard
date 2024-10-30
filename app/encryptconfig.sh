#!/bin/bash

# SPDX-FileCopyrightText: NOI Techpark <digital@noi.bz.it>
#
# SPDX-License-Identifier: CC0-1.0

read -sp 'Password: ' password
gpg --batch -c -o- --passphrase "$password" config.yaml | base64 > config.yaml.enc