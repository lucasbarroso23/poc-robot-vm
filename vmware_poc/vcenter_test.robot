*** Settings ***
Documentation
...                 Test app to use the pysphere functions
...                 The idea is connect to a vcenter and
...                 manipulate some VM using this lib
...                 from this we add the funcionalities that
...                 we need

Library             ./vsphere/VsphereRobot.py
Resource            variables.robot
Resource            keywords.robot

Suite Setup         Connect to Vsphere NewSession to host ${VCENTER_IP} with user ${VCENTER_USER} and password ${VCENTER_PASSWORD}


*** Test Cases ***
Test Create A VM From Template And Wait For The IP Address
    [Documentation]    Tries to create a VM from a template inside
    ...    the library item in the Vcenter using the template ID
    ...    and create the VM then power ON the vm and waits
    ...    the VmTools status to be running so it can get the VM IP address
    When Get Template ID Set as Suite Variable
    Then Create VM ${VM_NAME} From Template ID ${TEMPLATE_ID} And Return IP

Test Install Platform Agent in VM
    [Documentation]    Tries to install the Platform Agent on the VM
    ...    and check if is properly installed
    [Tags]    not implemented
    SKIP    not implemented

Test Perform Attestation And Get Result
    [Documentation]    Tries to perform attestation and get the result
    [Tags]    not implemented
    SKIP    not implemented

Test Get a VM by Name and Log the VM Info
    [Documentation]    Tries to get the vm reference using the vm name
    ...    checks if the the VM reference exists
    ...    then we use the vm reference to get the vm bios uuid,
    ...    the vm ip address and the power state
    When Get VM reference and Set as Suite Variable
    Then Get VM ${VM} BiosUUID
    And Get VM ${VM} IP
    And Get VM ${VM} Power Status

Test Delete VM
    [Documentation]    Tries to delete a VM
    ...    if the VM is powered ON will Power OFF
    ...    before deleting
    When Get VM reference and Set as Suite Variable
    Then Delete VM ${VM}
