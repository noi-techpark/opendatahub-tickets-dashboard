#!/bin/bash
read -sp 'Password: ' password
gpg --batch -c -o- --passphrase "$password" config.yaml | base64 > config.yaml.enc