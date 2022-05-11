import numpy as np
import pandas as pd
import pandahouse as ph

import matplotlib.pyplot as plt
import seaborn as sns

import telegram
import io

from datetime import date

def check_anomaly(df, metric, n=4, a=5):
    
    df = df[['ts', 'date', 'hm', metric]].copy()
    
    df['q75'] = df[metric].shift(1).rolling(window=n).quantile(.75)
    df['q25'] = df[metric].shift(1).rolling(window=n).quantile(.25)
    df['iqr'] = df['q75'] - df['q25']

    df['upper'] = df['q75'] + df['iqr'] * a
    df['upper'] = df['upper'].rolling(window=n, center=True, min_periods=1).mean()
    df['lower'] = df['q25'] - df['iqr'] * a
    df['lower'] = df['lower'].rolling(window=n, center=True, min_periods=1).mean()

    if df['lower'].iloc[-1] <= df[metric].iloc[-1] <= df['upper'].iloc[-1]:
        is_alert = 0
    else:
        is_alert = 1

    return is_alert, df

def run_alerts(chat=None):
    # chat_id = chat or 517873898
    chat_id = chat or -1001706798154
    bot = telegram.Bot(token='5161462233:AAHsaiNpJopThhUEugZI9ziKb-bgxBwTgzY')

    connection = {'host': 'https://clickhouse.lab.karpov.courses/',
    'database':'simulator_20220320',
    'user':'student', 
    'password':'dpo_python_2020'
    }
    
    query = '''
    with
    fds as (
        select
        toStartOfFifteenMinutes(time) as ts,
        toStartOfDay(time) as date,
        formatDateTime(ts, '%R') as hm,
        uniqExact(user_id) as users_fds,
        countIf(action='view') as views,
        countIf(action='like') as likes,
        likes / views as ctr
        from simulator_20220320.feed_actions
        where ts >=  today() - 1 and ts < toStartOfFifteenMinutes(now())
        group by ts, date, hm
    ),
    mssgs as (
        select
        toStartOfFifteenMinutes(time) as ts,
        toStartOfDay(time) as date,
        formatDateTime(ts, '%R') as hm,
        uniqExact(user_id) as users_mssgs,
        count(user_id) as messages
        from simulator_20220320.message_actions
        where ts >=  today() - 1 and ts < toStartOfFifteenMinutes(now())
        group by ts, date, hm
    )
    select
    f.ts,
    f.date,
    f.hm,
    f.users_fds,
    f.views,
    f.likes,
    f.ctr,
    m.users_mssgs,
    m.messages
    from fds as f
    left join mssgs as m
    on f.ts = m.ts and f.date = m.date and f.hm = m.hm
    order by ts
    '''

    data = ph.read_clickhouse(query, connection=connection)

    for metric in ['users_fds', 'views', 'likes', 'ctr', 'users_mssgs', 'messages']:
        is_alert, df = check_anomaly(data, metric)
        if is_alert:
            msg = '''Метрика {metric}:\
            \nтекущее значение = {current_value:.2f}\
            \nотклонение от предыдущего значения = {last_val_dif:.2%}.\
            \n@rushawx\
            \nДашборд алертов: https://superset.lab.karpov.courses/superset/dashboard/617/'''\
            .format(metric=metric, current_value=df[metric].iloc[-1], last_val_dif=abs(1 - df[metric].iloc[-1]/df[metric].iloc[-2]))

            sns.set(rc={'figure.figsize': (16, 10)})
            plt.tight_layout()

            ax = sns.lineplot(
                x=df["ts"],
                y=df[metric],
                label=metric
                )
            
            ax = sns.lineplot(
                x=df["ts"],
                y=df['upper'],
                label='upper'
                )
            
            ax = sns.lineplot(
                x=df["ts"],
                y=df['lower'],
                label='lower'
                )

            for ind, label in enumerate(ax.get_xticklabels()):
                if ind % 2 == 0:
                    label.set_visible(True)
                else:
                    label.set_visible(False)
            ax.set(xlabel='time')
            ax.set(ylabel=metric)

            ax.set_title('{}'.format(metric))
            ax.set(ylim=(0, None))

            plot_object = io.BytesIO()
            ax.figure.savefig(plot_object)
            plot_object.seek(0)
            plot_object.name = '{0}.png'.format(metric)
            plt.close()

            bot.sendMessage(chat_id=chat_id, text=msg)
            bot.sendPhoto(chat_id=chat_id, photo=plot_object)

try:
    run_alerts()
except Exception as e:
    print(e)
