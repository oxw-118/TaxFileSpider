import requests
import re
import pickle
import os
import jieba
import webbrowser as web
from multiprocessing import Pool
import time
import tkinter as tk
from tkinter.filedialog import askdirectory

REQUEST_URL = 'http://www.chinatax.gov.cn/n810341/n810755/index_2420064_{}.html'# 1 to Max_page
MAX_PAGE = 42


def GUI_get_save_directory():
    root = tk.Tk()
    root.withdraw()
    save_directory = askdirectory()
    root.destroy()
    return save_directory

class TaxFileSpider(object):

    def __init__(self):
        self.response = None
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36'
        self.base_url = 'http://www.chinatax.gov.cn/'
        self.url_list = []
        self.title_list = []
        self.tag_list = []
        self.result_indexs = []
        self.fobidden_search_list = ['税','的','号']    # 模糊搜索跳过的关键字,提高准确度
        self.save_directory = None
        self.urls_path = 'urls.txt'
        self.tags_path = 'tags.txt'
        self.titles_path = 'titles.txt'


    def get(self, url):
        headers = {
            'User-Agent':self.user_agent
        }
        self.response = requests.get(url=url, headers=headers)
        if self.response.status_code == 200:
            self.parse()
            print('%s ----- down'%url)
            time.sleep(3)
        else:
            print("status_code:%s  网页解析错误请稍后再试"%self.response.status_code)

    def parse(self):
        self.response.encoding = 'utf-8'
        content = self.response.text
        artical_data = re.findall('<dd>.*?href="(.*?)".*?title="(.*?)"><span.*?>(.*?)</span>'
                                  , content, re.S)
        for item in artical_data:
            self.url_list.append(self.base_url+item[0][6:])
            self.title_list.append(item[1])
            self.tag_list.append(item[2])

    # 打开浏览器访问网页
    def open_web(self, url):
        web.open_new_tab(url=url)

    def show_url_list(self):
        for url in self.url_list:
            print(url)
        print(len(self.url_list))

    def show_title_list(self):
        for title in self.title_list:
            print(title)

    def show_tag_list(self):
        for tag in self.tag_list:
            print(tag)

    def search(self, keyword):
        self.result_indexs = []
        for index, title in enumerate(self.title_list):
            if (title.find(str(keyword)) != -1 or self.tag_list[index].find(str(keyword)) != -1) and index not in self.result_indexs:
                print('文件索引: %s'%index)
                print('文件题目: %s'%title)
                print('文件标签: %s'%self.tag_list[index])
                print('来源网址: %s'%self.url_list[index])
                print(50*'-')
                self.result_indexs.append(index)

    # 模糊搜索
    def ambiguous_search(self, keyword):
        keyword_list = self.cut_for_search(keyword)
        self.result_indexs = []
        for keyword in keyword_list:
            if keyword not in self.fobidden_search_list:
                self.search(keyword)

    # 用jieba分割词,用于模糊搜索
    def cut_for_search(self, keyword):
        return [i for i in jieba.cut_for_search(keyword) if i]

    def download(self, index):
        headers = {'User-Agent':self.user_agent,
                   'Host': 'www.chinatax.gov.cn',
                   'Referer': 'http: // www.chinatax.gov.cn / n810341 / n810755 / index.html'
        }
        while index >= len(self.url_list):
            index = input('文件索引号有误,请重新输入:')
            if not index:
                return
            index = int(index)
        url = self.url_list[index]
        if not url:
            return
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            response.encoding = 'utf-8'
            try:
                title = re.findall('title.*?content="(.*?)">',response.text, re.S)[0]           # 文章题目
                pubdate = re.findall('pubdate.*?content="(.*?)">',response.text, re.S)[0]       # 发表日期
                mediaid = re.findall('mediaid.*?content="(.*?)">', response.text, re.S)[0]      # 作者
                content = re.findall('tax_content.*?<p>(.*?)</p>', response.text, re.S)[0]      # 文章内容
                if not content:
                    print('获取文章信息错误~请手动查看文章')
            except Exception as e:
                print('下载出现错误!~请手动查看文章')
                print('错误信息: %s'%repr(e))
                return
            artical_head = '题目: %s\n标签: %s\n发表时间: %s\n作者: %s\n文章来源: %s'%(title, self.tag_list[index], pubdate, mediaid, url)       # 构造文件开头
            pretty_content = self.content_prettify(content=content)
            self.save(title=title, artical_head=artical_head, content=pretty_content)
        else:
            print("网络请求异常,请手动访问网址")

    # 美化输出
    def content_prettify(self, content):
        content = content.replace('&ldquo;', '"')
        content = content.replace('&rdquo;', '"')
        content = content.replace('&mdash;', '-')
        content = content.replace('&nbsp;', ' ')
        content = content.replace('<br />', '')
        return content

    def is_exists(self, path):
        if os.path.exists(path):
            return True
        else:
            False

    def to_pickle(self, path, data):
        with open(path, 'wb') as f:
            pickle.dump(data, f)

    def read_pickle(self, path):
        with open(path, 'rb') as f:
            return pickle.load(f)

    # 默认不启用多进程加速
    def init(self, accelrate=False):
        print("正在初始化...\n")
        time1 = time.time()
        if not self.is_exists(self.titles_path) or not self.is_exists(self.urls_path) or not self.is_exists(self.tags_path):
            requests_url_list = [REQUEST_URL.format(str(i)) for i in range(1, MAX_PAGE+1)]
            if accelrate:
                pool = Pool()
                pool.map(self.get, requests_url_list)
            else:
                for url in requests_url_list:
                    self.get(url=url)
                    time.sleep(1)
            if self.response.status_code == 200:
                self.to_pickle(self.titles_path, data=self.title_list)
                self.to_pickle(self.urls_path, data=self.url_list)
                self.to_pickle(self.tags_path, data=self.tag_list)
            else:
                print('哎呀！爬虫被发现啦，请稍后再试~')
                input()
                exit()
        else:
            self.title_list = self.read_pickle(self.titles_path)
            self.url_list = self.read_pickle(self.urls_path)
            self.tag_list = self.read_pickle(self.tags_path)
        print("初始化完成!")
        print("用时: %s秒\n\n"%(time.time()-time1))

    def shell(self, command):
        command_list = command.split()
        try:
            if command_list[0] in ['?', 'help', '？']:
                print('所有指令(输入指令时用空格代替\'+\'):')
                print('           |   指令                  |                   功能   |')
                print('           |----------------------------------------------------|')
                print('           |  help/?                 |                    帮助  |')
                print('           |  a/all                  |                所有文件  |')
                print('           |  s/S+关键词             |                精确搜索  |')
                print('           |  m/M+关键词             |                模糊搜索  |')
                print('           |  o/O/open+文件索引号    |            用浏览器打开  |')
                print('           |  update/ud              |            更新本地缓存  |')
            elif command_list[0] in ['a', 'all']:
                self.show_title_list()
            elif command_list[0] in ['s', 'S']:
                self.search(keyword=command_list[1])
                print('含有关键字的文件索引号:')
                for index in self.result_indexs:
                    print(index, ',', end='')
                print()
            elif command_list[0] in ['o', 'O', 'open']:
                for i in range(1, len(command_list)):
                    self.open_web(url=self.url_list[int(command_list[i])])
            elif command_list[0] in ['m', 'M']:
                self.ambiguous_search(keyword=command_list[1])
                print('含有关键字的文件索引号:')
                for index in self.result_indexs:
                    print(index, ',', end='')
                print()
            elif command_list[0] in ['ud', 'update']:
                requests_url_list = [REQUEST_URL.format(str(i)) for i in range(1, MAX_PAGE+1)]
                for url in requests_url_list:
                    self.get(url=url)
                if self.response.status_code == 200:
                    self.to_pickle(self.titles_path, data=self.title_list)
                    self.to_pickle(self.urls_path, data=self.url_list)
                    self.to_pickle(self.tags_path, data=self.tag_list)
                else:
                    print('哎呀！爬虫被发现啦，请稍后再试~')
            else:
                print('您输入的指令有误噢~输入?或者help可以查看所有可以使用的指令')
        except:
            print('您输入的指令有误噢~输入?或者help可以查看所有可以使用的指令')


if __name__ == '__main__':
    print("因为爬虫请求网页速度很快,容易被封禁,过一段时间就好啦~\n")
    spider = TaxFileSpider()
    spider.init()
    while True:
        command = input('请输入指令>')
        if command:
            spider.shell(command=command)

