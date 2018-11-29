#!/bin/sh

wget http://phantomjs.googlecode.com/files/phantomjs-1.9.1-linux-x86_64.tar.bz2
tar xjf phantomjs-1.9.1-linux-x86_64.tar.bz2
sudo rm -rf /opt/local/phantomjs
sudo mv  phantomjs-1.9.1-linux-x86_64 /opt/local/phantomjs

sudo yum remove -y libmemcached libmemcached-devel
sudo wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
sudo wget http://rpms.famillecollet.com/enterprise/remi-release-6.rpm
sudo rpm -Uvh remi-release-6*.rpm epel-release-6*.rpm
sudo yum --enablerepo=remi install -y libmemcached-last libmemcached-last-devel
sudo yum install -y memcached
sudo service memcached restart

cd ..
virtualenv mics_env
source mics_env/bin/activate
cd -
pip install -r pip-requires.txt
cp mics/snap-ci/snap-settings.py mics/localsettings.py
cp survey/investigator_configs.py.example survey/investigator_configs.py
./manage.py syncdb --noinput
./manage.py migrate

