import sys
import paramiko

cmd = " ".join(sys.argv[1:])
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('103.74.92.72', username='root', password='eCTyD*R.94zTba')
stdin, stdout, stderr = client.exec_command(cmd)
print("STDOUT:")
print(stdout.read().decode())
print("STDERR:")
print(stderr.read().decode())
client.close()
