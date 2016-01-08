# docker-tools
Docker tools for Ops.

docker_setup.py
================

Simple script to spawn multiple docker "VM" and shared directory to test apps.

This is not a script for production. The purpose of this script is to help
Ops people to quiclky spawn multiple VM with network to test new apps.

This script create X containers + one share storage in a container.
You can reset each of them in one line command with a given image name.

**Features** :
  * Create shared directory between containers (/share)
  * Create shared directory between containers and host (/host)
  * Datas in shared directory are persistant !
  * Create or reset container (nodeX) with a given image name.
  * Reset share container.
  * NodeX containers are accessible with docker attach.
  * Launch first boot command in nodeX containers
  * Containers etc/hosts file dynamically filled.

**Architecture** :

```
                Shared directories with the host
                             +
                             |
       +--------------------------------------------+
       |                     |                      |
+------+------+       +------+------+       +-------+-----+
|   Node1     |       |   NodeX     |       |   Node4     |
+-----+-------+       +------+------+       +-------+-----+
      |                      |                      |
      +---------------------------------------------+
                             |
+----------------------------+----------------------------+
|                         /Share                          |
+---------------------------------------------------------+
```

**Usage** :

```
./docker_setup.py  --help
usage: docker_setup.py [-h] [-c] [-u] [--create-share] [-v host:container]
                       [--command command] [-i IMAGE] [--cleanup]

optional arguments:
  -h, --help            show this help message and exit
  -c, --create          Create or recreate the stack
  -u, --dns-update      update /etc/hosts file in the stack
  --create-share        Create or recreate the shared volume/container between
                        containers
  -v host:container, --host-volume host:container
                        This argument can be specified multiple times. Specify
                        path on the host you want to share with containers. Ex
                        /tmp:/opt. (This is applied only when create/recreate
                        the stack)
  --command command     First boot command to execute after start all
                        container (This is applied only when create/recreate
                        the stack)
  -i IMAGE, --image IMAGE
                        Give image for stack create
  -s SIZE, --size SIZE  Indicate the stack size (number of containers
  --cleanup             Remove all elements from this stack
```

Create or recreate a shared volume between containers:

    python docker_setup.py  --create-share

Create or recreate the stack with a given image.

    python docker_setup.py  --create --image myimage:01

Create the stack with 2 directory shared from the host

    python docker_setup.py  --create --host-volume /opt:/opt --host-volume  /.../scripts:/scripts

Create the stack and exec boot command after the stack creation :

    python docker_setup.py  --create --host-volume  /.../scripts:/scripts --command /script/init.sh

Update /etc/hosts file in case you reboot containers and private IP change.

    python docker_setup.py  --dns-update

Remove all containers handled by this script

    python docker_setup.py --cleanup
