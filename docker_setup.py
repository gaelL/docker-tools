#!/usr/bin/env python

"""
Simple script to spawn multiple docker "VM" and shared directory to test apps.
This is not a script for production. The purpose of this script is to help
Ops people to quiclky spawn multiple VM with network to test new apps.

This script create X containers + one share storage in a container.
You can reset each of them in one line command with a given image name.

Features :
  * Create shared directory between containers (/share)
  * Create shared directory between containers and host (/host)
  * Datas in shared directory are persistant !
  * Create or reset container (nodeX) with a given image name.
  * Reset share container.
  * NodeX containers are accessible with docker attach.
  * Launch first boot command in nodeX containers
  * Containers etc/hosts file dynamically filled.

Architecture :
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


Usage :

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

"""

import docker.client
import argparse
import logging

# Init logging level with debug stream handler
LOG = logging.getLogger()
LOG.setLevel(logging.INFO)

# Parse args
PARSER = argparse.ArgumentParser()
PARSER.add_argument('-c', '--create',
                    help='Create or recreate the stack',
                    action='store_true',
                    default=False)

PARSER.add_argument('-u', '--dns-update',
                    help='update /etc/hosts file in the stack',
                    action='store_true',
                    default=False)

PARSER.add_argument('--create-share',
                    help='Create or recreate the shared volume/container'
                         ' between containers',
                    action='store_true',
                    default=False)

PARSER.add_argument('-v', '--host-volume',
                    metavar='host:container',
                    help='This argument can be specified multiple times. '
                         'Specify path on the host you want to share with '
                         'containers. Ex /tmp:/opt. (This is applied only when'
                         ' create/recreate the stack)',
                    action='append',
                    type=str)

PARSER.add_argument('--command',
                    metavar='command',
                    help='First boot command to execute after start all'
                         ' container (This is applied only when '
                         'create/recreate the stack)',
                    type=str)

PARSER.add_argument('-i', '--image',
                    help='Give image for stack create',
                    type=str)

PARSER.add_argument('--cleanup',
                    help='Remove all elements from this stack',
                    action='store_true',
                    default=False)

ARGS = PARSER.parse_args()


class Docker(docker.Client):
    """Override of docker client.
       Usage :
           cli = Docker(base_url='unix://var/run/docker.sock')"""

    def __init__(self, *args, **kwargs):
        super(Docker, self).__init__(*args, **kwargs)
        self._print_template = ("| {Id:65}| {Name:8}| {Status:25}|"
                                " {Image:16}| {VolumesFrom:12}| {Binds:20}|")

    def _get_hosts(self, containers):
        "Get IP of each containers"
        hosts = []
        for _container in containers:
            infos = self.inspect_container(container=_container)
            _ip = infos['NetworkSettings']['IPAddress']
            _name = infos['Name'].lstrip('/')
            _id = infos['Id']

            hosts.append('%s %s %s' % (_ip, _name, _id))
        return hosts

    def set_hosts(self, containers):
        "Set IP of each containers in /etc/hosts file of each containers."
        # Get IP for all nodes
        hosts = self._get_hosts(containers=containers)
        # Append default lines
        hosts.append('127.0.0.1       localhost')
        hosts.append('::1     localhost ip6-localhost ip6-loopback')
        hosts.append('fe00::0 ip6-localnet')
        hosts.append('ff00::0 ip6-mcastprefix')
        hosts.append('ff02::1 ip6-allnodes')
        hosts.append('ff02::2 ip6-allrouters')
        # Write it on each containers
        for _container in containers:
            cmd_id = self.exec_create(container=_container,
                                      tty=False,
                                      stdout=False,
                                      cmd='''bash -c 'echo -e "%s" > /etc/hosts' ''' % '\n'.join(hosts))
            self.exec_start(exec_id=cmd_id, tty=False)

    def create_container(self, *args, **kwargs):
        "Override create_container to force default value"
        kwargs['tty'] = True
        kwargs['stdin_open'] = True
        kwargs['hostname'] = kwargs.get('name')
        super(Docker, self).create_container(*args, **kwargs)

    def remove_container(self, *args, **kwargs):
        "Override remove_container to force default value"
        kwargs['force'] = True
        super(Docker, self).remove_container(*args, **kwargs)

    def remove_containers(self, names, *args, **kwargs):
        "Call remove multiple times"
        for name in names:
            kwargs['container'] = name
            self.remove_container(*args, **kwargs)

    def create_containers(self, names, *args, **kwargs):
        "Call create multiple times"
        for name in names:
            kwargs['name'] = name
            self.create_container(*args, **kwargs)

    def starts(self, names, *args, **kwargs):
        "Call start multiple times"
        for name in names:
            kwargs['container'] = name
            self.start(*args, **kwargs)

    def create_shared_volume(self, name, image, volume=None):
        "Create a container to host shared volume"
        if volume is None:
            volume = '/%s' % name
        self.create_container(name=name,
                              command='/bin/true',
                              volumes=volume,
                              image=image)

    def print_containers_status(self, filter=None):
        """print containers status. Arg filter can be an array of container
            names you wan't to display"""

        print self._print_template.format(  # header
          Name="Name", Id="Id", Status="Status", Image="Image",
          VolumesFrom='VolumesFrom', Binds='Binds'
        )

        for container in cli.containers(all=True):
            container['Name'] = container['Names'][0].lstrip('/')
            if container['Name'] not in filter and filter is not None:
                continue
            _inspect = self.inspect_container(container=container)

            container['VolumesFrom'] = ' '.join(_inspect['HostConfig']['VolumesFrom'] or [])
            container['Binds'] = ' '.join(_inspect['HostConfig']['Binds'] or [])

            print self._print_template.format(**container)

    def is_container(self, containe):
        'Check if container exist or not'
        try:
            cli.inspect_container(container='share')
            return True
        except docker.errors.NotFound:
            return False

    def exec_cmd(self, command, containers):
        'Exec a commande on multiples containers'
        for container in mycontainers:
            LOG.info('%s - Launch first boot command %s' % (container, ARGS.command))
            cmd_id = cli.exec_create(container=container,
                                     tty=False,
                                     stdout=True,
                                     stderr=True,
                                     cmd=ARGS.command)
            # For later improve with stream.
            # https://github.com/docker/docker-py/issues/655
            print cli.exec_start(exec_id=cmd_id, tty=False)


