import math
import queue
import threading
from dearpygui.core import *
from dearpygui.simple import *

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from selenium.common.exceptions import NoSuchElementException, TimeoutException

global msg_arr, sum_str
global que, url_count, success_count, fail_count
url_count = success_count = fail_count = 0
sum_str = '总数：{}  / 成功：{}  / 失败：{}  '
que = queue.Queue()
msg_arr = []
# 转存文件夹
targ_dir = "我的资源"
# 浏览器驱动地址（驱动放在浏览器执行文件目录里）
driver_path = "D:\Program Files\Google\Chrome\Application\chromedriver86.exe"
# 主号
cookie_str = ''


# 通过文件获取百度网盘分享链接
def getUrls(file_path, d='----'):
    urls = []
    u_arr = []
    with open(file_path, 'r+') as file:
        temp_urls = file.readlines()
    for url in temp_urls:
        url_pwd = url.split(d)
        urls.append({'url': url_pwd[0], 'pwd': url_pwd[1].replace('\n', ''), 'status': '未操作'})
        u_arr.append([url_pwd[0], url_pwd[1].replace('\n', ''), '', '未操作'])
    return urls, u_arr


# 格式化cokie
def cookieFormant(cookie_str):
    a = cookie_str.split('; ')
    cookie_arr = []
    for i in a:
        b = {}
        n = i.split('=')
        b['name'] = n[0]
        try:
            b['value'] = n[1]
        except:
            b['value'] = ''
        cookie_arr.append(b)
    return cookie_arr


# 批量转存
def batchFileToMypan(urls_dict, cookie_dict, driver_path):
    print("启动")
    opt = webdriver.ChromeOptions()
    # 关闭浏览器界面
    opt.headless = True
    driver = webdriver.Chrome(executable_path=driver_path, options=opt)
    driver.get("https://pan.baidu.com")
    # 批量访问
    for url_dict in urls_dict:
        result = toMyPan(driver=driver, url_dict=url_dict, cookie_dict=cookie_dict)
        msg_arr.append(result)
        que.put(result)


# 转存流程
def toMyPan(driver, url_dict, cookie_dict):
    msg_obj = {
        'url': url_dict['url'],
        'pwd': url_dict['pwd'],
        'file': '',
        'status': '',
    }
    # 百度网盘输入密码界面，如果带登录cookie，就进不去
    driver.delete_all_cookies()
    driver.get(url_dict['url'])

    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="submitBtn"]/a')), "页面失效")
        # 输入提取码
        driver.find_element_by_id('accessCode').send_keys(url_dict['pwd'])
        # 提交提取码
        driver.find_element_by_xpath('//*[@id="submitBtn"]/a').click()
        # 等待进入文件界面
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="shareqr"]/div[2]/div[2]/div/ul[1]/li[1]/div/span[1]')), '密码错误')
        # 设置cookie
        for c in cookie_dict:
            driver.add_cookie(cookie_dict=c)
        driver.get(url_dict['url'])
        # 等待页面加载完成
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="shareqr"]/div[2]/div[2]/div/ul[1]/li[1]/div/span[1]')
            )
        )
        # 获取文件名
        files = driver.find_elements_by_css_selector(".file-name")
        files_str = ''
        for i in range(1, len(files)):
            files_str += files[i].text + "、"
        msg_obj['file'] = files_str
        # 进入内容页面，点击保存
        # 打钩所有分享文件
        driver.find_element_by_xpath('//*[@id="shareqr"]/div[2]/div[2]/div/ul[1]/li[1]/div/span[1]').click()
        # 点击保存按钮
        driver.find_element_by_xpath('//*[@id="bd-main"]/div/div[1]/div/div[2]/div/div/div[2]/a[1]').click()
        # 等待选择文件夹加载完成
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="fileTreeDialog"]/div[2]/div/ul/li/ul/li')))
        # 选中要保存的文件夹
        lis = driver.find_elements_by_xpath('//*[@id="fileTreeDialog"]/div[2]/div/ul/li/ul/li')
        for li in lis:
            if li.text == targ_dir:
                li.click()
        # 确认保存
        driver.find_element_by_css_selector('.g-button.g-button-blue-large').click()
        '//*[@id="fileTreeDialog"]/div[4]/a[2]'

        if WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="emptyDialogId"]/div/div[2]/div[1]')), '网络异常/空间不足/数据异常（进黑名单）').text == '保存成功':
            msg_obj['status'] = '保存成功'
            return msg_obj
    except NoSuchElementException:
        msg_obj['status'] = '链接失效或发生其他错误'
        return msg_obj
    except TimeoutException as timeExcept:
        msg_obj['status'] = str(timeExcept)
        return msg_obj


