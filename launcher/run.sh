#!/bin/bash 

# - Variables - 

name=papirus-color-manager
location=/tmp
script_url=https://raw.githubusercontent.com/satellaos-official/satellaos-papirus-color-manager/main/core/script.py
archive_url=https://raw.githubusercontent.com/satellaos-official/satellaos-papirus-color-manager/main/archive/icons.tar.gz

# - Checking The Internet Connection -

if ping -c 1 -W 3 8.8.8.8 &>/dev/null; then
    :
elif command -v network-warning &>/dev/null; then
    network-warning
    exit 0
else
    echo "Internet Connection not Found: Please check your network setting and try again"
    exit 1
fi

# - Creating The File Location -

mkdir -p "$location/$name"

# - Downloading The Files -

wget -O "$location/$name/script.py" "$script_url"
wget -O "$location/archive.tar.gz" "$archive_url"

# - Extracting The Archive -

tar -xf "$location/archive.tar.gz" -C "$location/$name"

# - Running The Script -

python3 "$location/$name/script.py"

# - Cleaning The Temporary Files -

rm -rf "$location/archive.tar.gz" 
rm -rf "$location/$name"