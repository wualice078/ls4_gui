# Oil pump images (interlock webpump)

Flask runs on **ls4-workstn**. Oil pump photos live on **interlock**
(`gpignata@192.168.50.200`) under `/home/gpignata/LS4/webpump/` as
`webpump_YYYYMMDD_HHMMSS.jpg`. Workstn cannot reach interlock directly, so
refresh hops: **workstn → nuc (`ls4@192.168.1.74`) → interlock**.

## One-time SSH key (observer → nuc)

On **observer@ls4-workstn**:

```tcsh
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_ls4snap -N ""
cat ~/.ssh/id_ed25519_ls4snap.pub | ssh ls4@192.168.1.74 "umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"
```

Test hop (should print a file path, no password):

```tcsh
ssh -i /home/observer/.ssh/id_ed25519_ls4snap -o BatchMode=yes ls4@192.168.1.74 "ssh -o BatchMode=yes gpignata@192.168.50.200 'ls -t /home/gpignata/LS4/webpump/webpump_*.jpg | head -1'"
```

Nuc → interlock must already be passwordless as `ls4` (it is, via existing
nuc keys for `gpignata`).

## `.env` on workstn (`~/ls4_gui/.env`)

```bash
LS4_OIL_PUMP_SYNC_ENABLED=true
LS4_OIL_PUMP_JUMP_HOST=ls4@192.168.1.74
LS4_OIL_PUMP_REMOTE_HOST=gpignata@192.168.50.200
LS4_OIL_PUMP_REMOTE_DIR=/home/gpignata/LS4/webpump
LS4_OIL_PUMP_REMOTE_GLOB=webpump_*.jpg
LS4_OIL_PUMP_SSH_KEY=/home/observer/.ssh/id_ed25519_ls4snap
LS4_OIL_PUMP_IMAGE_DIR=/home/observer/sim/webcams/oilpump_cache
```

Remove conflicting old oil-pump lines that pointed at nuc `snapshots` / `cam2`.

## Restart and check

```tcsh
cd ~/ls4_gui
git pull
# Ctrl+C old Flask, then:
./run.sh
```

In the GUI, click **Oil pump → Refresh**. Auto-refresh interval is
`LS4_WEBCAM_REFRESH_SECONDS` (default 30 seconds).

## Cache

`LS4_OIL_PUMP_IMAGE_DIR` is a **local copy** of the latest remote jpg so
Flask can serve a file from disk without holding an SSH connection open
while the browser loads the image.
