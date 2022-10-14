robot:
	python -m robot -L trace ./vmware_poc/vcenter_test.robot

doc:
	python -m pdoc --html ./vmware_poc/vsphere/VsphereRobot.py --force