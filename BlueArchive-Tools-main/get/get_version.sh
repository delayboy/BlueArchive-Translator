#!/bin/bash

server=$1
is_full_name=$2
target_version_key=$3
env_file="other/BA_${server}.env"

if [ -f "$env_file" ]; then
    export $(grep -v '^#' "$env_file" | xargs)
    if [ "$is_full_name" = "true" ]; then
        if [ "$server" = "CN" ]; then
            if [ -n "$target_version_key" ]; then
                version=${!target_version_key}
                echo "$server$GameVersion($version)"
            else
                echo "$server$GameVersion"
            fi
        else    
            version=$(echo "$AddressableCatalogUrl" | sed 's|.*/||')
            echo "$server$GameVersion($version)"
        fi
    else
        echo "$server$GameVersion"
    fi
else
    echo "Error: $env_file not found."
    exit 1
fi
