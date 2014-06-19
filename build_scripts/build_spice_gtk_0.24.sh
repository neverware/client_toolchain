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

mkdir -p ${PREFIX}
mkdir ${BUILD_DIR}
cd ${BUILD_DIR}

SPICE_GTK=spice-gtk-0.24
TAR_EXT=.tar.bz2
EXPECT_FILE=${SPICE_GTK}${TAR_EXT}
PACKAGE_DIR=/resources/packages/

if [ -e ${PACKAGE_DIR}${EXPECT_FILE} ]
then
    echo ${EXPECT_FILE} exists, using that
    mv ${PACKAGE_DIR}${EXPECT_FILE} ${BUILD_DIR}
else
    echo No spice-gtk specified, getting from remote
    URL=http://www.spice-space.org/download/gtk/
    wget -O ${BUILD_DIR} ${URL}${SPICE_GTK}${TAR_EXT}
fi

# Compile spice gtk
tar -xf ${BIULD_DIR}${EXPECT_FILE}
cd ${SPICE_GTK}

# Get all dependencies
apt-get install --assume-yes --force-yes pkg-config libspice-client-gtk-2.0-dev intltool libpixman-1-dev libssl-dev libgtk2.0-dev libsoup2.4-dev pulseaudio libpulse-dev libjpeg-dev libusb-1.0-0-dev libusbredirhost-dev

# x11 and gtk2.0 are supposed to give some performance boosts
./configure --enable-usbredir --with-x11 --with-gtk=2.0 --prefix=${PREFIX}
make
make install
