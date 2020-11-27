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
    os.system("pip install requests dns-dnspod tldextract six")
    os.system("sysctl -w net.core.somaxconn=10240")
    os.system("echo 'sysctl -w net.core.somaxconn=10240' >>/etc/rc.local")
    sys.path.append("/tmp/pydnspod")
    sys.path.append("/tmp/tldextract")
    import pydnspod
    import tldextract
    import json,hashlib
    from six.moves.urllib import request, parse


    class BTApi:
        # __BT_KEY = '4vKENa5oEo8ZoNBuN7Rt6QGtlgB0Bo5i'
        # __BT_PANEL = 'http://192.168.1.245:8888'

        def __init__(self, bt_panel, bt_key):
            # if bt_panel:
            self.__BT_PANEL = bt_panel
            self.__BT_KEY = bt_key

        # 取面板日志
        def get_logs(self):
            # 拼接URL地址
            url = self.__BT_PANEL + '/data?action=getData'
            # 准备POST数据
            p_data = self.__get_key_data()  # 取签名
            p_data['table'] = 'logs'
            p_data['limit'] = 10
            p_data['tojs'] = 'test'
            # 请求面板接口
            result = self.__http_post_cookie(url, p_data)
            # 解析JSON数据
            return json.loads(result)

        def __get_md5(self, s):
            m = hashlib.md5()
            m.update(s.encode('utf-8'))
            return m.hexdigest()

        # 构造带有签名的关联数组
        def __get_key_data(self):
            now_time = int(time.time())
            p_data = {
                'request_token': self.__get_md5(str(now_time) + '' + self.__get_md5(self.__BT_KEY)),
                'request_time': now_time
            }
            return p_data

        # 发送POST请求并保存Cookie
        # @url 被请求的URL地址(必需)
        # @data POST参数，可以是字符串或字典(必需)
        # return string
        def __http_post_cookie(self, url, p_data, timeout=20):
            data = parse.urlencode(p_data).encode('utf-8')
            req = request.Request(url, data)
            opener = request.build_opener()
            response = opener.open(req, timeout=timeout)
            result = response.read()
            if type(result) == bytes: result = result.decode('utf-8')
            return result

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
    os.system("service firewalld stop")
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
    os.system("docker run "
              " --network host  "
              " -v /data/site_template_dir:/data/site_template_dir -v /www/wwwroot:/www/wwwroot "
              " -d   fastsite/bt:0.3  %s" % secret)
    time.sleep(2)
    bt_container_id = _get_cmd_stdout("docker ps |grep fastsite/bt").split()[0]
    os.system("echo 'sleep 30'>> /etc/rc.local")
    os.system("echo 'docker start %s'>> /etc/rc.local" % bt_container_id)
    time.sleep(4)

    for i in range(1000):
        bt = BTApi('http://127.0.0.1:8888' , 'B3g0qV1sECiJmHAK03OCWz3fHEavbwKo')
        try:
            assert 'data' in bt.get_logs(),Exception('error')
            break
        except:
            pass
    green_print("fastsite/bt启动成功。")

    green_print("fastsite/fastsite_py开始启动")
    os.system("docker run -e NODENAME='%s' "
              "-e SECRET='%s'  --network host  "
              " -v /data/site_template_dir:/data/site_template_dir -v /www/wwwroot:/www/wwwroot "
              " -d fastsite/fastsite_py:0.3 " % (domain, secret)
              )

    bt_container_id = _get_cmd_stdout("docker ps |grep fastsite/fastsite_py").split()[0]
    os.system("echo 'sleep 30'>> /etc/rc.local")
    os.system("echo 'docker start %s'>> /etc/rc.local" % bt_container_id)
    green_print("fastsite/fastsite_py启动成功")


    green_print("完成")
    green_print("管理页面：http://%s/ , 用户名：fastsite 密码：%s" % (domain, secret))












