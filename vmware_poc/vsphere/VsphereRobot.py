import time
import requests
from robot.api.deco import keyword
from robot.api import logger


from vmware.vapi.vsphere.client import create_vsphere_client
from com.vmware.vcenter_client import VM
from com.vmware.vcenter.vm_client import Power
from com.vmware.vcenter.vm.guest_client import Power as GuestPower

from com.vmware.vcenter_client import (
    Datastore, Datacenter, Folder, ResourcePool)

from com.vmware.content.library_client import Item
from com.vmware.vcenter.vm_template_client import LibraryItems
from com.vmware.vapi.std.errors_client import ServiceUnavailable


__version__ = '1.0.0'

STATE_TIMEOUT = 500


class VsphereRobot:
    """
    VsphereRobot is a wrapper of the Vsphere python SDK lib\n
    This lib provide Robot Keywords to create and manipulate
    VMs in the Vcenter
    """
    ROBOT_LIBRARY_VESION = __version__
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'
    _clients = {}
    _client = None

    @keyword('Connect to Vsphere ${session_name} to host ${hostname} with user ${username} and password ${password}')
    def _connect_to_vsphere(self, session_name, hostname, username, password):
        self.session = _get_unverified_session()
        client = create_vsphere_client(
            server=hostname, username=username, password=password, session=self.session)

        self._clients[session_name] = client
        self._client = client

        logger.info(f'User ${username} connected in session ${session_name}')

    @keyword('Switch to Session ${session_name}')
    def switch_to_session(self, session_name):
        """
        Switch to Session will use the session_name to change between
        session\n
        if the session dont exists will raise a exception
        """
        if not session_name in self._clients:
            raise Exception(
                "Vsphere session {} does not exists".format(session_name))
        self._client = self._clients[session_name]

    @keyword('List All Vms')
    def list_vm(self):
        """
        List all VMs inside the vCenter Server
        """
        listOfVms = self._client.vcenter.VM.list()

        logger.info(f'All Vms in the Vcenter: ${listOfVms}')

        return listOfVms

    @keyword('Get VM ${vm_name} Info')
    def get_vm(self, vm_name):
        """
        Get a single VM
        """
        vms_name = set([vm_name])
        vms = self._client.vcenter.VM.list(VM.FilterSpec(names=vms_name))

        logger.info(f'VM info ${vms[0]}')
        return vms[0]

    @keyword('Get VM ${vm} BiosUUID')
    def get_vm_uuid(self, vm):
        """
        Get VM instance bios_uuid
        """
        vm = self._client.vcenter.VM.get(vm.vm)

        logger.info(f'VM identity ${vm.identity}')
        return vm.identity.bios_uuid

    @keyword('Get VM ${vm} IP')
    def get_vm_ip(self, vm):
        """
        Get the identity info from a VM
        @return: the vm ip address.
        """
        self.power_on(vm)

        self._wait_for_guest_info_ready(vm, 700)

        identity = self._client.vcenter.vm.guest.Identity.get(vm.vm)

        logger.info(f'VM IP: ${identity.ip_address}')
        return identity.ip_address

    @keyword('Get VM ${vm} Power Status')
    def vm_power_status(self, vm):
        """
        Get the VM Power status
        @return: the vm Power status.
        """
        status = self._client.vcenter.vm.Power.get(vm.vm)
        logger.info(f'VM Power Status ${status}')
        return status

    @keyword('Power ON VM ${vm}')
    def power_on(self, vm):
        """
        Will Power ON the VM if the Power status is OFF
        """
        status = self.vm_power_status(vm)
        # Power on the vm if it is off and wait result
        if status == (Power.Info(state=Power.State.POWERED_OFF)):
            self._client.vcenter.vm.Power.start(vm.vm)
            self._wait_for_power_operations_state(vm, True, STATE_TIMEOUT)
        else:
            return

    @keyword('Power OFF VM ${vm}')
    def power_off(self, vm):
        """
        Will Power OFF the VM if the Power status is ON
        """
        status = self.vm_power_status(vm)
        # Power off the vm if it is on and wait result
        if status == Power.Info(state=Power.State.POWERED_ON):
            self._client.vcenter.vm.Power.stop(vm.vm)
            self._wait_for_power_operations_state(vm, False, STATE_TIMEOUT)
        else:
            return

    @keyword('Reboot VM ${vm}')
    def reboot(self, vm):
        """
        Checks the VM Power status and if is Power OFF
        will Power ON the machine and reboot\n
        Then will wait the machine Power state
        """

        # power on the VM if necessary
        self.power_on(vm)

        # reboot the guest
        self._client.vcenter.vm.guest.Power.reboot(vm.vm)

        # wait vm power and guest power state
        self._wait_for_power_operations_state(vm, False, STATE_TIMEOUT)

        self._wait_for_guest_power_state(
            vm, GuestPower.State.RUNNING, STATE_TIMEOUT)

        self.wait_for_power_operations_state(vm, True, STATE_TIMEOUT)

    @keyword('Delete VM ${vm}')
    def delete_vm(self, vm):
        """
        Check the VM Power status and if is Power OFF
        deletes the VM

        """
        if not vm:
            raise Exception(
                'requires an existing, please create the vm first.')

        state = self.vm_power_status(vm)
        if state == Power.Info(state=Power.State.POWERED_ON):
            self._client.vcenter.vm.Power.stop(vm.vm)
        elif state == Power.Info(state=Power.State.SUSPENDED):
            self._client.vcenter.vm.Power.start(vm.vm)
            self._client.vcenter.vm.Power.stop(vm.vm)

        # deleting vm
        self._client.vcenter.VM.delete(vm.vm)

    @keyword('Create VM ${vm_name} in Folder ${folder_name} Inside Datastore ${datastore_name}')
    def create_vm(self, vm_name, folder_name, datastore_name):
        """
        Will create a VM with default config
        @return VM info
        """
        datacenter_name = 'Datacenter'
        guest_os = "CENTOS_7_64"

        placement_spec = self._get_placement_spec_for_resource_pool(
            datacenter_name,
            folder_name,
            datastore_name)

        vm_create_spec = VM.CreateSpec(name=vm_name,
                                       guest_os=guest_os,
                                       placement=placement_spec,
                                       )

        vm = self._client.vcenter.VM.create(vm_create_spec)

        vm_info = self._client.vcenter.VM.get(vm)

        logger.info(f'Created VM info: ${vm_info}')

        return vm_info

    @keyword('Create VM ${vm_name} From Template ID ${template_id} And Return IP')
    def create_vm_from_template(self, vm_name, template_id):
        """
        Create a VM from a template in the library item\n        
        Build the deploy spec to pass in the deploy proccess\n
        Power On the created VM and waits the VM Tool to be running\n
        @return: the created vm ip address.
        """

        datacenter_name = 'Datacenter'
        vm_folder_name = 'POCVMRobot'

        vmtx_service = LibraryItems(self._client.session_svc._config)

        folder_id = self._get_folder(datacenter_name, vm_folder_name)

        resource_pool_id = self._get_resource_pool(datacenter_name)

        placement_spec = vmtx_service.DeployPlacementSpec(
            folder=folder_id,
            resource_pool=resource_pool_id)

        deploy_spec = vmtx_service.DeploySpec(
            name=vm_name,
            placement=placement_spec,
            powered_on=True,
        )

        vmtx_service.deploy(template_id, deploy_spec)

        vm = self.get_vm(vm_name)

        self._wait_for_guest_power_state(
            vm, GuestPower.State.RUNNING, STATE_TIMEOUT)

        # wait for guest info to be ready
        self._wait_for_guest_info_ready(vm, STATE_TIMEOUT)

        ip = self.get_vm_ip(vm)

        return ip

    @keyword('Get Template ${name} ID')
    def get_template_id_by_name(self, name):
        """
        Uses the template name to get the template ID
        the template needs to be in the library item
        @return: the template id.
        """
        library_item_service = Item(self._client.session_svc._config)
        find_spec = Item.FindSpec(name=name)
        item_ids = library_item_service.find(find_spec)
        item_id = item_ids[0] if item_ids else None

        logger.info(f'Template ID: ${item_id}')
        return item_id

    def _get_placement_spec_for_resource_pool(self,
                                              datacenter_name,
                                              vm_folder_name,
                                              datastore_name):
        """
        Create the vm placement spec with the datastore, resource pool and vm
        folder
        """

        resource_pool = self._get_resource_pool(datacenter_name)

        folder = self._get_folder(datacenter_name, vm_folder_name)

        datastore = self._get_datastore(datacenter_name, datastore_name)

        placement_spec = VM.PlacementSpec(folder=folder,
                                          resource_pool=resource_pool,
                                          datastore=datastore)

        return placement_spec

    def _get_datastore(self, datacenter_name, datastore_name):
        """
        Returns the identifier of a datastore
        Note: The method assumes that there is only one datastore and datacenter
        with the mentioned names.
        """
        datacenter = self._get_datacenter(datacenter_name)
        if not datacenter:
            return None

        filter_spec = Datastore.FilterSpec(names=set([datastore_name]),
                                           datacenters=set([datacenter]))

        datastore_summaries = self._client.vcenter.Datastore.list(filter_spec)
        if len(datastore_summaries) > 0:
            datastore = datastore_summaries[0].datastore
            return datastore
        else:
            return None

    def _get_datacenter(self, datacenter_name):
        """
        Returns the identifier of a datacenter
        Note: The method assumes only one datacenter with the mentioned name.
        """

        filter_spec = Datacenter.FilterSpec(names=set([datacenter_name]))

        datacenter_summaries = self._client.vcenter.Datacenter.list(
            filter_spec)
        if len(datacenter_summaries) > 0:
            datacenter = datacenter_summaries[0].datacenter
            return datacenter
        else:
            return None

    def _get_folder(self, datacenter_name, folder_name):
        """
        Returns the identifier of a folder
        Note: The method assumes that there is only one folder and datacenter
        with the mentioned names.
        """
        datacenter = self._get_datacenter(datacenter_name)
        if not datacenter:
            return None

        filter_spec = Folder.FilterSpec(type=Folder.Type.VIRTUAL_MACHINE,
                                        names=set([folder_name]),
                                        datacenters=set([datacenter]))

        folder_summaries = self._client.vcenter.Folder.list(filter_spec)
        if len(folder_summaries) > 0:
            folder = folder_summaries[0].folder
            return folder
        else:
            return None

    def _get_resource_pool(self, datacenter_name, resource_pool_name=None):
        """
        Returns the identifier of the resource pool with the given name or the
        first resource pool in the datacenter if the name is not provided.
        """
        datacenter = self._get_datacenter(datacenter_name)
        if not datacenter:
            return None

        names = set([resource_pool_name]) if resource_pool_name else None
        filter_spec = ResourcePool.FilterSpec(datacenters=set([datacenter]),
                                              names=names)

        resource_pool_summaries = self._client.vcenter.ResourcePool.list(
            filter_spec)
        if len(resource_pool_summaries) > 0:
            resource_pool = resource_pool_summaries[0].resource_pool
            return resource_pool
        else:
            return None

    def _wait_for_power_operations_state(self, vm, desiredState, timeout):
        """
        Waits for the desired soft power operations state, or times out.
        """
        start = time.time()
        timeout = start + timeout
        while timeout > time.time():
            time.sleep(1)
            curState = self._client.vcenter.vm.guest.Power.get(
                vm.vm).operations_ready
            if desiredState == curState:
                break
        if desiredState != curState:
            raise Exception('Timed out waiting for guest to reach desired '
                            ' operations ready state')
        else:
            return

    def _wait_for_guest_power_state(self, vm, desiredState, timeout):
        """
        Waits for the guest to reach the desired power state, or times out.
        """
        start = time.time()
        timeout = start + timeout
        while timeout > time.time():
            time.sleep(1)
            curState = self._client.vcenter.vm.guest.Power.get(vm.vm).state
            if desiredState == curState:
                break
        if desiredState != curState:
            raise Exception(
                'Timed out waiting for guest to reach desired power state')
        else:
            return

    def _wait_for_guest_info_ready(self, vm, timeout):
        """
        Waits for the Tools info to be ready, or times out.
        """
        start = time.time()
        timeout = start + timeout
        while timeout > time.time():

            time.sleep(1)
            try:
                self._client.vcenter.vm.guest.Identity.get(vm.vm)
                break
            except ServiceUnavailable as e:
                pass
            except Exception as e:
                raise e
        if time.time() >= timeout:
            raise Exception('Timed out waiting for guest info to be available.\n'
                            'Be sure the VM has VMware Tools.')
        else:
            return


def _get_unverified_session():
    """
    Get a requests session with cert verification disabled.
    Also disable the insecure warnings message.
    Note this is not recommended in production code.
    @return: a requests session with verification disabled.
    """
    session = requests.session()
    session.verify = False
    requests.packages.urllib3.disable_warnings()
    return session
