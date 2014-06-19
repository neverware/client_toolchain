#!/bin/sh

# This script is meant to be run on a fresh client so we can determine what 3rd party
# ".deb" packages we need to host.  The juiceclient will then pull those packages down
# when it goes through its install phase.  This is done because we don't want to rely
# on internet connectivity during install time; just juicebox connectivity

if [ -z $1 ]
then
    DOWNLOAD_FILE=downloads.list
    echo No download dest provided
else
    DOWNLOAD_FILE=$1
fi
echo Using dest file${DOWNLOAD_FILE}

PKG_LIST="libspice-protocol-dev libspice-client-gtk-2.0-dev libpixman-1-dev libssl-dev libgtk2.0-dev libsoup2.4-dev pulseaudio libpulse-dev libjpeg-dev libusb-1.0-0-dev libusbredirhost-dev sl"

apt-get update

apt-get --print-uris --yes install ${PKG_LIST} | grep ^\' | cut -d\' -f2 > ${DOWNLOAD_FILE}
