#!/usr/bin/env bash
__SELF="${0##*/}"
set -euxo pipefail
echo "$__SELF"

ARG_UUID=$(cat /proc/sys/kernel/random/uuid)
ARG_ISO_DATE="$(date --iso-8601)"
ARG_FILENAME=nothing_here_"$ARG_UUID".tar.gz
ARG_SOURCE=/var/log/audit/audit.log
ARG_HASH=$(sudo md5sum "$ARG_SOURCE")

utmpdump /var/run/utmp  > latest_utmp.log
utmpdump /var/log/wtmp > latest_wtmp.log

#needs sudo
utmpdump /var/log/btmp > latest_btmp.log
uptime > latest_uptime.log
uname -a > latest_unamea.log
ARG_HASH2=$(cat latest_utmp.log latest_wtmp.log latest_btmp.log latest_uptime.log latest_unamea.log | md5sum)
echo "$ARG_ISO_DATE $ARG_UUID $ARG_HASH $ARG_HASH2" > checksum.file

#neds sudo 
tar -czvf "$ARG_FILENAME" "$ARG_SOURCE" latest_utmp.log latest_wtmp.log latest_btmp.log latest_uptime.log latest_unamea.log checksum.file
time gpg --no-tty --always-trust --encrypt --recipient $3 "$ARG_FILENAME"
sftp -i /root/.ssh/nitor-audit -o StrictHostKeyChecking=accept-new $1@$2 <<EOF
put "$ARG_FILENAME".gpg
bye
EOF