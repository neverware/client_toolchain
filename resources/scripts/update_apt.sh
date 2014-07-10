#!/bin/sh

apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 082CCEDF94558F59
apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 16126D3A3E5C1192
apt-get update
apt-get install --assume-yes --force-yes gcc locales dialog wget

# We try to set up our locales correctly for apt
locale-gen en_US.UTF-8
HOMEDIR=/root
touch $HOMEDIR/.profile
echo "TZ='America/New_York'; export TZ" >> $HOMEDIR/.profile
touch $HOMEDIR/.bashrc
echo "export LANG=C" >> $HOMEDIR/.bashrc
