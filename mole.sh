#!/bin/bash

BASEDIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
GIT="$( command -v git )"
PYTHON="$( command -v python3 )"

sleep 3
cd "$BASEDIR" || exit
$GIT checkout master > /dev/null
$GIT pull origin master > /dev/null

$PYTHON "$BASEDIR/mole.py"
