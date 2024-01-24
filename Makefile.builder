NO_ARCHIVE := 1

DEBIAN_BUILD_DIRS.bookworm := debian-pkg/debian
DEBIAN_BUILD_DIRS.trixie := debian-pkg/debian
DEBIAN_BUILD_DIRS := $(DEBIAN_BUILD_DIRS.$(DIST))

SOURCE_COPY_IN.debian := source-debian-copy-in
SOURCE_COPY_IN.qubuntu := source-debian-copy-in
SOURCE_COPY_IN := $(SOURCE_COPY_IN.$(DISTRIBUTION))

source-debian-copy-in: VERSION = $(file <$(ORIG_SRC)/version)
source-debian-copy-in: ORIG_FILE = $(CHROOT_DIR)/$(DIST_SRC)/rpm_$(VERSION)+dfsg.orig.tar.bz2
source-debian-copy-in: SRC_FILE  = $(ORIG_SRC)/rpm-$(VERSION).tar.bz2
source-debian-copy-in:
	cp -p $(SRC_FILE) $(ORIG_FILE)
	tar xjf $(SRC_FILE) -C $(CHROOT_DIR)/$(DIST_SRC)/debian-pkg --strip-components=1
