#!/bin/bash

# This script is used to grab the two tarballs containing packages
# and dependencies required to build proxychains, and then install
# those packages. "proxy_dependencies" are pre-dependencies of all
# the packages in "proxy_debs".

pushd .
cd resources/packages
if [ ! -d proxy_depends ]; then
  mkdir proxy_depends
fi
if [ ! -d proxy_debs ]; then
  mkdir proxy_debs
fi

cd proxy_depends
if [ ! -e proxy_dependencies.tar.gz ]; then
  wget https://s3.amazonaws.com/Juicebox/AptServerFiles/proxy_dependencies.tar.gz
fi
tar -xf proxy_dependencies.tar
dpkg -i *.deb
cd ..

cd proxy_debs
if [ ! -e proxy_debs.tar.gz ]; then
  wget https://s3.amazonaws.com/Juicebox/AptServerFiles/proxy_debs.tar.gz
fi
tar -xf proxy_debs.tar
dpkg -i *.deb
cd ..

popd
