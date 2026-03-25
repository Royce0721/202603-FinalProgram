# choice() 方法返回一个列表、元组或是字符串的随机项
from random import choice
# 在公共库中已经定义了服务访问基类，如果有所遗忘，可以查看“开发公共库”的阶段
from tblib.service import Service


class TbUser(Service):
    @property
    def base_url(self):
        # 事实上在项目中本来就只有一个地址，就不存在随机选择，如果配置多个地址就可以随机挑选
        return choice(self.app.config['SERVICE_TBUSER']['addresses'])
