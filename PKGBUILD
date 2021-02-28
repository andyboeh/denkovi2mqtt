pkgname=denkovi2mqtt-git
pkgver=r2.429c5c9
pkgrel=1
pkgdesc="Simple Denkovi SmartDEN to MQTT bridge"
arch=('any')
url="https://github.com/andyboeh/denkovi2mqtt"
license=('GPL')
depends=('python' 'python-paho-mqtt' 'python-easysnmp')
install='denkovi2mqtt.install'
source=('denkovi2mqtt-git::git+https://github.com/andyboeh/denkovi2mqtt.git'
        'denkovi2mqtt.install'
        'denkovi2mqtt.sysusers'
        'denkovi2mqtt.service')
provides=('denkovi2mqtt')
conflicts=('denkovi2mqtt')
sha256sums=('SKIP'
            '6de50bccbce4a5d387645ea8aefb2ba47c2a3d4e03ad6334f42bb5729266a3b7'
            'c7f86396cad9849d5aa8eba207c4c5c03c5851d86db0eaefb16ee248c713ace5'
            '4c67fde53f11888b068c5d68c1936935cbd3c253f2a1eab9ce7cf73860e1d901')

backup=('opt/denkovi2mqtt/denkovi2mqtt.yaml')

pkgver() {
  cd "$pkgname"
  printf "r%s.%s" "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

package() {
  cd "${pkgname}"
  install -d "${pkgdir}/opt/denkovi2mqtt"
  cp denkovi2mqtt.py "${pkgdir}/opt/denkovi2mqtt/denkovi2mqtt.py"
  install -Dm644 "${srcdir}/denkovi2mqtt.service" "${pkgdir}/usr/lib/systemd/system/denkovi2mqtt.service"
  install -Dm644 "${srcdir}/denkovi2mqtt.sysusers" "${pkgdir}/usr/lib/sysusers.d/denkovi2mqtt.conf"
  install -Dm644 denkovi2mqtt.yaml "${pkgdir}/opt/denkovi2mqtt/denkovi2mqtt.yaml"
}