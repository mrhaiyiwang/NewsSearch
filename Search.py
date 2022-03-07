from bs4 import BeautifulSoup
import jieba
import sys
import sqlite3
import matplotlib
import requests
import  re
import operator
import numpy
from urllib import request
import math
import tkinter
r='https://news.sina.com.cn/'
dep=2
url=''
q=[r]
coll={}
bastion=[]
time=0
class SearchEngine(object):
    def __init__(self):
        #主窗口
        self.root=tkinter.Tk()
        #主窗口标题
        self.root.title("mini search")
        self.root.geometry('800x400')
        #输入框尺寸
        self.word_in=tkinter.Entry(self.root,width=30)
        #结果列表
        self.display_info=tkinter.Text(self.root,width=60,height=50)
        #搜索按钮
        self.result_button=tkinter.Button(self.root,command=self.find_content,text="duggle一下")
    #布局
    def gui_arrange(self):
        self.word_in.pack()
        self.result_button.pack()
        self.display_info.pack()
    #搜索结果
    def find_content(self):
        self.ask=self.word_in.get()
        pagescore(self.ask)
        global contents
        self.display_info.delete('0.0', 'end')
        for item in contents:
            self.display_info.insert('end',item)
            self.display_info.insert('end', '\n')
            self.display_info.insert('end', '\n')
conn=sqlite3.connect('base.db')
c=conn.cursor()
c.execute('drop table web')
c.execute('create table web(ord int primary key,link text,total int)')
c.execute('drop table word')
c.execute('create table word(term varchar(25) primary key, list text)')
conn.commit()
conn.commit()
cou=0
while not len(q)==0 and dep>0:                                                #record the number of links
    for i in range(0,len(q)):
        url = q.pop(0)
        try:
            req=request.Request(url)
            res=request.urlopen(req)
            res=res.read().decode('utf-8')
        except:continue
        soup = BeautifulSoup(res,'lxml')
        l1=len(q)
        #爬取链接
        alinks=soup.select('a')
        for attr in alinks:
            try:
                link=attr['href']
                if "doc-"in link:
                    if link not in coll: #第一次出链
                        q.append(link)
                        coll[link]=1
                    else:               #出链次数加一
                        coll[link]+=1
                else:
                    continue
            except:continue
        # 爬取当前页面的文本，分词后建立索引（词语和出现的网站序号）

        if time != 0:#第一层没有新闻内容
            article = []
            for p in soup.select('.article p'):
                article.append(p.text.strip())
            frag=jieba.cut_for_search(" ".join(article))
            fraglist=list(frag)
            conn=sqlite3.connect("base.db")
            c=conn.cursor()
            c.execute('insert into web values(?,?,?)',(cou,url,len(fraglist)))
            for word in fraglist:
                c.execute('select list from word where term=?',(word,))
                #该词语是否已经在数据库内？
                outcome=c.fetchall()
                if len(outcome)==0:#不存在，即第一次出现
                    wordappear=str(cou)#记录词语出现的网站序号
                    c.execute('insert into word values(?,?)',(word,wordappear))
                else:#该词语已经出现在其他网站中
                    wordappear=outcome[0][0]
                    wordappear+=' '+str(cou)#在原有字符串后拼接上当前网站序号
                    c.execute('update word set list=? where term=?',(wordappear,word))
            conn.commit()
            在bastion中记录当前网站的出链
        l=len(q)-l1
        bastion.append([])
        bastion[time].append(url)
        for j in range(1,l+1):
            if (q[-j])!=url:
                bastion[time].append(q[-j])
        coll.clear()
        time+=1
        cou+=1
    dep-=1
for i in range(0,len(q)):#为最后爬取的网页建立出链
    flag=0
    for j in range(0,len(bastion)):
        if q[i] ==bastion[j][0]:
            flag=1
    if not flag:
        bastion.append([q[i]])#每次增加一个列表，表头存储未建立出链的网页
for i in range(0,len(bastion)):#为无出链的网页建立链接到所有网址的链接
    if len(bastion[i])==1:
        for j in range(0,len(bastion)):
            if j!=i:
                bastion[i].append(bastion[j][0])
m=numpy.zeros(((len(bastion)),len(bastion)))
for i in range(0, len(bastion)):
    sum=0
    for j in range(0, len(bastion)):
        if bastion[j][0]!= bastion[i][0] and bastion[j][0] in bastion[i]:
            m[i][j]=1/(len(bastion[i])-1)
            sum+=m[i][j]
S=m.transpose()
pn=numpy.ones(len(bastion))/len(bastion)
E=numpy.ones(((len(bastion)),len(bastion)))
A=0.85*S+0.15/len(bastion)*E
while 1:
    buf=numpy.matmul(A,pn)
    mo=numpy.linalg.norm(buf-pn)
    if mo<0.00001:
        break
    pn=buf

def pagescore(demand):
    global contents
    global pn
    conn = sqlite3.connect("base.db")
    c = conn.cursor()
    c.execute('select count(*)from web')
    N = c.fetchall()[0][0] + 1
    shard = jieba.cut_for_search(demand)
    rscore = {}  # 记录各网站及其相关度得分
    for word in shard:
        # 计算TF
        tf = {}  # 选中的搜索关键词在 某个页面 的 出现次数
        c.execute('select list from word where term=?', (word,))
        result = c.fetchall()
        if len(result) > 0:
            sitelist = result[0][0]
            sitelist = sitelist.split(' ')
            sitelist = [int(x) for x in sitelist]
            for site in sitelist:
                if site in tf:
                    tf[site] += 1
                else:
                    tf[site] = 1
                    # 此处的tf[site]还没有除以每个页面的总词数
                    # 计算IDF
            df = len(set(sitelist))
            idf = math.log(N / df)
            # 计算TF-IDF
            for site in tf:
                c.execute('select total from web where ord=?', (site,))
                total = c.fetchall()[0][0]
                if site in rscore:  # 该网站已经拥有得分
                    rscore[site] += idf * tf[site] / total
                else:
                    rscore[site] = idf * tf[site] / total
    for site in rscore:
        rscore[site]*=pn[site]
    scorelist = sorted(rscore.items(), key=lambda d: d[1], reverse=True)
    count = 0
    for num, score in scorelist:
        if count == 5:
            break
        c.execute('select link from web where ord=?', (num,))
        count += 1
        website = c.fetchall()[0][0]
        try:
            req = request.Request(website)
            res = request.urlopen(req)
            res = res.read().decode('utf-8')
        except:
            continue
        soup = BeautifulSoup(res, 'lxml')
        if soup.select('.main-title'):
            title = soup.select('.main-title')[0].text
        else:continue
        inside = soup.select('.article p')
        infor=['标题:']
        infor.append(title)
        infor.append('\n')
        ti=0
        for na in inside:
            if ti==0:
                ti=1
                continue
            infor.append(na.text.strip())
        infor.append('/n')
        infor = " ".join(infor)
        if len(infor) > 96:
            infor = infor[0:95] + '...'
        else:
            infor = infor+'...'
        contents.append(infor)
contents=[]
#initialize
SE=SearchEngine()
#framing
SE.gui_arrange()
#execute
tkinter.mainloop()