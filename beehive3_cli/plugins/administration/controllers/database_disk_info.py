# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte
from ujson import loads
from beehive3_cli.core.connect import SshConnectionManager


class DbVolumeInfo:
    scm = None
    node = None
    cmd = """\
#!/bin/bash

QUOTE='"'

# Get LVM Physical Volumes info: PV name, VG name
pvs_output=$(pvs --noheadings -o pv_name,vg_name 2>/dev/null)

# Accumulators for backup and data total sizes
backup_total=0
data_total=0


is_valid_partition() {
  local devname="$1"
  local syslink="/sys/class/block/$devname"

  # Il link simbolico deve esistere
  [[ -L "$syslink" ]] || return 1

  local target
  target=$(readlink -f "$syslink")

  # Deve essere una vera partizione (non il device padre, non loop, non ram)
  [[ "$target" =~ /block/.+/.+ ]] && [[ "$target" != */block/$devname ]]
}


partitions_json() {
  local part_json_output="{"
  local first_entry=true

  while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]*[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+.+$ ]]; then
      read -r major minor blocks name <<< "$line"

      if is_valid_partition "$name"; then
        size_bytes=$((blocks * 1024))

        if ! "$first_entry"; then
          part_json_output="$part_json_output,"
        fi
        part_json_output="$part_json_output${QUOTE}/dev/$name${QUOTE}:$size_bytes"
        first_entry=false
      fi
    fi
  done < /proc/partitions

  echo "$part_json_output}"
}


volumes_json() {
  local vol_json_output="{"
  local first_entry=true

  for device_path in /sys/block/*; do
    device=$(basename "$device_path")
    if [[ ! -e "$device_path/partition" && "$device" ]]; then
      if [[ -e "$device_path/size" ]]; then
        sectors=$(cat "$device_path/size" 2>/dev/null)
        if [ -n "$sectors" ]; then
          size_bytes=$((sectors * 512))
          if ! "$first_entry"; then
            vol_json_output="$vol_json_output,"
          fi
          vol_json_output="$vol_json_output${QUOTE}/dev/$device${QUOTE}:$size_bytes"
          first_entry=false
        fi
      fi
    fi
  done
  echo "$vol_json_output}"
}


lvm_json() {
  local lvm_output="{"
  local first_vg=true

  # Mappa VG → lista di PV (slaves)
  declare -A vg_pvs
  while IFS= read -r line; do
    local pv vg
    read -r pv vg <<< "$line"
    if [[ -n "$vg" ]]; then
      vg_pvs["$vg"]+="${vg_pvs[$vg]:+,}${QUOTE}${pv}${QUOTE}"
    fi
  done <<< "$(pvs --noheadings -o pv_name,vg_name 2>/dev/null)"

  # Mappa VG → dict con /dev/dm-* come chiavi
  declare -A vg_blocks

  while IFS= read -r line; do
    local lv_path vg
    read -r lv_path vg <<< "$line"
    local dm_path=$(readlink -f "$lv_path")
    local lv_name=$(basename "$lv_path")

    # Ricava gli slaves specifici per questo device
    local dm_base=$(basename "$dm_path")
    local slaves_raw=""
    while IFS= read -r slave; do
      slaves_raw+="${slaves_raw:+,}${QUOTE}/dev/${slave}${QUOTE}"
    done < <(ls -1 /sys/block/"$dm_base"/slaves 2>/dev/null)

    # Entry completa
    local entry="${QUOTE}${dm_path}${QUOTE}:{${QUOTE}lv${QUOTE}:${QUOTE}${lv_name}${QUOTE},${QUOTE}slaves${QUOTE}:[${slaves_raw}]}"

    if [[ -z "${vg_blocks[$vg]}" ]]; then
      vg_blocks[$vg]="$entry"
    else
      vg_blocks[$vg]+=",$entry"
    fi
  done <<< "$(lvs --noheadings -o lv_path,vg_name 2>/dev/null)"

  for vg in "${!vg_blocks[@]}"; do
    if ! $first_vg; then
      lvm_output+=","
    else
      first_vg=false
    fi
    lvm_output+="${QUOTE}${vg}${QUOTE}:{${vg_blocks[$vg]}}"
  done

  lvm_output+="}"
  echo "$lvm_output"
}


is_valid_block_device() {
  local dev="$1"
  [[ -b "$dev" ]]
}


mount_points_json() {
  local mount_points_output='{'
  local first_entry=true

  while IFS= read -r line; do
    device=$(echo "$line" | awk '{print $1}')
    mount_point=$(echo "$line" | awk '{print $3}')

    [[ "$device" =~ ^/dev/ ]] || continue

    # Resolve to actual device
    real_device=$(readlink -f "$device" 2>/dev/null || echo "$device")

    # Check if it's a real block device
    if is_valid_block_device "$real_device"; then
      if [ "$first_entry" = true ]; then
        first_entry=false
      else
        mount_points_output+=","
      fi

      mount_points_output+="${QUOTE}${real_device}${QUOTE}:${QUOTE}${mount_point}${QUOTE}"
    fi
  done <<< "$(mount 2>/dev/null)"

  mount_points_output+='}'
  echo "$mount_points_output"
}


# Output in JSON format
echo -n "{"\
"${QUOTE}lvm${QUOTE}: $(lvm_json),"\
"${QUOTE}volumes${QUOTE}: $(volumes_json),"\
"${QUOTE}partitions${QUOTE}: $(partitions_json),"\
"${QUOTE}mount_points${QUOTE}: $(mount_points_json)"\
"}"
"""

    def __init__(self, scm: 'SshConnectionManager', node):
        self.scm: 'SshConnectionManager' = scm
        self.node = node

    def get_disk_info(self):
        res = self.scm.sshcmd2node(node=self.node, cmd=self.cmd)
        stdout = res["stdout"][0]
        disk_d = loads(stdout)
        return disk_d
