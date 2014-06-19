#!/bin/sh

if [ -z $1 ]
then
    PREFIX=/opt/neverware
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

git clone https://github.com/neverware/virt-viewer -b ${BRANCH} ${DEST}

cd ${DEST}

git fetch

# We build libspice with gtk2.0
PKG_CONFIG_PATH=${PREFIX}/lib/pkgconfig ./autogen.sh --with-gtk=2.0 --prefix=${PREFIX}
make
make install
