*** Settings ***
Library     OperatingSystem


*** Variables ***
# ${VCENTER_IP}=    16.127.157.121
# ${VCENTER_USER}=    administrator@vsphere.local
# ${VCENTER_PASSWORD}=    HPE@aurora2

${VM_VM}                vm-6026
#${VM_NAME}    poc_vm_from_template_robot_ip
${VM_NAME}              poc_vm_robot_template
${TEMPLATE_REF}         secc3_sles15sp3_tpm_1

${VCENTER_IP}=          host51.br.rdlabs.hpecorp.net
${VCENTER_USER}=        admin2@vsphere.local
${VCENTER_PASSWORD}=    HPE@vmaas2

${folder_name}=         POCVMRobot
${datastore_name}=      st116_VMaaS_Disk1_Lun10
