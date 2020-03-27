# Build with debug info rpm
%global with_debug 0
# Run unit tests
%global with_tests 0

%if 0%{?with_debug}
%global _dwz_low_mem_die_limit 0
%else
%global debug_package   %{nil}
%endif

# Those can be overridden when invoking make, eg: `make VERSION=2.0.0 rpm`
%global package_version 0.0.1
%global package_release 1

%global provider        github
%global provider_tld    com
%global project         istio
%global repo            istio
# https://github.com/istio/istio
%global provider_prefix %{provider}.%{provider_tld}/%{project}/%{repo}
%global import_path     github.com/istio/istio

# Use /usr/local as base dir, once upstream heavily depends on that
%global _prefix /usr/local

Name:           istio-sidecar
Version:        %{package_version}
Release:        %{package_release}%{?dist}
Summary:        An open platform to connect, manage, and secure microservices
License:        ASL 2.0
URL:            https://%{provider_prefix}

Source0:        istio.tar.gz
Source1:        istio-start.sh
Source2:        istio.service

# e.g. el6 has ppc64 arch without gcc-go, so EA tag is required
ExclusiveArch:  %{?go_arches:%{go_arches}}%{!?go_arches:%{ix86} x86_64 aarch64 %{arm}}

%description
Istio is an open platform that provides a uniform way to connect, manage
and secure microservices. Istio supports managing traffic flows between
microservices, enforcing access policies, and aggregating telemetry data,
all without requiring changes to the microservice code.

%prep

rm -rf ISTIO
mkdir -p ISTIO/src/github.com/istio/istio
tar zxf %{SOURCE0} -C ISTIO/src/github.com/istio/istio --strip=1

%build
cd ISTIO
export GOPATH=$(pwd)

pushd src/github.com/istio/istio
go build -o out/linux_amd64/generate_cert security/tools/generate_cert/main.go
make  pilot-agent istioctl node_agent istio-iptables istio-clean-iptables

popd

%install
rm -rf $RPM_BUILD_ROOT
install -d -m755 $RPM_BUILD_ROOT/%{_bindir}
install -d -m755 $RPM_BUILD_ROOT/%{_unitdir}
install -m755 %{SOURCE1} $RPM_BUILD_ROOT/%{_bindir}/istio-start.sh
install -m644 %{SOURCE2} $RPM_BUILD_ROOT/%{_unitdir}/istio.service

binaries=(envoy generate_cert pilot-agent istioctl istio_ca node_agent istio-iptables istio-clean-iptables)
pushd .
cd ISTIO/src/github.com/istio/istio/out/linux_amd64

%if 0%{?with_debug}
    for i in "${binaries[@]}"; do
        cp -pav $i $RPM_BUILD_ROOT%{_bindir}/
%else
    mkdir stripped
    for i in "${binaries[@]}"; do
        echo stripping: $i
        strip -o stripped/$i -s $i
        cp -pav stripped/$i $RPM_BUILD_ROOT%{_bindir}/
    done
%endif
popd

%if 0%{?with_tests}

%check
cd ISTIO
export GOPATH=$(pwd):%{gopath}
pushd src/github.com/istio/istio
make test
popd

%endif

%pre
getent group istio-proxy >/dev/null || groupadd --system istio-proxy || :
getent passwd istio-proxy >/dev/null || \
  useradd -c "Istio Proxy User" --system -g istio-proxy \
  -s /sbin/nologin -d /var/lib/istio istio-proxy 2> /dev/null || :

mkdir -p /var/lib/istio/{envoy,proxy,config} /var/log/istio /etc/certs
touch /var/lib/istio/config/mesh
chown -R istio-proxy.istio-proxy /var/lib/istio/ /var/log/istio /etc/certs

ln -s -T /var/lib/istio /etc/istio 2> /dev/null || :

%post
%systemd_post istio.service

%preun
%systemd_preun istio.service

%postun
%systemd_postun_with_restart istio.service

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%files
%license ISTIO/src/github.com/istio/istio/LICENSE
%attr(2755,root,root) %{_bindir}/envoy
%attr(2755,root,root) %{_bindir}/generate_cert
%attr(2755,root,root) %{_bindir}/pilot-agent
%attr(0755,root,root) %{_bindir}/istio-iptables
%attr(0755,root,root) %{_bindir}/istio-clean-iptables
%attr(0755,root,root) %{_bindir}/istioctl
%attr(0755,root,root) %{_bindir}/istio_ca
%attr(0755,root,root) %{_bindir}/node_agent
%attr(0755,root,root) %{_bindir}/istio-start.sh
%attr(0644,root,root) %{_unitdir}/istio.service
%doc     ISTIO/src/github.com/istio/istio/README.md

%changelog
* Tue Nov 19 2019 Idan Zach <zachidan@gmail.com>
- Upgrade istio version
* Thu Feb 7 2019 Jonh Wendell <jonh.wendell@redhat.com> - 1.1.0-1
- First package
