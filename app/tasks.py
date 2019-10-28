import requests, json
from apscheduler.schedulers.background import BackgroundScheduler
from config import Config
from app import redis
import asyncio, aiohttp
from datetime import datetime
from app import redis


async def async_get_response(key, url, res):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            assert resp.status == 200
            res[key] = await resp.json()


def get_access_token():
    url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s' % (
        Config.APPID, Config.APPSECRET)
    js = json.loads(requests.get(url=url).text)
    if js.get('access_token'):
        # 在Redis中存贮access_token，过期时间设置为7200s
        redis.set('access_token', js.get('access_token'), ex=7200)
        print('get access_token success')


def schedule():  # 默认间隔设置为7200秒
    get_access_token()
    scheduler = BackgroundScheduler()
    scheduler.add_job(get_access_token, 'interval', seconds=7200)
    scheduler.add_job(post, 'cron', hour=8, minute=00)
    scheduler.start()


def post():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    tasks = list()
    res = dict()

    # 天气
    tasks.append(async_get_response(key='her_weather',
                                    url=Config.WEATHER_URL.format('weather', 'now', 'location=' + Config.HER_LOCATION),
                                    res=res))
    tasks.append(async_get_response(key='her_forecast', url=Config.WEATHER_URL.format('weather', 'forecast',
                                                                                      'location=' + Config.HER_LOCATION),
                                    res=res))
    tasks.append(async_get_response(key='her_life', url=Config.WEATHER_URL.format('weather', 'lifestyle',
                                                                                  'location=' + Config.HER_LOCATION),
                                    res=res))
    tasks.append(async_get_response(key='her_air',
                                    url=Config.WEATHER_URL.format('air', 'now', 'location=' + Config.HER_LOCATION),
                                    res=res))
    tasks.append(async_get_response(key='my_weather',
                                    url=Config.WEATHER_URL.format('weather', 'now', 'location=' + Config.MY_LOCATION),
                                    res=res))
    tasks.append(async_get_response(key='my_forecast', url=Config.WEATHER_URL.format('weather', 'forecast',
                                                                                     'location=' + Config.MY_LOCATION),
                                    res=res))
    tasks.append(async_get_response(key='my_life', url=Config.WEATHER_URL.format('weather', 'lifestyle',
                                                                                 'location=' + Config.MY_LOCATION),
                                    res=res))
    tasks.append(async_get_response(key='my_air',
                                    url=Config.WEATHER_URL.format('air', 'now', 'location=' + Config.MY_LOCATION),
                                    res=res))
    # 每日一言
    yy = requests.get(Config.DAILY_YY).text

    loop.run_until_complete(asyncio.wait(tasks))

    # 给女朋友发消息
    weather = res['her_weather']['HeWeather6'][0]['now']
    forecast = res['her_forecast']['HeWeather6'][0]['daily_forecast'][0]
    air = res['her_air']['HeWeather6'][0]['air_now_city']
    lifestyle = res['her_life']['HeWeather6'][0]['lifestyle']
    w_description = '当前天气{0},{1}摄氏度,风向{2},风力{3}级,今日天气{4},{5}~{6}摄氏度,降雨概率{7}%'.format(weather['cond_txt'],
                                                                                     weather['tmp'],
                                                                                     weather['wind_dir'],
                                                                                     weather['wind_sc'],
                                                                                     forecast['cond_txt_d'],
                                                                                     forecast['tmp_min'],
                                                                                     forecast['tmp_max'],
                                                                                     forecast['pop'])
    a_description = '空气质量{0},空气质量指数{1},pm2.5指数{2},pm10指数{3},主要污染物{4}'.format(air['qlty'],
                                                                             air['aqi'],
                                                                             air['pm25'],
                                                                             air['pm10'],
                                                                             air['main'])
    l_description = str(lifestyle[0]['txt']).replace('您', '你')
    a_time = datetime.strptime(Config.ANNIVERSARY, '%Y-%m-%d')
    e_time = datetime.strptime(Config.EXPECTED_DAY, '%Y-%m-%d')
    a_days = (datetime.now() - a_time).days
    e_days = (e_time - datetime.now()).days

    her_template = {
        'touser': Config.HER_OPENID,
        'template_id': Config.TEMPLATE,
        'data': {
            'first': {
                'value': '早安呀宝宝，这是我们在一起的第{0}天！'.format(a_days),
                'color': '#173177'
            },
            'weather': {
                'value': w_description,
                'color': '#173177'
            },
            'air': {
                'value': a_description,
                'color': '#173177'
            },
            'lifestyle': {
                'value': l_description,
                'color': '#173177'
            },
            'next': {
                'value': ('还有' + str(e_days) + '天') if e_days >= 0 else '还有0天',
                'color': '#173177'
            },
            'remark': {
                'value': yy,
                'color': '#173177'
            }
        }
    }
    response = requests.post(Config.POST_URL.format(redis.get('access_token')), data=json.dumps(her_template))

    # 给自己发消息
    weather = res['my_weather']['HeWeather6'][0]['now']
    forecast = res['my_forecast']['HeWeather6'][0]['daily_forecast'][0]
    air = res['my_air']['HeWeather6'][0]['air_now_city']
    lifestyle = res['my_life']['HeWeather6'][0]['lifestyle']
    w_description = '当前天气{0},{1}摄氏度,风向{2},风力{3}级,今日天气{4},{5}~{6}摄氏度,降雨概率{7}%'.format(weather['cond_txt'],
                                                                                     weather['tmp'],
                                                                                     weather['wind_dir'],
                                                                                     weather['wind_sc'],
                                                                                     forecast['cond_txt_d'],
                                                                                     forecast['tmp_min'],
                                                                                     forecast['tmp_max'],
                                                                                     forecast['pop'])
    a_description = '空气质量{0},空气质量指数{1},pm2.5指数{2},pm10指数{3},主要污染物{4}'.format(air['qlty'],
                                                                             air['aqi'],
                                                                             air['pm25'],
                                                                             air['pm10'],
                                                                             air['main'])
    l_description = str(lifestyle[0]['txt']).replace('您', '你')
    my_template = {
        'touser': Config.MY_OPENID,
        'template_id': Config.TEMPLATE,
        'data': {
            'first': {
                'value': '早安,这是和宝宝在一起的第{0}天！'.format(a_days),
                'color': '#173177'
            },
            'weather': {
                'value': w_description,
                'color': '#173177'
            },
            'air': {
                'value': a_description,
                'color': '#173177'
            },
            'lifestyle': {
                'value': l_description,
                'color': '#173177'
            },
            'next': {
                'value': ('还有' + str(e_days) + '天') if e_days >= 0 else '还有0天',
                'color': '#173177'
            },
            'remark': {
                'value': yy,
                'color': '#173177'
            }
        }
    }

    response = requests.post(Config.POST_URL.format(redis.get('access_token')), data=json.dumps(my_template))


if __name__ == '__main__':
    post()
