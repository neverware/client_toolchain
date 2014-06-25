#!/bin/sh

if [ -z $1 ]
then
    PREFIX=/opt/neverware/virt_viewer
    echo No prefix provided
else
    PREFIX=$1
fi
echo Using prefix ${PREFIX}

BUILD_DIR=/build
mkdir ${BUILD_DIR}
cd ${BUILD_DIR}

apt-get --assume-yes --force-yes install git libspice-protocol-dev libtool

BRANCH=2.3RC
DEST=virt-viewer

if [ ! -d ${DEST} ]
then
    git clone https://github.com/neverware/virt-viewer -b ${BRANCH} ${DEST}
    cd ${DEST}
else
    cd ${DEST}
    git fetch
    git checkout ${BRANCH}
    git pull
fi

# We build libspice with gtk2.0
PKG_CONFIG_PATH=${PREFIX}/lib/pkgconfig ./autogen.sh --with-gtk=2.0 --prefix=${PREFIX}
make
make install
