Name:		something
Version:	1.0
Release:	1%{?dist}
Summary:	Something wicked

Group:		Applications
License:	GPL-2+
URL:		https://www.debian.org/
Source0:	something-1.0.tar.gz

%description
This is a package that may help with something.
Or not.

%prep
%autosetup -n something-1.0

%build
make %{?_smp_mflags}

%install
make install DESTDIR=%{buildroot}

%files
%{_bindir}/something
%{_docdir}/something/README

%changelog
* Wed Nov 17 2021 Peter Pentchev <roam@ringlet.net> - 1.0-1
- Initial packaging; that's all there is.
