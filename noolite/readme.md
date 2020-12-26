# Noolite2MQTT
Аддон представляет возможность управления устройствами noolite с помощью модуля MTRF-64, подключенного к uart raspberry pi и модуля mqtt в HA. Устройства будут отображаться в HA автоматически.

Для активации uart потребуется отредактировать файл config.txt в hass.io. Для этого вам потребуется ssh доступ к системе, инструкция описана [тут](https://developers.home-assistant.io/docs/en/hassio_debugging.html)

Далее отредактировать файл config.txt:
```shell script
ssh root@hassio.local -p 22222 -i .ssh/YOUR Private Key File
login
vi /mnt/boot/config.txt

enable_uart=1

reboot
```
