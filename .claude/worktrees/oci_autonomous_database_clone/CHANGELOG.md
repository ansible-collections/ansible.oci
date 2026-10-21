# Oracle OCI Collection Release Notes

**Topics**

- <a href="#v1-1-0">v1\.1\.0</a>
    - <a href="#release-summary">Release Summary</a>
    - <a href="#minor-changes">Minor Changes</a>
    - <a href="#new-modules">New Modules</a>
- <a href="#v1-0-0">v1\.0\.0</a>
    - <a href="#release-summary-1">Release Summary</a>
    - <a href="#new-modules-1">New Modules</a>

<a id="v1-1-0"></a>
## v1\.1\.0

<a id="release-summary"></a>
### Release Summary

Release summary for v1\.1\.0

<a id="minor-changes"></a>
### Minor Changes

* oci\_blockstorage\_volume \- add create\-time source\_details to restore from a volume backup or clone from an existing volume\.
* oci\_vnic\_attachment \- add secondary VNIC attachment lifecycle management\.
* oci\_vnic\_attachment\_info \- add VNIC attachment retrieval and listing\.

<a id="new-modules"></a>
### New Modules

* ansible\.oci\.oci\_bastion \- Manage a Bastion resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_bastion\_info \- Retrieve bastion information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_boot\_volume \- Manage a boot volume resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_identity\_compartment \- Manage OCI compartments\.
* ansible\.oci\.oci\_identity\_compartment\_info \- Retrieve OCI compartment information\.
* ansible\.oci\.oci\_identity\_domain \- Manage OCI identity domains\.
* ansible\.oci\.oci\_identity\_domain\_info \- Retrieve OCI identity domain information\.
* ansible\.oci\.oci\_identity\_group \- Manage a group in an OCI IAM identity domain\.
* ansible\.oci\.oci\_identity\_group\_info \- Retrieve groups from an OCI IAM identity domain\.
* ansible\.oci\.oci\_identity\_user \- Manage a user in an OCI IAM identity domain\.
* ansible\.oci\.oci\_identity\_user\_group\_membership \- Manage a user group membership in an OCI IAM identity domain\.
* ansible\.oci\.oci\_identity\_user\_group\_membership\_info \- Retrieve user group memberships from an OCI IAM identity domain\.
* ansible\.oci\.oci\_identity\_user\_info \- Retrieve users from an OCI IAM identity domain\.
* ansible\.oci\.oci\_network\_private\_ip \- Manage a Private IP resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_public\_ip \- Manage a Public IP resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_object\_lifecycle\_policy \- Manage an Object Storage bucket lifecycle policy\.
* ansible\.oci\.oci\_object\_lifecycle\_policy\_info \- Get an Object Storage bucket lifecycle policy from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_object\_storage\_bucket \- Manage an Object Storage bucket in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_object\_storage\_bucket\_info \- Retrieve Object Storage bucket information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_object\_storage\_object \- Upload\, download\, or delete an Object Storage object\.
* ansible\.oci\.oci\_object\_storage\_object\_info \- Retrieve Object Storage object information\.
* ansible\.oci\.oci\_vnic\_attachment \- Manage a VNIC attachment resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_vnic\_attachment\_info \- Retrieve VNIC attachment information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_volume\_backup\_policy \- Manage a volume backup policy in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_volume\_backup\_policy\_assignment \- Manage an OCI volume backup policy assignment\.
* ansible\.oci\.oci\_volume\_backup\_policy\_assignment\_info \- Retrieve an OCI volume backup policy assignment\.
* ansible\.oci\.oci\_volume\_backup\_policy\_info \- Retrieve volume backup policy information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_volume\_group\_backup \- Manage a volume group backup resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_volume\_group\_backup\_info \- Retrieve volume group backup information from Oracle Cloud Infrastructure\.

<a id="v1-0-0"></a>
## v1\.0\.0

<a id="release-summary-1"></a>
### Release Summary

Release summary for v1\.0\.0

<a id="new-modules-1"></a>
### New Modules

* ansible\.oci\.oci\_availability\_domain\_info \- Retrieve Availability Domain information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_blockstorage\_volume \- Manage a block volume resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_blockstorage\_volume\_info \- Retrieve block volume information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_boot\_volume\_backup \- Manage a boot volume backup resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_boot\_volume\_backup\_info \- Retrieve boot volume backup information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_boot\_volume\_info \- Retrieve boot volume information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_image \- Manage a custom Compute image resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_image\_info \- Retrieve Compute image information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_instance \- Manage a Compute instance resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_instance\_console\_connection \- Manage a Compute instance console connection resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_instance\_console\_connection\_info \- Retrieve Compute instance console connection information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_instance\_info \- Retrieve Compute instance information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_dhcp\_options \- Manage a DHCP Options resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_dhcp\_options\_info \- Retrieve DHCP Options information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_drg \- Manage a Dynamic Routing Gateway \(DRG\) resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_drg\_attachment \- Manage a DRG attachment resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_drg\_attachment\_info \- Retrieve DRG attachment information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_drg\_info \- Retrieve Dynamic Routing Gateway \(DRG\) information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_internet\_gateway \- Manage an Internet Gateway resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_internet\_gateway\_info \- Retrieve Internet Gateway information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_local\_peering\_gateway \- Manage a Local Peering Gateway resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_local\_peering\_gateway\_info \- Retrieve Local Peering Gateway information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_nat\_gateway \- Manage a NAT Gateway resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_nat\_gateway\_info \- Retrieve NAT Gateway information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_route\_table \- Manage a Route Table resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_route\_table\_info \- Retrieve Route Table information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_security\_list \- Manage a Security List resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_security\_list\_info \- Retrieve Security List information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_service\_gateway \- Manage a Service Gateway resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_service\_gateway\_info \- Retrieve Service Gateway information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_subnet \- Manage a Subnet resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_subnet\_info \- Retrieve Subnet information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_vcn \- Manage a Virtual Cloud Network resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_network\_vcn\_info \- Retrieve Virtual Cloud Network information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_shape\_info \- Retrieve Compute shape information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_volume\_attachment \- Manage a block volume attachment resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_volume\_attachment\_info \- Retrieve block volume attachment information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_volume\_backup \- Manage a block volume backup resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_volume\_backup\_info \- Retrieve block volume backup information from Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_volume\_group \- Manage a volume group resource in Oracle Cloud Infrastructure\.
* ansible\.oci\.oci\_volume\_group\_info \- Retrieve volume group information from Oracle Cloud Infrastructure\.
