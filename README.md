# nitor-audit

Client for a workstation security auditing setup where certain security data is continously
uploaded to a central server. Requires an sftp server and rest endpoint that receives
authenticated users and creates sftp access for a ssh public key.

## Init
Init flow is the folliwng:
![init flow](nitor-audit-init-flow.png)