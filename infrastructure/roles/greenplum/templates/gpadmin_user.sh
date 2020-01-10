#!/bin/bash

set -euxo pipefail
setup_ssh_for_user() {
  local user="${1}"
  local home_dir
  home_dir=$(eval echo "~${user}")

  mkdir -p "${home_dir}"/.ssh
  touch "${home_dir}/.ssh/authorized_keys" "${home_dir}/.ssh/known_hosts" "${home_dir}/.ssh/config"
  ssh-keygen -t rsa -N "" -f "${home_dir}/.ssh/id_rsa"
  cat "${home_dir}/.ssh/id_rsa.pub" >> "${home_dir}/.ssh/authorized_keys"
  chmod 0600 "${home_dir}/.ssh/authorized_keys"
  cat << 'NOROAMING' >> "${home_dir}/.ssh/config"
Host *
  UseRoaming no
  StrictHostKeyChecking no
NOROAMING
  echo "       StrictHostKeyChecking no" >> "/etc/ssh/ssh_config"
  chown -R "${user}" "${home_dir}/.ssh"
  chmod 0400 "${home_dir}/.ssh/config"
}
ssh_keyscan_for_user() {
  local user="${1}"
  local home_dir
  home_dir=$(eval echo "~${user}")
  {
    ssh-keyscan localhost
    ssh-keyscan 0.0.0.0
    ssh-keyscan `hostname`
  } >> "${home_dir}/.ssh/known_hosts"
}
transfer_ownership() {
    [ -d /usr/local/greenplum* ] && chown -R gpadmin:gpadmin /usr/local/greenplum*
    [ -d /usr/local/greenplum* ] && chown -R gpadmin:gpadmin /usr/local/greenplum*
    chown -R gpadmin:gpadmin /home/gpadmin
}
set_limits() {
  if [ -d /etc/security/limits.d ]; then
    cat > /etc/security/limits.d/gpadmin-limits.conf <<-EOF
		gpadmin soft core unlimited
		gpadmin soft nproc 131072
		gpadmin soft nofile 65536
	EOF
  fi
   if [ -d /etc/systemd/logind.conf ]; then
    cat > /etc/systemd/logind.conf <<-EOF
		RemoveIPC=no
	EOF
  fi
  if [ -d  /etc ]; then
    cat >  /etc/sysctl.conf <<-EOF
		kernel.shmmax = 500000000
    kernel.shmmni = 4096
    kernel.shmall = 4000000000
    kernel.sem = 500 2048000 200 4096
    kernel.sysrq = 1
    kernel.core_uses_pid = 1
    kernel.msgmnb = 65536
    kernel.msgmax = 65536
    kernel.msgmni = 2048
    net.ipv4.tcp_syncookies = 1
    net.ipv4.conf.default.accept_source_route = 0
    net.ipv4.tcp_tw_recycle = 1
    net.ipv4.tcp_max_syn_backlog = 4096
    net.ipv4.conf.all.arp_filter = 1
    net.ipv4.ip_local_port_range = 1025 65535
    net.ipv4.ip_forward = 0
    net.core.netdev_max_backlog = 10000
    net.core.rmem_max = 2097152
    net.core.wmem_max = 2097152
    vm.overcommit_memory = 2
    vm.overcommit_ratio = 95
    vm.swappiness = 10
    vm.zone_reclaim_mode = 0
    vm.dirty_expire_centisecs = 500
    vm.dirty_writeback_centisecs = 100
    vm.dirty_background_ratio = 0 # See Note 5
    vm.dirty_ratio = 0
    vm.dirty_background_bytes = 1610612736
    vm.dirty_bytes = 4294967296
	EOF
  fi
  if [ -d /etc ]; then
    cat > /etc/security/limits.conf <<-EOF
		* soft nofile 65536
    * hard nofile 65536
    * soft nproc 131072
    * hard nproc 131072
	EOF
  fi
  su gpadmin -c 'ulimit -a'
}
setup_gpadmin_user() {
  groupadd supergroup
  case "$TEST_OS" in
    sles)
      groupadd gpadmin
      /usr/sbin/useradd -G gpadmin,supergroup,tty gpadmin
      ;;
    centos)
      /usr/sbin/useradd -G supergroup,tty gpadmin
      ;;
    ubuntu)
      /usr/sbin/useradd -G supergroup,tty gpadmin -s /bin/bash
      ;;
    *) echo "Unknown OS: $TEST_OS"; exit 1 ;;
  esac
  echo -e "password\npassword" | passwd gpadmin
  setup_ssh_for_user gpadmin
  transfer_ownership
  set_limits
}
setup_sshd() {
  if [ ! "$TEST_OS" = 'ubuntu' ]; then
    test -e /etc/ssh/ssh_host_key || ssh-keygen -f /etc/ssh/ssh_host_key -N '' -t rsa1
  fi
  test -e /etc/ssh/ssh_host_rsa_key || ssh-keygen -f /etc/ssh/ssh_host_rsa_key -N '' -t rsa
  test -e /etc/ssh/ssh_host_dsa_key || ssh-keygen -f /etc/ssh/ssh_host_dsa_key -N '' -t dsa
  sed -ri 's@^HostKey /etc/ssh/ssh_host_ecdsa_key$@#&@' /etc/ssh/sshd_config
  sed -ri 's@^HostKey /etc/ssh/ssh_host_ed25519_key$@#&@' /etc/ssh/sshd_config
  setup_ssh_for_user root
  if [ "$TEST_OS" = 'ubuntu' ]; then
    mkdir -p /var/run/sshd
    chmod 0755 /var/run/sshd
  fi
  /usr/sbin/sshd
  ssh_keyscan_for_user root
  ssh_keyscan_for_user gpadmin
}
determine_os() {
  if [ -f /etc/redhat-release ] ; then
    echo "centos"
    return
  fi
  if [ -f /etc/os-release ] && grep -q '^NAME=.*SLES' /etc/os-release ; then
    echo "sles"
    return
  fi
  if lsb_release -a | grep -q 'Ubuntu' ; then
    echo "ubuntu"
    return
  fi
  echo "Could not determine operating system type" >/dev/stderr
  exit 1
}

workaround_before_concourse_stops_stripping_suid_bits() {
  chmod u+s /bin/ping
}

_main() {
  TEST_OS=$(determine_os)
  setup_gpadmin_user
  setup_sshd
  workaround_before_concourse_stops_stripping_suid_bits
}
_main "$@"
