VERSION := $(file <version)
URL := https://ftp.osuosl.org/pub/rpm/releases/rpm-4.18.x/rpm-$(VERSION).tar.bz2
SRC_FILE = $(notdir $(URL))
UNTRUSTED_SUFF := .UNTRUSTED
SHELL := /bin/bash

ifeq ($(FETCH_CMD),)
$(error "You can not run this Makefile without having FETCH_CMD defined")
endif

%: %.sha256
	@$(FETCH_CMD) $@$(UNTRUSTED_SUFF) $(URL)
	@sha256sum --status -c <(printf "$(file <$<)  -\n") <$@$(UNTRUSTED_SUFF) || \
		{ echo "Wrong SHA256 checksum on $@$(UNTRUSTED_SUFF)!"; exit 1; }
	@mv $@$(UNTRUSTED_SUFF) $@

.PHONY: get-sources
get-sources: $(SRC_FILE)

verify-sources:
	@true
