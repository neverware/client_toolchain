#!/bin/sh

apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 082CCEDF94558F59
apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 16126D3A3E5C1192
apt-get update
apt-get install --assume-yes --force-yes gcc locales dialog wget
locale-gen en_US.UTF-8
touch ~/.profile
echo "TZ='America/New_York'; export TZ" >> ~/.profile
toucl ~/.bashrc
echo "export LANG=C" >> ~/.bashrc
