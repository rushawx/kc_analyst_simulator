import numpy as np
import pandas as pd
import pandahouse as ph
import matplotlib.pyplot as plt
import seaborn as sns
import io
import telegram
from read_db.CH import Getch

sns.set()

def task_one(chat=None):
    #cht_id = chat or 517873898
    cht_id = chat or -1001539201117
    bot = telegram.Bot(token='5161462233:AAHsaiNpJopThhUEugZI9ziKb-bgxBwTgzY')

    df = Getch('''
    SELECT toStartOfDay(toDateTime(time)) as date,
    count(DISTINCT user_id) as dau,
    countIf(user_id, action='like') as likes,
    countIf(user_id, action='view') as views,
    (countIf(user_id, action='like') / countIf(user_id, action='view')) * 100 as ctr
    FROM simulator_20220320.feed_actions
    WHERE toStartOfDay(toDateTime(time)) >= today() - 7 and toStartOfDay(toDateTime(time)) < today()
    GROUP BY toStartOfDay(toDateTime(time))
    ORDER by toStartOfDay(toDateTime(time))
    ''').df

    txt_msg = df.iloc[-1, :].to_list()
    txt_msg = f'@rushawx\
    \nКлючевые метрики за предыдущий день, {str(txt_msg[0])[0:10]}:\
    \ndau - {txt_msg[1]},\
    \nпросмотры - {txt_msg[3]},\
    \nлайки - {txt_msg[2]},\
    \nctr - {round(txt_msg[4], 4)}.'

    metrics_report = io.BytesIO()
    metrics_report.name = 'metrics_report.png'
    fig, axs = plt.subplots(nrows=3, figsize=(16,8), sharex=True)
    fig.suptitle(f'Metrics for a week from {str(df["date"].to_list()[0])[0:10]} to {str(df["date"].to_list()[-1])[0:10]}', fontsize=12)
    sns.lineplot(x='date', y='dau', data=df, ax=axs[0], label='dau', color='g')
    axs[0].set(xlabel='dau', title='DAU')
    sns.lineplot(x='date', y='views', data=df, ax=axs[1], label='views', color='b')
    sns.lineplot(x='date', y='likes', data=df, ax=axs[1], label='likes', color='m')
    axs[1].set(xlabel='count', title='Views & Likes')
    sns.lineplot(x='date', y='ctr', data=df, ax=axs[2], label='ctr', color='r')
    axs[2].set(title='CTR')
    plt.tight_layout()
    plt.savefig(metrics_report)

    bot.sendMessage(chat_id=cht_id, text=txt_msg)
    metrics_report.seek(0)
    bot.sendPhoto(chat_id=cht_id, photo=metrics_report)

try:
    task_one()
except Exception as e:
    print(e)
