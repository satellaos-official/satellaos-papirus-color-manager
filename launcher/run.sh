#!/bin/bash 

if ping -c 1 -W 3 8.8.8.8 &>/dev/null; then
    :
elif command -v network-warning &>/dev/null; then
    network-warning
    exit 0
else
    echo "Internet Connection not Found: Please check your network setting and try again"
    exit 1
fi

svn export https://github.com/satellaos-official/satellaos-papirus-color-manager/tree/main/core /tmp/core