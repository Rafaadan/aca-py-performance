#!/bin/bash

PNAME="$1"
LOG_FILE="$2"

#Remplaza si ya existe el fichero

if [ -f "$LOG_FILE" ]; then
    echo "$(ps -p ${PNAME} -o %cpu,%mem | tail -1)" > $LOG_FILE
    sleep 1
fi

#Mide CPU y RAM cada segundo

while true ; do
    echo "$(ps -p ${PNAME} -o %cpu,%mem | tail -1)" >> $LOG_FILE
    sleep 1
done
