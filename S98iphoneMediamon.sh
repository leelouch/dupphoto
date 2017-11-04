#!/bin/sh
# /usr/syno/etc/rc.d/S99mediamon.sh

BD=BASE TOBEDEFINED
BIN=$BD/bin
VAR=$BD/var
PID=$VAR/run/iphoneMediaMon.pid
NAME=iphoneMediaMon.py
DAEMON=$BIN/$NAME

case "$1" in
  start|"")
    #start the monitoring daemon
	[ -r $PID ] && {
		read pid < $PID
		ps auxw | grep $NAME  | grep -q $pid && {
			echo "$NAME already running with pid=$pid"
		} || {
			rm $PID
		    /bin/python3 $DAEMON
		}
	} || {
		/bin/python3 $DAEMON
	}
    ;;
  restart|reload|force-reload)
    echo "Error: argument '$1' not supported" >&2
    exit 3
    ;;
  stop)
    kill `cat $PID`
    ;;
  *)
    echo "Usage: S98iphoneMediamon.sh [start|stop]" >&2
    exit 3
    ;;
esac
