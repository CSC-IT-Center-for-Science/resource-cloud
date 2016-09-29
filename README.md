[![TravisCI](https://travis-ci.org/CSC-IT-Center-for-Science/pouta-blueprints.svg)](https://travis-ci.org/CSC-IT-Center-for-Science/pouta-blueprints/) [![Code Climate](https://codeclimate.com/github/CSC-IT-Center-for-Science/pouta-blueprints/badges/gpa.svg)](https://codeclimate.com/github/CSC-IT-Center-for-Science/pouta-blueprints) [![Test Coverage](https://codeclimate.com/github/CSC-IT-Center-for-Science/pouta-blueprints/badges/coverage.svg)](https://codeclimate.com/github/CSC-IT-Center-for-Science/pouta-blueprints)

# Pouta Blueprints

**Pouta Blueprints** is a frontend to manage cloud resources and lightweight user
accounts.
Currently supported resource types are 
 - [OpenStack driver](pouta_blueprints/drivers/provisioning/openstack_driver.py),
    which can be used to launch instances on OpenStack cloud.
 - [Docker driver] (pouta_blueprints/drivers/provisioning/README_docker_driver.md),
    for running web notebook instances in Docker containers on a pool of virtual machines. 
 - [Pouta Virtualcluster](https://github.com/CSC-IT-Center-for-Science/pouta-virtualcluster),
    which can be used to launch clusters on [cPouta](https://research.csc.fi/pouta-iaas-cloud).
    
Additional resources can be added by implementing the driver interface [/pouta_blueprints/drivers/provisioning/base_driver.py](pouta_blueprints/drivers/provisioning/base_driver.py)

## Installation on cPouta ##

To install Pouta Blueprints in your project on cPouta, see [how_to_install_on_cpouta.md](doc/how_to_install_on_cpouta.md)

## Installation of development environment ##

Provided Vagrantfile can be used to start a new **Pouta Blueprints** instance
(requires VirtualBox or Docker)

    vagrant up

or

    vagrant up --provider=docker

After the installation the first admin user is created by using the
initialization form at (https://localhost:8888/#/initialize). The development 
environment uses a self-signed certificate.


## Database migrations ##

Check out [database_migrations.md](doc/database_migrations.md) for how to run
or create migrations.
