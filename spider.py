import requests
import re
import pickle
import os
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
        print('搜索结果:')
        for index, title in enumerate(self.title_list):
            if title.find(str(keyword)) != -1 or self.tag_list[index].find(str(keyword)) != -1:
                print('文件索引: %s'%index)
                print('文件题目: %s'%title)
                print('文件标签: %s'%self.tag_list[index])
                print('来源网址: %s'%self.url_list[index])
                print(50*'-')


    def download(self, index):
        headers = {'User-Agent':self.user_agent,
                   'Host': 'www.chinatax.gov.cn',
                   'Referer': 'http: // www.chinatax.gov.cn / n810341 / n810755 / index.html'
        }
        if index < len(self.url_list):
            url = self.url_list[index]
        else:
            while index >= len(self.url_list):
                index = input('文件索引号有误,请重新输入:')
                if not index:
                    return
                index = int(index)
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

    def save(self, title, artical_head, content):
        if not self.save_directory:
            self.save_directory = GUI_get_save_directory()
        save_path = self.save_directory + '/%s.txt'%title
        with open(save_path, 'w') as fw:
            try:
                fw.write(artical_head+'\n\n')
                fw.write(content)
            except:
                print('%s |下载失败!请手动访问')
                os.remove(save_path)
                return
        print('已成功保存至 %s'%save_path)

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
        print("用时: %s秒"%(time.time()-time1))

if __name__ == '__main__':
    print("因为爬虫请求网页速度很快,容易被封禁,过一段时间就好啦~\n")
    spider = TaxFileSpider()
    spider.init()
    while True:
        keyword = input('请输入文件的关键字:')
        if keyword == 'ALL':
            spider.show_title_list()
            print(25 * '#' + '快乐的分割线' + 25 * '#')
            continue
        else:
            spider.search(keyword=keyword)
        indexs = input('输入需要下载文件的索引号(多个文件以英文逗号隔开):')
        if indexs:
            if indexs.find(',') != -1:
                for index in indexs.split(','):
                    spider.download(index=int(index))
            else:
                spider.download(index=int(indexs))
        print(25*'#'+'快乐的分割线'+25*'#')
