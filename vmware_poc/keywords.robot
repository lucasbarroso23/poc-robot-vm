*** Settings ***
Library     ./vsphere/VsphereRobot.py
Resource    variables.robot


*** Keywords ***
 Get VM reference and Set as Suite Variable
    ${VM_REF}=    Get Vm ${VM_NAME} Info
    Set Suite Variable    $VM    ${VM_REF}
    Should Not Be Empty    len('${VM}')

 Get Template ID Set as Suite Variable
    ${id}=    Get Template ${TEMPLATE_REF} ID
    Set Suite Variable    $TEMPLATE_ID    ${id}
    Should Not Be Empty    len('${id}')
