import numpy as np
import pandas as pd
import pandahouse as ph

import matplotlib.pyplot as plt
import seaborn as sns
sns.set()

import io
import telegram

def txt_cmpr(df, metric=None, col=None):
    td_dt = str(df.iloc[-1,].to_list()[0])[0:10]
    td_vl = df.iloc[-1,].to_list()[1]
    pr_dt = str(df.iloc[0,].to_list()[0])[0:10]
    pr_vl = df.iloc[0,].to_list()[1]
    avg_vl = df[col].mean()

    pr_cmpr = 'больше' if td_vl > pr_vl else 'меньше'
    avg_cmpr = 'больше' if td_vl > avg_vl else 'меньше'

    txt_msg = f'{metric} за {td_dt} составило {round(td_vl, 1)}\
    \nЧто на {round((td_vl / pr_vl - 1) * 100, 2)}% {pr_cmpr}, чем неделей ранее {pr_dt}\
    \nА также на {round((td_vl / avg_vl - 1) * 100, 2)}% {avg_cmpr}, чем в среднем за неделю с {td_dt} по {pr_dt}'

    return txt_msg

def task_two(chat=None):
    #cht_id = chat or 517873898
    cht_id = chat or -1001539201117
    bot = telegram.Bot(token='5161462233:AAHsaiNpJopThhUEugZI9ziKb-bgxBwTgzY')
    
    connection = {'host': 'https://clickhouse.lab.karpov.courses/',
    'database':'simulator_20220320',
    'user':'student', 
    'password':'dpo_python_2020'
    }
    
    #dau_messages
    query = '''
    select
    toStartOfDay(time) as date,
    count(distinct user_id) as dau
    from simulator_20220320.message_actions
    where toStartOfDay(time) between today() - 7 and yesterday()
    group by toStartOfDay(time)
    order by toStartOfDay(time)
    '''
    dau_messages = ph.read_clickhouse(query, connection=connection)
    
    bot.sendMessage(chat_id=cht_id, text=txt_cmpr(dau_messages, metric='Количество уникальных пользователей сообщений', col='dau'))
    
    report_dau_messages = io.BytesIO()
    report_dau_messages.name = 'report_dau_messages.png'
    fig, axs = plt.subplots(figsize=(16,8))
    sns.lineplot(x='date', y='dau', data=dau_messages, ax=axs, label='dau', color='g')
    axs.set(xlabel='dau', title='DAU. Messages')
    plt.tight_layout()
    plt.savefig(report_dau_messages)
    report_dau_messages.seek(0)
    bot.sendPhoto(chat_id=cht_id, photo=report_dau_messages)
    
    #average_messages
    query = '''
    select
    toStartOfDay(time) as date,
    count(user_id) / count(distinct user_id) as avg
    from simulator_20220320.message_actions
    where toStartOfDay(time) between today() - 7 and yesterday()
    group by toStartOfDay(time)
    order by toStartOfDay(time)
    '''
    avg_messages = ph.read_clickhouse(query, connection=connection)
    
    bot.sendMessage(chat_id=cht_id, text=txt_cmpr(avg_messages, metric='Количество сообщений в среднем на пользователя', col='avg'))
    
    report_avg_messages = io.BytesIO()
    report_avg_messages.name = 'report_avg_messages.png'
    fig, axs = plt.subplots(figsize=(16,8))
    sns.lineplot(x='date', y='avg', data=avg_messages, ax=axs, label='avg_messages', color='b')
    axs.set(xlabel='avg_messages', title='Average Messages by User')
    plt.tight_layout()
    plt.savefig(report_avg_messages)
    report_avg_messages.seek(0)
    bot.sendPhoto(chat_id=cht_id, photo=report_avg_messages)
    
    #total_messages
    query = '''
    select
    toStartOfDay(time) as date,
    count(user_id) as total
    from simulator_20220320.message_actions
    where toStartOfDay(time) between today() - 7 and yesterday()
    group by toStartOfDay(time)
    order by toStartOfDay(time)
    '''
    total_messages = ph.read_clickhouse(query, connection=connection)
    
    bot.sendMessage(chat_id=cht_id, text=txt_cmpr(total_messages, metric='Общее количество сообщений', col='total'))
    
    #both_apps
    query = '''
    with
    f as (
      select
      toStartOfDay(time) as day,
      user_id,
      if(gender=1, 'male', 'female') as gender,
      age,
      country,
      city,
      os,
      source,
      countIf(action='view') as views,
      countIf(action='like') as likes
      from simulator_20220320.feed_actions
      where toStartOfDay(time) between today() - 7 and yesterday()
      group by day, user_id, gender, age, country, city, os, source
      order by day desc, user_id asc
    ),
    m as (
      select
      toStartOfDay(time) as day,
      user_id,
      if(gender=1, 'male', 'female') as gender,
      age,
      country,
      city,
      os,
      source,
      count(*) as messages
      from simulator_20220320.message_actions
      where toStartOfDay(time) between today() - 7 and yesterday()
      group by day, user_id, gender, age, country, city, os, source
      order by day desc, user_id asc
    ),
    t1 as (
      select
      if(f.day=0, m.day, f.day) as day,
      if(f.user_id=0, m.user_id, f.user_id) as user_id,
      if(f.gender='', m.gender, f.gender) as gender,
      if(f.age=0, m.age, f.age) as age,
      if(f.country='', m.country, f.country) as country,
      if(f.city='', m.city, f.city) as city,
      if(f.os='', m.os, f.os) as os,
      if(f.source='', m.source, f.source) as source,
      views,
      likes,
      messages
      from f
      full join m
      on f.user_id = m.user_id and f.day = m.day
    ),
    t2 as (
    select
    day,
    user_id,
    if(and(views + likes != 0, messages != 0), 1, 0) as both_apps,
    if(and(views + likes = 0, messages != 0), 1, 0) as only_mess,
    if(and(views + likes != 0, messages = 0), 1, 0) as only_news
    from t1
    )
    select
    day,
    sum(both_apps) as both_apps_dau,
    sum(only_mess) as only_mess_dau,
    sum(only_news) as only_news_dau,
    avg(both_apps) as both_apps_prcnt,
    avg(only_mess) as only_mess_prcnt,
    avg(only_news) as only_news_prcnt
    from t2
    group by day
    order by day
    '''
    both = ph.read_clickhouse(query, connection=connection)
    
    td_lst = both.iloc[-1,].to_list()
    txt_msg = f'@rushawx\
    \nКоличество уникальных пользователей в разрезе используемых сервисов на {str(td_lst[0])[0:10]}:\
    \n- только новостная лента {td_lst[3]} или {round(td_lst[6] * 100, 2)}%\
    \n- только сообщения {td_lst[2]} или {round(td_lst[5] * 100, 2)}%\
    \n- оба сервиса {td_lst[1]} или {round(td_lst[4] * 100, 2)}%'
    bot.sendMessage(chat_id=cht_id, text=txt_msg)
    
    both_melted = both[['day', 'both_apps_dau', 'only_mess_dau', 'only_news_dau']].melt(id_vars=['day'])
    both_melted['day'] = both_melted['day'].astype('str')
    report_both = io.BytesIO()
    report_both.name = 'report_both.png'
    fig, axs = plt.subplots(figsize=(16,8))
    sns.barplot(x='day', y='value', hue='variable', data=both_melted, ax=axs)
    axs.set(xlabel='dau', title='DAU. Breakdown by apps. Absolute values')
    plt.tight_layout()
    plt.savefig(report_both)
    report_both.seek(0)
    bot.sendPhoto(chat_id=cht_id, photo=report_both)

try:
    task_two()
except Exception as e:
    print(e)
