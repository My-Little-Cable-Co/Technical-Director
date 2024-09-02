# MyLittleCableCo/Technical-Director

The technical director is responsible for queueing and playing videos. It
consults the [Scheduler](https://github.com/My-Little-Cable-Co/Scheduler) to
know what should be playing, and intersperses commercials to fill the
timeslot.

This project is a python program that uses python-vlc bindings to control a VLC
instance.

## Setting up on a Raspberry Pi

These are the steps I take when installing Technical Director on a Raspberry
Pi 3B+.

1. Using the [Raspberry Pi Imager program](https://github.com/raspberrypi/rpi-imager), image your Micro SD card with Raspberry Pi OS Lite (64-bit).
    * Before writing, I preset the hostname, wifi credentials, and add my computer's SSH key to make the on-device configuration much easier.
    * NOTE: These scripts assume the user is named `mlcc` and the hostname is `mlcc-00`, replacing "00" with your choice of channel number.
2. Insert the freshly imaged Micro SD card and power on the Raspberry Pi
    * The Pi does some firstboot stuff, and may restart once or twice before your configuration can begin.
3. SSH to the device, update all installed packages, and install the packages we'll need to run Technical Director
    * ```bash
      # update packages
      sudo apt-get update && sudo apt-get upgrade

      # install desktop environment and a few programs
      sudo apt install xserver-xorg raspberrypi-ui-mods vlc unclutter vim git python3-poetry ffmpeg
      ```
4. Install log2ram. I am including this as a separate step as the instructions for installing it may change.
    * ```bash
      # install log2ram
      echo "deb [signed-by=/usr/share/keyrings/azlux-archive-keyring.gpg] http://packages.azlux.fr/debian/ bookworm main" | sudo tee /etc/apt/sources.list.d/azlux.list
      sudo wget -O /usr/share/keyrings/azlux-archive-keyring.gpg https://azlux.fr/repo.gpg
      sudo apt update
      sudo apt install log2ram
      ```
5. Pre-create the video that will play if there is no listing information available. Note: Technical director will auto-generate this on demand, but I like to pre-create it since it's hard to tell if something's wrong when it generates it on the fly. (You just see a black screen while it creates it before it can play it)
    * ```bash
      # create a 30 minute default video file
      echo "Creating a 1 minute default video file"
      time ffmpeg -f lavfi -i smptebars=size=640x480,drawtext=text='MyLittleCableCo':font='mono|bold':fontcolor=white:fontsize=42:box=1:boxcolor=black@0.5:boxborderw=5:x="(w-text_w)/2:y=(h-text_h)/2" -t 60 default_video_1m.mp4
      echo "Looping the 1 minute video to create a 30 minute default video file"
      ffmpeg -stream_loop -1 -i default_video_1m.mp4 -c copy -t 1800 output30.mp4
      echo "Removing 1 minute video and moving the 30 minute video to the expected location."
      rm default_video_1m.mp4
      mkdir -p ~/.mylittlecableco/technical_director/
      mv output30.mp4 ~/.mylittlecableco/technical_director/smpte.mp4
      echo "Done!"
      ```
6. Edit `/etc/fstab` with any network mounts you need so Technical Director can access your videos.
    * This part is very specific to your own network configuration. I have a Synology NAS with all my videos on it, and I created a separate user with read-only access to those directories. I will provide my (credential redacted) fstab lines here for inspiration, but one size does not fit all here.
    * ```
      //nas.local/Media/TV\040Shows                    /media/tv           cifs username=mylittlecableco,password=REDACTED-PASSWORD,x-systemd.automount,x-systemd.requires=network-online.target 0
      //nas.local/Media/Videos/Commercials/Individual  /media/commercials  cifs username=mylittlecableco,password=REDACTED-PASSWORD,x-systemd.automount,x-systemd.requires=network-online.target 0
      //nas.local/Media/Movies                         /media/movies       cifs username=mylittlecableco,password=REDACTED-PASSWORD,x-systemd.automount,x-systemd.requires=network-online.target 0
      ```
7. Use `sudo raspi-config` to set the pi to autologin to the desktop environment and enable the composite output
    * `raspi-config` will ask if you want to reboot, you do!
8. The Raspberry Pi should boot into the desktop environment. I make a few visual customizations here in case the desktop shows up on a broadcast:
    * Set the desktop background to a solid black color
    * Hide the wastebasket and network share icons from the desktop
    * Make the task bar small, and change its color to black
9. Make a startup script to run Technical Director on boot
    * Here's the script I use, I name this file `launch-technical-director.sh`:
    * ```bash
      #! /bin/bash

      set -e

      # Ensure the repo has been cloned
      if [ ! -d /home/mlcc/src/Technical-Director ]; then
              mkdir -p /home/mlcc/src/
              cd /home/mlcc/src/
              git clone https://github.com/My-Little-Cable-Co/Technical-Director.git
      fi

      # cd to the repo directory
      cd /home/mlcc/src/Technical-Director

      # Pull the latest version of the code, discarding any local changes.
      git fetch --all
      git reset --hard origin/main

      poetry install
      DISPLAY=:0 SCHEDULER_URL=http://mlcc-03.local:3000 poetry run python technical_director/technical_director.py &> /home/mlcc/technical_director.log &
      ```
    * Make sure that script is executable, and note that you will need to change the SCHEDULER_URL in the last line to point to your running [Scheduler](https://github.com/My-Little-Cable-Co/Scheduler) server.
    * Make an LXDE autostart script to call `launch-technical-director.sh`. (This also configures unclutter to hide the mouse cursor at boot)
    * ```bash
      echo -e "@lxpanel --profile LXDE-pi\n@pcmanfm --desktop --profile LXDE-pi\n@unclutter -idle 0\n@bash /home/mlcc/launch-technical-director.sh\n@xscreensaver -no-splash" > ~/.config/lxsession/LXDE-pi/autostart
      chmod 771 ~/.config/lxsession/LXDE-pi/autostart 
      ```
10. Run `launch-technical-director.sh` (The first time requires some manual intervention)
      * It should create a directory, clone the git repo, and run `poetry install`. In my experience, `poetry install` hangs because of a request being made to the system keychain. On the display showing the desktop, a window appears asking you to password protect the keychain. I leave it blank, and just press "enter" twice (the second time confirms "yes, leave it blank"). After this, the poetry install is hung. Abort with ctrl-c and try it again (by invoking `launch-technical-director.sh`). It should succeed this time with installing the python dependencies for Technical Director.
      * You'll know it worked when you see the SMPTE color bars (May take some time). When you see those, you are good to go! Feel free to power off, when you power it back on everything will come up on its own. If there are scheduled listings, it'll start playing them.
