#!/usr/bin/env python

"""
Build script that attempts to build the requires debs for a juiceclient machine.
"""

import ConfigParser
import getpass
import hashlib
import os
import platform
import re
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time


class Builder(object):
    """
    Object that contains all the necessary functions to build the client debs

    NB: Currently, the client_toolchain repo only houses code to build:
        * virt-viewer
        * spice-gtk
    Its probably a good idea to roll juiceclient into here as well.
    """
    def __init__(self, prefix, version):
        # This will get the directory this file resides in
        self._prefix = prefix
        self._curdir = os.path.abspath(os.path.dirname(__file__))
        # The *_name is the relative name of the dir
        self._resources_dir_name = "resources"
        self._build_scripts_dir_name = "build_scripts"
        self._version = version

    @property
    def _client_deb_file(self):
        return os.path.join(self._curdir, "client_debs.tar.bz2")

    @property
    def _resources_dir(self):
        return os.path.join(self._curdir, self._resources_dir_name)

    @property
    def _build_scripts_dir(self):
        return os.path.join(self._curdir, self._build_scripts_dir_name)

    def generate_debootstrap_rpm(self):
        """
        Generates an .rpm file for the debootstrap package.
        If necessary, we grab the 'alien' binary, which is used to convert a .deb
        file to a .rpm file.
        """
        if "y" != raw_input("We keep these packages in {0}/rpms.  "
                            "You should install them.  Unless you lost them, then "
                            "feel free to run this command.  Type \"y\" to "
                            "continue:\n").format(self._resources_dir).lower()[0]:
            print("Exiting...")
            return
        if not self.can_apt_get():
            raise RuntimeError("Can only generate debootstrap rpm on debian systems")
        start_dir = os.path.abspath(os.path.curdir)
        build_dir = tempfile.mkdtemp()
        os.chdir(build_dir)
        get_deb = ["apt-get", "download", "debootstrap"]
        subprocess.check_call(get_deb)
        # There should only be one thing in this temp dir
        deb_pkg = os.listdir(build_dir)[0]   
        alien_pkg = "alien"
        try:
            check_alien = ["dpkg", "-s", alien_pkg]
            subprocess.check_call(check_alien)
        except subprocess.CalledProcessError as e:
            print("{0} is not detected, installing".format(alien_pkg))
            install_alien = ["apt-get", "install", alien_pkg]
            subprocess.check_call(install_alien)
        else:
            print("Alien detected, proceeding")
        produce_rpm = ["alien", "--to-rpm", deb_pkg]
        # This is some magic to get the newly created RPM file
        # I kind of hate how we do this, but alien doesn't expose an arg to specify
        # the output file :(
        deb_set = set(deb_pkg)
        new_files = set(os.listdir(build_dir))
        diff = new_files - deb_set
        if len(diff) != 1:
            raise RuntimeError("Something went wrong...there are too many files in {0}".format(build_dir))
        rpm = list(diff)[0]
        shutil.move(os.path.join(build_dir, rpm),
                    os.path.join(start_dir, rpm))
        print("Successfully converted {0} into {1}".format(deb_pkg, rpm))
        os.chdir(start_dir)
        return rpm

    def can_apt_get(self):
        try:
            subprocess.check_call(["which", "apt-get"])
        except subprocess.CalledProcessError as e:
            return False
        else:
            return True

    def make_chroot_jail(self, chroot_dir="chroot"):
        """
        Uses debootstrap to create a chroot jail.

        We also set the chroot jail up with all our resources/build scripts/etc
        to put it in a good state.
        """
        # First we check for debootstrap
        debootstrap = "debootstrap"
        try:
            subprocess.check_call(["which", debootstrap])
        except Exception as e:
            raise RuntimeError("{0} is required to make chroot jail".format(debootstrap))
        # Next we build the actual chroot jail
        arch = "i386"
        suite = "saucy"
        cmd = [debootstrap, 
               "--variant=buildd", 
               "--arch={0}".format(arch), 
               suite, 
               chroot_dir, 
               "http://archive.ubuntu.com/ubuntu/"]
        subprocess.check_call(cmd)
        # Now we copy over all the resources
        for dir in [self._resources_dir, self._build_scripts_dir]:
            basename = os.path.basename(dir)
            dest_dir = os.path.join(chroot_dir, basename)
            print("Copying {0} to {1}".format(dir, dest_dir))
            shutil.copytree(dir, dest_dir)
        # Now we update the sources
        sources_file = os.path.join("etc", "apt", "sources.list")
        self._concatenate_file(os.path.join(self._resources_dir, sources_file),
                               os.path.join(chroot_dir, sources_file))

        # the chroot's /sbin/run must be stubbed to avoid post-install logic
        # (such as dbus's) from breaking due to limits of chroot jail
        STARTFILE_PATH = "/root/client_toolchain/build_chroot/sbin/start"
        # largest empty file made via the method below will be 2: \n, EOF 
        if not os.path.exists(STARTFILE_PATH + ".bak"): 
            # then the original is in place and should be stubbed
            shutil.move(STARTFILE_PATH, STARTFILE_PATH + ".bak")
            with open(STARTFILE_PATH, "w") as f:
                f.write("\n")
            # make it executable
            cur_bits = os.stat(STARTFILE_PATH).st_mode
            os.chmod(STARTFILE_PATH, cur_bits | stat.S_IEXEC)

        # Now we apt-get update
        # This is from the root dir, since we'll execute it inside the chroot jail
        apt_update_script = os.path.join("/", self._resources_dir_name, "scripts", "update_apt.sh")
        subprocess.check_call(["chroot", chroot_dir, apt_update_script])

    def _concatenate_file(self, src, dst):
        """
        Concatenates the src file onto the dst file
        """
        with open(dst, 'a') as _dst:
            with open(src, 'r') as _src:
                for line in _src:
                    _dst.write(line)

    def get_chroot_name(self, prefix=None):
        chroot_name = ["chroot"]
        if isinstance(prefix, (str, bytes, unicode)):
            chroot_name.insert(0, prefix)
        return "_".join(chroot_name)

    def _make_chroot_if_necessary(self, chroot_dir):
        if not os.path.isdir(chroot_dir):
            print("Could not find {0}, making new chroot jail".format(chroot_dir))
            self.make_chroot_jail(chroot_dir)

    def build_spice_gtk(self, chroot_dir):
        """
        Creates a chroot jail (if it doesn't find one) and builds/packages up spice-gtk
        """
        self._make_chroot_if_necessary(chroot_dir)
        build_spice = os.path.join("/", self._build_scripts_dir_name, "build_spice_gtk_0.24.sh")
        cmd = ["chroot", chroot_dir, build_spice]
        if self._prefix != None:
            cmd.append(self._prefix)
        subprocess.check_call(cmd)

    def build_virt_viewer(self, chroot_dir):
        """
        Packages up the virt_viewer app
        """
        self._make_chroot_if_necessary(chroot_dir)
        build_virt_viewer = os.path.join("/", self._build_scripts_dir_name, "build_virt_viewer_0.6.0.sh")
        cmd = ["chroot", chroot_dir, build_virt_viewer]
        if self._prefix != None:
            cmd.append(self._prefix)
        subprocess.check_call(cmd)

    def _calc_sha1(self, path):
        """
        Reads a file one chunk at a time, until we have a checksum for the entire file
        """
        print("Calculating checksum.  This could take a while")
        sum = hashlib.sha1()
        size = 2**20
        with open(path) as f:
            data = f.read(size)
            while data != "":
                sum.update(data)
                data = f.read(size)
        return sum.hexdigest()

    def _download_client_deb_tarball(self, 
                                     url="https://s3.amazonaws.com/Juicebox/"
                                         "AptServerFiles/client_debs.tar.bz2"):
        download_cmd = ["wget", "-O", self._client_deb_file, url]
        subprocess.check_call(download_cmd)

    def build_client_debs(self, chroot_dir):
        client_deb = "client_deb"
        client_deb_tarball = "{0}.tar.bz2".format(client_deb)
        config_parser = ConfigParser.ConfigParser()
        checksum_cfg = "checksums.cfg"
        with open(checksum_cfg) as f:
            config_parser.readfp(f)
        def update_checksum():
            new_checksum = self._calc_sha1(self._client_deb_file)
            config_parser.set("checksums", client_deb, new_checksum)
            with open(checksum_cfg, 'w') as f:
                config_parser.write(f)
        if not os.path.exists(self._client_deb_file):
            self._download_client_deb_tarball()
            update_checksum()
        else:
            got_checksum = self._calc_sha1(self._client_deb_file)
            expected_checksum = config_parser.get("checksums", client_deb)
            if got_checksum != expected_checksum:
                print("Checksums {0} (expected) and {1} (got) don't match, downloading {2}".format(
                      expected_checksum, got_checksum, client_deb_tarball))
                self._download_client_deb_tarball()
                update_checksum()
        chroot_deb_dir = os.path.join("/",
                                      "chroot", 
                                      "precise", 
                                      "www", 
                                      "dists", 
                                      "precise", 
                                      "neverware", 
                                      "binary-i386")
        print("Extracting all tarfiles")
        with tarfile.open(self._client_deb_file, "r:*") as f:
            f.extractall(path=chroot_deb_dir)
        

    def package_client_debs(self, chroot_dir):
        self._make_chroot_if_necessary(chroot_dir)
        prefix = os.path.join(chroot_dir, "opt", "client_debs")
        get_debs = os.path.join("/", self._resources_dir_name, "scripts", "download_client_debs.sh")
        download_list = os.path.join("/", self._resources_dir_name, "downloads.list")
        cmd = ["chroot", chroot_dir, get_debs, download_list]
        if self._prefix != None:
            cmd.append(self._prefix)
        try:
            raise subprocess.CalledProcessError('a', 'b')
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as e:
            print("Failed to wget all packages, tarring up what we can")
        cur_dir = os.path.abspath(os.curdir)
        os.chdir(prefix)
        archive_name = "client_debs.tar.bz2"
        deb_ext = ".deb"
        with tarfile.open(archive_name, "w:bz2") as f:
            for file in os.listdir("."):
                if file.endswith(deb_ext):
                    f.add(file)
        print("Packaged all client debs to: {0}".format(os.path.join(prefix, archive_name)))
        os.chdir(cur_dir)

    def _copy_debs(self, chroot_dir):
        deb_dir = os.path.join(chroot_dir, "opt", "client_debs")
        for deb in os.listdir(deb_dir):
            (name, ext) = os.path.splitext(deb)
            if ext == ".deb":
                shutil.copy(os.path.join(deb_dir, deb), chroot_deb_dir)

    def build_neverware_virt_viewer_deb(self, chroot_dir):
        version = self._version
        apt_name = "neverware-virt-viewer"
        prev_dir = os.path.abspath(os.curdir)
        os.chdir(os.path.join(self._curdir, "apt_configs", apt_name.replace("-", "_")))
        temp_dir = tempfile.mkdtemp()
        build_dir_name = "{0}-{1}".format(apt_name, version)
        build_dir = os.path.join(temp_dir, build_dir_name)
        os.mkdir(build_dir)
        print("Building deb file at {0}".format(build_dir))
        debian_dir_name = "DEBIAN"
        debian_dir = os.path.join(build_dir, debian_dir_name)
        os.mkdir(debian_dir)
        with open(os.path.join(self._resources_dir, "scripts", "dependencies.list")) as f:
            dependencies = f.read()
        dependencies = dependencies.replace(" ", ", ").rstrip()
        with open(os.path.join(debian_dir, "control"), 'w') as f:
            f.write("Package: {0}\n".format("neverware-virt-viewer"))
            f.write("Version: {0}\n".format(version))
            f.write("Section: base\n")
            f.write("Priority: optional\n")
            f.write("Architecture: i386\n")
            f.write("Depends: {0}\n".format(dependencies))
            f.write("Maintainer: neverware <it@neverware.com>\n")
            f.write("Description: Neverare's flavor of virt-viewer.\n")
        # This will copy files like postint, prerm, etc
        for file in os.listdir(os.curdir):
            shutil.copy2(file, debian_dir)
        executables = ["postinst", "postrm", "preinst", "prerm"]
        permission_bits = 0775
        for exe in executables:
            path = os.path.join(debian_dir, exe)
            if os.path.exists(path):
                os.chmod(path, permission_bits)

        # We do this crazy tar copy so we dont need to deal with the annoyingness of 
        # copying files/dir/parent dirs.
        compression = "bz2"
        with tempfile.NamedTemporaryFile(suffix=".tar.{0}".format(compression)) as f:
            arc_name = f.name
        os.chdir(os.path.join(self._curdir, chroot_dir))
        with tarfile.open(arc_name, "w:{0}".format(compression)) as f:
            # TODO: We allow our build scripts to implement their own prefix, but we assume its
            # at a specific dir.  This is bad, and we should change it.
            f.add(os.path.join("opt", "neverware"))
        with tarfile.open(arc_name, "r:{0}".format(compression)) as f:
            f.extractall(build_dir)
        os.unlink(arc_name)

        # Now we bundle up the deb build directory
        os.chdir(os.path.join(build_dir, os.pardir))
        built_tar = "{0}.tar.{1}".format(build_dir_name, compression)
        with tarfile.open(built_tar, "w:{0}".format(compression)) as f:
            f.add(os.path.basename(build_dir))

        precise_chroot = os.path.join("/", "chroot", "precise")
        tar_dst = os.path.join(precise_chroot, "www", os.path.basename(built_tar))
        print("Moving {0} to {1}".format(built_tar, tar_dst))
        shutil.move(built_tar, tar_dst)
        cmd = ["chroot",
               precise_chroot,
               "./neverware_deb_packager.py",
               "--tar-name",
               os.path.basename(built_tar),
              ]
        subprocess.check_call(cmd)
 

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser("Script that attempts to create a chroot "
                                     "jail that can build the various client "
                                     "debs required to run a neverware client.")
    parser.add_argument(
        "--generate-debootstrap-rpm",
        action="store_true",
        dest="generate_debootstrap_rpm",
        help="Generate the debootstrap RPM to install on redhat machines")
    parser.add_argument(
        "--make-chroot-jail",
        action="store_true",
        dest="make_chroot_jail",
        help="Creates a chroot jail, similar to the one we use to compile the client toolchain.")
    parser.add_argument(
        "--build-prefix",
        action="store",
        type=str,
        default=None,
        dest="build_prefix",
        help="The prefix the different components will be installed to.")
    parser.add_argument(
        "--package-client-debs",
        action="store_true",
        dest="package_client_debs",
        help="Grab all the required debs from external sources and wrap them up in a tarball")
    parser.add_argument(
        "--build-all",
        action="store_true",
        dest="build_all",
        help="Build all required components")
    parser.add_argument(
        "--deb-version",
        action="store",
        type=str,
        default="v0.0.1",
        dest="deb_version",
        help="The version of the deb we are going to produce")
    # We machine generate all of these params
    components = ["spice_gtk", "virt_viewer", "client_debs", "neverware_virt_viewer_deb"]
    options = {}
    for component in components:
        parser.add_argument(
            "--{0}".format(component.replace("_", "-")),
            action="store_true",
            dest=component,
            help="Package {0}".format(component))
        # Initialize the options field
        options[component] = False
    args = parser.parse_args()
    root_user = "root"

    # Builder object holds all functions to build with
    version_regex = "v(\d*)\.(\d*).(\d*)"
    match = re.match(version_regex, args.deb_version)
    if match == None:
        raise AttributeError("Bad version number {0}".format(args.deb_version))
    else:
        version = "{0}.{1}-{2}".format(match.group(1), match.group(2), match.group(3))
    builder = Builder(args.build_prefix, version)
    chroot_dir = builder.get_chroot_name("build")
    if getpass.getuser() != root_user:
        print("Sorry, this script needs to be run as root :(")
        sys.exit(1)

    if getattr(args, "generate_debootstrap_rpm", False):
        print("Generateing debootstrap rpm")
        builder.generate_debootstrap_rpm()

    if getattr(args, "make_chroot_jail", False):
        builder.make_chroot_jail()

    if getattr(args, "package_client_debs", False):
        builder.package_client_debs(chroot_dir)

    if getattr(args, "build_all", False):
        for key in options:
            options[key] = True
    else:
        for component in components:
            if getattr(args, component, False):
                options[component] = True
    for component in components:
        if options[component]:
            print("Executing {0}".format(component))
            func = getattr(builder, "build_{0}".format(component))
            func(chroot_dir)
