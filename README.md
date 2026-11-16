# ps5-fedora-manager
ps5-fedora-manager


sudo git -C /opt/ps5-manager fetch --all --prune && \
sudo git -C /opt/ps5-manager reset --hard origin/main && \
sudo install -m 0755 /opt/ps5-manager/ps5-manager.sh /usr/local/bin/ps5-manager
