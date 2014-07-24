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

PKG_LIST=`cat dependencies.list`
echo $PKG_LIST

proxychains4 apt-get update

proxychains4 apt-get --print-uris --yes install ${PKG_LIST} | grep ^\' | cut -d\' -f2 > ${DOWNLOAD_FILE}