# 开始按钮被点击，获取信息
def clickmy():
    global url_count, success_count, fail_count
    urls_dict, table_urls = getUrls(get_value("filepath"), d=get_value("d"))
    for data in table_urls:
        add_row("dataTable", data)
    url_count = len(table_urls)
    set_value("urls_status", sum_str.format(url_count, success_count, fail_count))
    # 格式化cookie
    cookie_dict = cookieFormant(get_value("baiducookie"))
    global targ_dir
    targ_dir = get_value("targ_dir")
    driver_path = get_value("driver_path")
    # 线程数
    n = get_value("thnum")

    urls_arr = [urls_dict[i:i + math.ceil(len(urls_dict) / n)] for i in
                range(0, len(urls_dict), math.ceil(len(urls_dict) / n))]
    print(targ_dir, cookie_dict, n)
    threads = []

    for i in range(n):
        t1 = threading.Thread(target=batchFileToMypan, args=(urls_arr[i], cookie_dict, driver_path,))
        threads.append(t1)
    for t in threads:
        t.start()


# 主窗口
def openWindow():
    with window("Tutorial"):
        add_additional_font("static/NotoSerifCJKjp-Medium.otf", 20, "chinese_simplified_common")
        add_spacing(count=5)

        add_input_text(name="driver_path", default_value="（驱动放在浏览器执行文件目录里）", label="浏览器驱动地址", )
        add_spacing(count=5)
        add_input_text(name="filepath", default_value="输入文件地址，不要有中文", label="文件地址", )
        # add_input_text(name="filepath",default_value="data.txt",label="文件地址",)

        add_spacing(count=5)

        add_input_text(name="targ_dir", default_value="我的资源", label="储存的文件夹", )
        add_spacing(count=5)

        add_input_text(name="d", default_value="----", label="分隔符")
        add_spacing(count=5)

        add_input_int(name="thnum", default_value=5, label="线程数", min_value=1, max_value=10)
        add_spacing(count=5)

        add_input_text(name="baiducookie", default_value="百度网盘cookie", label="百度cookie")
        # add_input_text(name="baiducookie", default_value=cookie_str)
        add_button("开始", callback=clickmy)
        add_spacing(count=5)
        add_text("urls_status", default_value=sum_str.format(0, 0, 0))
        add_spacing(count=5)
        add_table("dataTable", ["链接", "提取码", "文件名", "状态"], height=500)

    start_dearpygui(primary_window="Tutorial")


# 设置url状态
def check():
    global success_count, fail_count, url_count
    while 1:
        if que.qsize() > 0:
            msg = que.get()
            table_data = get_table_data("dataTable")
            for i in range(0, len(table_data)):
                if table_data[i][0] == msg["url"]:
                    set_table_item("dataTable", i, 2, msg['file'])
                    set_table_item("dataTable", i, 3, msg['status'])
            if msg['status'] == '保存成功':
                success_count += 1
                set_value("urls_status", sum_str.format(url_count, success_count, fail_count))
            else:
                fail_count += 1
                set_value("urls_status", sum_str.format(url_count, success_count, fail_count))
            print("获取消息：", msg)


if __name__ == '__main__':
    tt = threading.Thread(target=check)
    tt.start()
    # 开启窗口
    openWindow()