if __name__ == '__main__':
    # Init logger
    LOGFORMAT = '%(asctime)s %(levelname)s -: %(message)s'
    FORMATTER = logging.Formatter(LOGFORMAT)
    HDL = logging.StreamHandler()
    HDL.setFormatter(FORMATTER)
    LOG.addHandler(HDL)

    # Set container list
    mycontainers = ['node1', 'node2', 'node3', 'node4']

    # Default image name
    if ARGS.image:
        myimage = ARGS.image
    else:
        myimage = 'debian'

    # Init docker cli
    cli = Docker(base_url='unix://var/run/docker.sock')

    # Print actual stack status
    print 'Actual stack status :'
    cli.print_containers_status(filter=mycontainers + ['share'])

    if ARGS.create_share:
        try:
            LOG.info('Remove existing share containers')
            container = cli.remove_containers(names=['share'])
        except docker.errors.APIError as e:
            pass
        # Create shared volume
        LOG.info('Create existing share containers')
        cli.create_shared_volume(name='share', image='debian')

    if ARGS.create:
        # Remove existing containers
        try:
            LOG.info('Remove existing containers')
            container = cli.remove_containers(names=mycontainers)
        except docker.errors.APIError as e:
            pass

        # Create new containers
        container = cli.create_containers(image=myimage,
                                          names=mycontainers)

        start_kwargs = {}

        # Share between containers
        if cli.is_container('share'):
            # Note : volume_from is on start because :
            # docker.errors.InvalidVersion: 'volumes_from' parameter has no
            # effect on create_container(). It has been moved to start()
            LOG.info('Start with share storage')
            start_kwargs['volumes_from'] = 'share'

        # Share between host and containers
        if ARGS.host_volume:
            # Doc for host volumes https://github.com/docker/docker/issues/2949
            binds = {}
            for volume in ARGS.host_volume:
                (host_path, container_path) = volume.split(':')
                binds[host_path] = container_path
            start_kwargs['binds'] = binds

        cli.starts(names=mycontainers, **start_kwargs)

        # Set etc/hosts file with all addresses
        cli.set_hosts(mycontainers)

        # If boot commande is specified run it
        if ARGS.command:
            cli.exec_cmd(command=ARGS.command,
                         containers=mycontainers)

        print 'New stack status:'
        cli.print_containers_status(filter=mycontainers + ['share'])

    elif ARGS.dns_update:
        # Set hosts file with all addresses
        cli.set_hosts(mycontainers)
    elif ARGS.cleanup:
        try:
            LOG.info('Cleanup existing containers')
            container = cli.remove_containers(names=mycontainers + ['share'])
        except docker.errors.APIError as e:
            pass
