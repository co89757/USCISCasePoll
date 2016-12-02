#!/bin/bash

SCRIPT_NAME='./poll_uscis.py'
# check pre-requisites
# availablity of commands

if [[ ! -e $SCRIPT_NAME ]]; then
	echo "script file ${SCRIPT_NAME} is not found in current directory"
	exit -1 
fi

if ! [[ (hash 'python') && (hash 'pip') ]] ; then
	echo "check your PATH, make sure python and pip are available"
	exit -1 
fi