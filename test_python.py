__author__ = 'Alexey'

print "NEW Hello World!!!"

# import paramiko
#
# host = 'poisknomera.ru'
# user = 'ec2-user'
# port = 22
# key_file='D:\\Documents\\Dropbox\\Backup\\AWS2013.pem'
#
# client = paramiko.SSHClient()
# client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
# client.connect(hostname=host, username=user, port=port, key_filename=key_file)
# stdin, stdout, stderr = client.exec_command('ls -l')
# data = stdout.read() + stderr.read()
# transport = client.get_transport()#.open_session()
#
# sftp = paramiko.SFTPClient.from_transport(transport)
# remotepath = './file.py'
# localpath = 'D:\\Projects\\ec2_tools\\test_ec2.py'
#
# # sftp.get(remotepath, localpath)
# sftp.put(localpath, remotepath)
#
# sftp.close()
# transport.close()
# client.close()
