LOCKED_2004_BOX_VERSION = "20211026.0.0"
LOCKED_JAMMY_VERSION = "20220712.0.0"
WORDPRESS_VERSION = "-6.0.1-en_GB"

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"
  config.vm.box_version = LOCKED_JAMMY_VERSION
  config.vm.box_check_update = false
  config.vm.hostname = "img-rescaler"
  config.vm.network :forwarded_port, guest: 80, host: 8382
  config.vm.network :forwarded_port, guest: 443, host: 8542
  config.vm.network :forwarded_port, guest: 22, host: 8214, id: 'ssh'

  config.vm.provision "file", source: "full_db_220727_0953-mariadb.sql", destination: "/home/vagrant/current_db.sql"
  # full_db_220727_0953-mariadb.sql is a backup from a mariadb docker paired with an apache wordpress docker.

  config.vm.provision "Install OS packages", type: "shell", inline: <<-SHELL
apt-get update
apt-get install -y apache2 \
                   libapache2-mod-php \
                   mysql-server \
                   php \
                   php-bcmath \
                   php-curl \
                   php-intl \
                   php-json \
                   php-mbstring \
                   php-mysql \
                   php-xml \
                   php-zip \
                   php-imagick \
                   python3-pip \
                   imagemagick
SHELL

  config.vm.provision "Setup WordPress", type: "shell", inline: <<-SHELL
chown -R www-data: /var/www/html
curl https://en-gb.wordpress.org/wordpress#{WORDPRESS_VERSION}.tar.gz | sudo -u www-data tar zx --strip-components=1 -C /var/www/html
cp /vagrant/ssl-params.conf /etc/apache2/conf-available/ssl-params.conf
cp /vagrant/wordpress.conf /etc/apache2/sites-available/wordpress.conf
sudo -u www-data cp /vagrant/wp.htaccess /var/www/html/.htaccess
sudo -u www-data cp /vagrant/wp-config.php /var/www/html/wp-config.php
SHELL

  config.vm.provision "Setup MySQL", type: "shell", inline: <<-SHELL
mysql -u root < /vagrant/wpdbsetup.sql
mysql -uroot wordpress < /home/vagrant/current_db.sql
SHELL

  config.vm.provision "Setup Apache", type: "shell", inline: <<-SHELL
openssl req -new -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -days 365 -nodes -x509 \
    -subj "/CN=localhost" \
    -keyout /etc/ssl/private/apache-selfsigned.key -out /etc/ssl/certs/apache-selfsigned.crt
a2enmod ssl
a2enmod headers
a2enmod rewrite
a2ensite wordpress
a2enconf ssl-params
a2dissite 000-default
systemctl reload apache2
SHELL

  config.vm.provision "Grab the TLS cert from WP", type: "shell", inline: <<-SHELL
  echo quit | openssl s_client -showcerts -servername "localhost" -connect localhost:443 > /vagrant/tests/self-signed-cacert.crt
SHELL

  config.vm.provision "pip install requirements", type: "shell", privileged: false, inline: <<-SHELL
pip install -r /vagrant/requirements.txt
SHELL

  config.vm.provision "configure vagrant shell", type: "shell", privileged: false, inline: <<-SHELL
echo "colo ron" > ~/.vimrc
SHELL

  config.vm.provision "acquire wp_api", type: "shell", privileged: false, inline: <<-SHELL
git clone https://github.com/ployt0/wp_app_api.git
cp -r wp_app_api/wp_api /vagrant/tests/
SHELL

  config.vm.provision "Test or die", type: "shell", privileged: false, inline: <<-SHELL
pip install -r /vagrant/requirements.txt
cd /vagrant/tests
export PYTHONPATH=/vagrant/ss_img_shrinker
/home/vagrant/.local/bin/pytest
SHELL

  config.vm.provision "Check coverage", type: "shell", privileged: false, inline: <<-SHELL
cd /vagrant/tests
PYTHONPATH=../ss_img_shrinker /home/vagrant/.local/bin/coverage run --source="../ss_img_shrinker" -m pytest
PYTHONPATH=../ss_img_shrinker /home/vagrant/.local/bin/coverage report -m --fail-under=90
SHELL

end


