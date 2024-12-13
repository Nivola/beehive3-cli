# beehive3-cli
__beehive3-cli__ is a project that contains a shell console (Command Line Interface) that is used to manage all the
components of the beehive platform:
- cmp
- orchestrated infrastructure platform
- instruments

## Installing

### Install requirements
First of all you have to install some package:

```
$ sudo apt-get install gcc
$ sudo apt-get install -y python-dev libldap2-dev libsasl2-dev libssl-dev
```

### Create python virtualenv
At this point create a virtualenv

```
$ python3 -m venv /tmp/beehive-py3-test-env
$ source /tmp/beehive-py3-test-env/bin/activate
$ pip3 install wheel
```

### Install python packages

public packages:

```
$ pip3 install -U git+https://github.com/Nivola/beecell.git
$ pip3 install -U git+https://github.com/Nivola/beehive3_cli.git
```


#### Inspect logs

- beehive3.log

#### Update bash completion commands

cd <package_path>/beehive3-cli/beehive3_cli/ext
beehive3 bash-completion > commands

#### Run bash completion

in docker:

source /home/beehive3/pkgs/beehive3-cli/beehive3_cli/ext/beehive_completion.rc /home/beehive3/pkgs/beehive3-cli/beehive3_cli/ext/commands


### Starting cli with docker

#### Prerequisites
- You must have already downloaded the projects beecell, beedrones, beehive.
- Install a MySql/MariaDB database (MySql version > 5.7, MariaDB version > 10.5).

We suggest to use a Mysql Docker that runs in a docker network "nivolanet" for being reachable from others Nivola components
- Install Elasticsearch server where write logs.
- Install Docker for building images.


#### Mysql Docker
This section explains how to install a MySQL instance with docker.
If you intend to install mysql in another way, ignore this section.

Create folders where Mysql can store persistent data
```
mkdir $HOME/mysql
mkdir $HOME/mysql/datadir
```

Run Mysql image in "nivolanet" network with an IP.
This way mysql is reachable from others Nivola components
and the IP doesn't change every time you restart the instance
```
docker run --network nivolanet --name=mysql-nivola \
--ip 192.168.49.100 \
--mount type=bind,src=$HOME/mysql/datadir,dst=/var/lib/mysql \
-d mysql/mysql-server:8.0.25
```

Look mysql docker logs and find "GENERATED ROOT PASSWORD".
The following value is the "root" user temporary password.
```
docker logs mysql-nivola 2>&1 | more
```

Update "root" db user password and create a "root" db user with password "nivola" for accessing from any IP.
The default "root" one only allows you to login from localhost.
```
docker exec -it mysql-nivola mysql -uroot -p

	-- update localhost root password
	ALTER USER 'root'@'localhost' IDENTIFIED BY 'nivola';

	-- create user root
	CREATE USER 'root'@'%' IDENTIFIED BY 'docker';
	GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
	FLUSH PRIVILEGES;
```

Search the IP of your database instance for following environment configurations
```
docker inspect mysql-nivola | grep "IPAddress"
```

#### Copy config
Copy beehive3-cli/deploy/files/beehive3cli_docker to "cli3_nivola" directory under your home.
Update configuration in file /config/env/mylab.yml
 - replace placeholder <HOST_DB> with your db host and <DB_ROOT_PW> with password of db user "root"
 - entries /cmp/endpoints/... have to point to Nginx to connect to CMP (are not necessary yet)
 - replacement of <HOST_NGINX> can be done after you have installed the cmp and Nginx
 - replace placeholder <HOST_ELASTIC> with your Elasticsearch server IP

Look at configuration file /config/beehive.yml
The parameters:
- ansible_path
- cmp_post_install_path
point at temporary folder where you can copy files for customizations


#### Build docker image
In deploy directory __beehive3_cli/deploy__ you find dockerfiles.
Build docker image "nivola/console-python":
```
docker image build --tag nivola/console-python -f beehive3-cli/deploy/Dockerfile.cli-py3 .
```

Build docker image "nivola/console" that start from image "nivola/console-python"
or downloading projects into image and passing git user/password
```
docker image build --build-arg GITUSER=<USER> --build-arg GITPWD=<PASSWORD> --tag nivola/console -f beehive3-cli/deploy/Dockerfile.beehive3-cli .
```
or copying projects into image (in this case you have to go to folder where you downloaded projects)
```
docker image build --tag nivola/console -f beehive3-cli/deploy/Dockerfile.beehive3-cli .
```

#### Run cli docker image
We suggest that CLI process starts in a docker network "nivolanet" for being reachable from other Nivola components (Nginx), descrive in Nivola project.
Launch:
```
docker run -it --network nivolanet --name beehive3-cli --rm --entrypoint bash \
-e TZ=Europe/Rome --dns 10.101.0.10 --dns 10.101.0.105 \
--mount type=bind,source=$HOME/cli3_nivola,target=/home/beehive3/.beehive3 \
--mount type=bind,source=$HOME/<WORKSPACE>,target=/home/beehive3/pkgs \
--mount type=bind,source=/tmp,target=/tmp \
nivola/console
```

Type "beehive3" in cli to verify Beehive Console is running correctly and showing help.
Type "beehive3 envs" to show environments
Others command to verify configuration:
```
beehive3 platform mysql ping
beehive3 platform elastic ping
beehive3 platform elastic info
```

Watching cli log:
```
docker exec -it beehive3-cli tail -100f /home/beehive3/beehive3.log
```

## Versioning
We use Semantic Versioning for versioning. (http://semver.org)

## Authors and Contributors
See the list of contributors who participated in this project in the file AUTHORS.md contained in each specific project.

## Copyright
CSI Piemonte - 2018-2024

Regione Piemonte - 2020-2022

## License
See EUPL v1_2 EN-LICENSE.txt or EUPL v1_2 IT-LICENSE.txt file for details

## Community site (Optional)
At https://www.nivolapiemonte.it/ could find all the informations about the project.
