# coding:utf-8
__author__ = "zhou"
# create by zhou on 2020/11/20
import os
try:
    import configparser
except Exception:
    import ConfigParser as configparser
import sys
import subprocess
import time


def _get_cmd_stdout(cmd):
    d = dict(os.environ)
    #d["PYTHONIOENCODING"] = "utf-8"
    #d["LANG"] = "en_US.UTF-8"
    _pen = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,env=d)
    _pen.wait()
    _stdout = _pen.stdout.read()
    return _stdout


def green_print(*msg):
    for _ in msg:
        print('\033[92m%s \033[0m' % _)
    print('')


def red_print(*msg):
    for _ in msg:
        print('\033[91m%s \033[0m' % _)
    print('')


def yellow_print(*msg):
    for _ in msg:
        print('\033[93m%s \033[0m' % _)
    print('')


if __name__ == '__main__':
    os.system("yum install -y epel-release")
    os.system("yum install -y htop net-tools vim")
    os.system("yum install -y git python-setuptools")
    os.system("easy_install pip")
    os.system("pip install pip --upgrade")
    os.system("pip install requests dns-dnspod tldextract")
    sys.path.append("/tmp/pydnspod")
    sys.path.append("/tmp/tldextract")
    import pydnspod
    import tldextract
    os.system("mkdir -p /data/docker")
    os.system("mkdir -p /data/site_template_dir")
    os.system("yum install -y  vim docker")
    green_print("docker 安装成功")
    os.system("rm -rf /var/lib/docker")
    with open("/etc/docker/daemon.json", "w") as f:
        content = '''{
         "graph":"/data/docker",
    "bip": "10.254.254.1/24"
 }'''
        f.write(content)
    os.system("service docker restart")
    os.system("chkconfig docker on")
    os.system("service firewalld start")
    os.system("docker network create --subnet=10.254.253.1/24  fastsite")
    green_print("开始拉取 fastsite/bt fastsite/fastsite_py 镜像")
    os.system("docker pull fastsite/bt:0.3")
    os.system("docker pull fastsite/fastsite_py:0.3")
    green_print("docker 镜像拉取成功")

    if os.path.exists("/etc/fastsite.ini"):
        _ = configparser.ConfigParser()
        _.read("/etc/fastsite.ini")
        buff = dict()
        for s in _.sections():
            buff[s] = {}
            for info in _.items(s):
                buff[s][info[0]] = info[1]
        _config_dict = buff.get("fastsite")
        if not _config_dict:
            raise Exception('配置文件格式有误')

        secret = _config_dict.get('secret', '')
        if not secret or len(secret) <=7:
            raise Exception('secret 配置有误')
        ip  = _config_dict.get("ip", '')
        if not ip:
            raise Exception('ip配置有误')
        domain = _config_dict.get('domain', '')
        if not domain:
            raise Exception('domain配置有误')
        domain_dnspod_id = _config_dict.get('domain_dnspod_id', '')
        if not domain_dnspod_id:
            raise Exception('domain_dnspod_id配置有误')
        domain_dnspod_key = _config_dict.get('domain_dnspod_key', '')
        if not domain_dnspod_key:
            raise Exception('domain_dnspod_key配置有误')
        try:
            dp = pydnspod.connect(domain_dnspod_id, domain_dnspod_key)
            _ = tldextract.extract(domain)
            main_d = _.domain + '.' + _.suffix
            main_sub = _.subdomain
            print(domain, main_d, main_sub)
            old_info = dp.record.list(main_d)["records"]
            old_info = [i['name'] for i in old_info]
            if main_sub in old_info :
                raise Exception('%s记录已经存在！'% main_sub)
            if  "*." + main_sub in old_info:
                raise Exception('*.%s记录已经存在！' % main_sub)
            dp.record.add(main_d,main_sub, 'A', ip)
            dp.record.add(main_d, "*." + main_sub, 'A', ip)

        except Exception as e:
            print(str(e))
            red_print("domain domain_dnspod_id domain_dnspod_key配置有误，"
                      "无法自动完成DNS记录添加")
            sys.exit(0)
        else:
            green_print("已自动添加DNS记录 %s -- > %s" % (domain, ip))
            green_print("已自动添加DNS记录 *.%s -- > %s" % (domain, ip))

    else:
        red_print("Error!")
        red_print("/etc/fastsite.ini配置文件不存在！ 请先配置。")
        sys.exit(-1)
    green_print("fastsite/bt开始启动...")
    os.system("mkdir -p /www/wwwroot")
    os.system("docker run -p 8888:8888 -p 8889:8889 -p 443:443 -p 80:80 "
              " -p 21:21  --network fastsite --ip 10.254.253.2 "
              " -v /data/site_template_dir:/data/site_template_dir -v /www/wwwroot:/www/wwwroot "
              " -d   fastsite/bt:0.3  %s" % secret)
    time.sleep(2)
    bt_container_id = _get_cmd_stdout("docker ps |grep fastsite/bt").split()[0]
    os.system("echo 'sleep 30'>> /etc/rc.local")
    os.system("echo 'docker start %s'>> /etc/rc.local" % bt_container_id)
    green_print("fastsite/bt启动成功。")
    time.sleep(5)
    green_print("fastsite/fastsite_py开始启动")
    os.system("docker run -p 8887:8887 -e NODENAME='%s' "
              "-e SECRET='%s'  --network fastsite  "
              " --ip  10.254.253.3   "
              " -v /data/site_template_dir:/data/site_template_dir -v /www/wwwroot:/www/wwwroot "
              "--sysctl net.core.somaxconn=10240  -d "
              "fastsite/fastsite_py:0.3 " % (domain, secret))

    bt_container_id = _get_cmd_stdout("docker ps |grep fastsite/bt").split()[0]
    os.system("echo 'sleep 30'>> /etc/rc.local")
    os.system("echo 'docker start %s'>> /etc/rc.local" % bt_container_id)
    green_print("fastsite/fastsite_py启动成功")
    os.system("firewall-cmd --zone=public --add-port=80/tcp --permanent")
    os.system("firewall-cmd --zone=public --add-port=443/tcp --permanent")
    os.system("firewall-cmd --zone=public --add-port=21/tcp --permanent")
    os.system("firewall-cmd --zone=public --add-port=8888/tcp --permanent")
    os.system("firewall-cmd --zone=public --add-port=8889/tcp --permanent")
    # 对ftp所需的端口进行转发
    _buff = []
    for i in range(39000, 40001):
        _buff.append(i)
        if len(_buff) >= 103 or _buff[-1] == 40000:
            cmd = "firewall-cmd  --permanent  " + "  ".join(
                ['--add-forward-port=port=%s:proto=tcp:toport=%s:toaddr=10.254.253.2' %
                 (j, j) for j in _buff])
            _buff = []
            os.system(cmd)
    os.system("service firewalld reload")
    green_print("完成")
    green_print("管理页面：http://%s/ , 用户名：fastsite 密码：%s" % (domain, secret))












