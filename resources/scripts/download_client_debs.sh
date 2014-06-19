#!/bin/sh

if [ -z $1 ]
then
    echo I need a download file.  Please run \"get_client_deb_paths\" on a fresh juiceclient to produce a list of deb packages to download.
    exit 1
else
    DOWNLOAD_FILE=$1
fi

if [ -z $2 ]
then
    PREFIX=/opt/client_debs
    echo No prefix provided
else
    PREFIX=$2
fi
echo Using prefix ${PREFIX}

mkdir -p ${PREFIX}
cp ${DOWNLOAD_FILE} ${PREFIX}
cd ${PREFIX}

wget --input-file ${DOWNLOAD_FILE}
