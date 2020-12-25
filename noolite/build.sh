docker run --rm -ti --name hassio-builder --privileged \
  -v /home/andvikt/projects/noolite:/data \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  homeassistant/amd64-builder -t /data --aarch64 --test \
  -i noolite_addon -d local