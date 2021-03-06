#!/usr/bin/env python

import os
import re
import functions
from config import Config
from execcmd import ExecCmd

packageStatus = [ 'installed', 'notinstalled', 'uninstallable' ]
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae']
blacklistPath = '/etc/modprobe.d/blacklist-nouveau.conf'
nvUbuntuMin = 2000
nvUbuntu = [
[5000, 'nvidia-96'],
[6000, 'nvidia-173'],
[0, 'nvidia-current']
]

class Nvidia():
    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        
        # Install nvidia-detect if it isn't installed already
        if functions.getPackageStatus('nvidia-detect') == packageStatus[1]:
            self.log.write('Install nvidia-detect', 'nvidia.getNvidia', 'info')
            self.ec.run('apt-get -y --force-yes install nvidia-detect')
    
    # Called from drivers.py: Check for Nvidia
    def getNvidia(self):
        hwList = []
        # Get the appropriate driver
        drv = self.getDriver()
        if drv != '':
            self.log.write('Get package status for driver: ' + drv, 'nvidia.getNvidia', 'info')
            status = functions.getPackageStatus(drv)
            self.log.write('Package status: ' + status, 'nvidia.getNvidia', 'debug')
            hw = functions.getGraphicsCard()
            hwList.append([hw, hwCodes[0], status])
        
        return hwList

    # Check distribution and get appropriate driver
    def getDriver(self):
        drv = ''
        hw = functions.getGraphicsCard()
        # Is it Nvidia?
        nvChk = re.search('\\b' + hwCodes[0] + '\\b', hw.lower())
        if nvChk:
            if self.distribution == 'debian':
                # Get Debian driver for Nvidia
                self.log.write('Get the appropriate Nvidia driver', 'nvidia.getNvidia', 'info')
                drv = self.ec.run("nvidia-detect | grep nvidia- | tr -d ' '")[0]
                self.log.write('Nvidia driver to install: ' + drv, 'nvidia.getNvidia', 'info')
            else:
                # Get Ubuntu driver for Nvidia
                nvChip = re.search('geforce (\d+)', hw.lower())
                if nvChip:
                    for chip in nvUbuntu:
                        if (nvChip.group(1) >= nvUbuntuMin and nvChip.group(1) < chip[0]) or chip[0] == 0:
                            drv = chip[1]
                            self.log.write('Nvidia driver to install: ' + drv, 'nvidia.getNvidia', 'info')
                            break
        else:
            self.log.write('No Nvidia card found', 'nvidia.getNvidia', 'debug')
                
        return drv
    
    # Install the given packages
    def installNvidiaDriver(self, packageList):
        try:
            removePackages = ''
            installPackages = ''
            # Check if drivers are available in the repositories
            for package in packageList:
                # Build install packages string
                installPackages += ' ' + package[0]
                if package[1] == 1:
                    # Check if package is installed
                    # If it is, it's nominated for removal
                    self.log.write('Is package installed: ' + package[0], 'nvidia.installNvidiaDriver', 'debug')
                    drvChkCmd = 'apt search ' + package[0] + ' | grep ^i | wc -l'
                    drvChk = self.ec.run(drvChkCmd, False)
                    if functions.strToInt(drvChk[0]) > 0:
                        # Build remove packages string
                        removePackages += ' ' + package[0]
            
            # Remove these packages before installation
            if removePackages != '':
                self.log.write('Remove drivers before reinstallation: ' + removePackages, 'nvidia.installNvidiaDriver', 'debug')
                nvDrvRemCmd = 'apt-get -y --force-yes remove' + removePackages
                self.ec.run(nvDrvRemCmd)
                
            # Preseed answers for some packages
            self.preseedNvidiaPackages('install')
                
            # Install the packages
            self.log.write('Install drivers: ' + installPackages, 'nvidia.installNvidiaDriver', 'debug')
            nvDrvInstCmd = 'apt-get -y --force-yes install' + installPackages
            self.ec.run(nvDrvInstCmd)
            
        except Exception, detail:
            self.log.write(detail, 'nvidia.installNvidiaDriver', 'exception')
    
    # Get additional packages
    # The second value in the list is a numerical value (True=1, False=0) whether the package must be removed before installation
    def getAdditionalPackages(self, driver):
        drvList = []
        # Distribution specific packages
        if self.distribution == 'debian':
            if driver == 'nvidia-glx':
                drvList.append(['nvidia-kernel-dkms', 1])
            elif driver == 'nvidia-glx-legacy-96xx':
                drvList.append(['nvidia-kernel-legacy-96xx-dkms', 1])
            elif driver == 'nvidia-glx-legacy-173xx':
                drvList.append(['nvidia-kernel-legacy-173xx-dkms', 1])
            drvList.append(['build-essential', 0])
            drvList.append(['nvidia-xconfig', 0])
        # Common packages
        drvList.append([driver, 1])
        drvList.append(['nvidia-settings', 0])
        return drvList
    
    # Called from drivers.py: install the Nvidia drivers
    def installNvidia(self):
        try:
            # Get the appropriate drivers for the card
            drv = self.getDriver()
            if drv != '':
                packages = self.getAdditionalPackages(drv)
                self.installNvidiaDriver(packages)
                # Install the appropriate drivers
                if self.distribution == 'debian':
                    # Configure Nvidia
                    self.log.write('Configure Nvidia...', 'nvidia.installNvidia', 'debug')
                    self.ec.run('nvidia-xconfig')
                
                # Blacklist Nouveau
                self.log.write('Blacklist Nouveau: ' + blacklistPath, 'nvidia.installNvidia', 'debug')
                modFile = open(blacklistPath, 'w')
                modFile.write('blacklist nouveau')
                modFile.close()
            else:
                self.log.write('No apprpriate driver found', 'nvidia.installNvidia', 'error')
                
        except Exception, detail:
            self.log.write(detail, 'nvidia.installNvidia', 'exception')
    
    # Called from drivers.py: remove the Nvidia drivers and revert to Nouveau
    def removeNvidia(self):
        try:
            # Preseed answers for some packages
            self.preseedNvidiaPackages('purge')
            
            self.log.write('Removing Nvidia drivers', 'nvidia.removeNvidia', 'info')
            packages = self.getAdditionalPackages(self.getDriver())
            for package in packages:
                self.log.write('Remove package: ' + package[0], 'nvidia.removeNvidia', 'debug')
                cmdPurge = 'apt-get -y --force-yes purge ' + package[0]
                self.ec.run(cmdPurge)
            self.ec.run('apt-get -y --force-yes autoremove')
            self.ec.run('apt-get -y --force-yes install xserver-xorg-video-nouveau')
           
            # Remove blacklist Nouveau
            if os.path.exists(blacklistPath):
                self.log.write('Remove : ' + blacklistPath, 'nvidia.removeNvidia', 'debug')
                os.remove(blacklistPath)
                
            # Remove xorg.conf
            xorg = '/etc/X11/xorg.conf'
            if os.path.exists(xorg):
                self.log.write('Remove : ' + xorg, 'nvidia.removeNvidia', 'debug')
                os.remove(xorg)
                
        except Exception, detail:
            self.log.write(detail, 'nvidia.removeNvidia', 'exception')
            
    def preseedNvidiaPackages(self, action):
        if self.distribution == 'debian':
            # Run on configured system and debconf-utils installed:
            # debconf-get-selections | grep nvidia > debconf-nvidia.seed
            # replace tabs with spaces and change the default answers (note=space, boolean=true or false)
            debConfList = []
            debConfList.append('nvidia-support nvidia-support/warn-nouveau-module-loaded note ')
            debConfList.append('nvidia-support nvidia-support/check-xorg-conf-on-removal boolean false')
            debConfList.append('nvidia-support nvidia-support/check-running-module-version boolean true')
            debConfList.append('nvidia-installer-cleanup nvidia-installer-cleanup/delete-nvidia-installer boolean true')
            debConfList.append('nvidia-installer-cleanup nvidia-installer-cleanup/remove-conflicting-libraries boolean true')
            debConfList.append('nvidia-support nvidia-support/removed-but-enabled-in-xorg-conf note ')
            debConfList.append('nvidia-support nvidia-support/warn-mismatching-module-version note ')
            debConfList.append('nvidia-support nvidia-support/last-mismatching-module-version string 302.17')
            debConfList.append('nvidia-support nvidia-support/needs-xorg-conf-to-enable note ')
            debConfList.append('nvidia-support nvidia-support/create-nvidia-conf boolean true')
            debConfList.append('nvidia-installer-cleanup nvidia-installer-cleanup/uninstall-nvidia-installer boolean true')
            
            # Add each line to the debconf database
            for line in debConfList:
                os.system('echo "' + line + '" | debconf-set-selections')
            
            # Install or remove the packages
            self.ec.run('apt-get -y --force-yes ' + action + ' nvidia-support nvidia-installer-cleanup')
