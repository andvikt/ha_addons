docker run --rm -ti --name hassio-builder --privileged \
  -v /home/andvikt/projects/ha_addons/noolite:/data \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  homeassistant/amd64-builder -t /data --aarch64 --test \
  -i noolite \
  --docker-hub andvikt \
  --self-cache \
  --no-crossbuild-cleanup \
  --docker-user andvikt \
  --docker-password $DOCKER_PWD

# docker push andvikt/noolite
# git commit . -m "new version"
# git push