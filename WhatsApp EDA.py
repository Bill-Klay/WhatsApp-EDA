import base64
import datetime
import io

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table

import re
import datetime
import numpy as np
import pandas as pd
import warnings
from collections import Counter

# from wordcloud import WordCloud, STOPWORDS
# import matplotlib.pyplot as plt
# import seaborn as sns
# import emoji

import plotly.offline as pyo
import plotly.graph_objs as go


warnings.filterwarnings('ignore')

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        # Allow multiple files to be uploaded
        multiple=True
    ),
    html.Div(id='output-data-upload'),
])

def rawToDf(file, key):
    '''Converts raw .txt file into a Data Frame'''
    
    split_formats = {
        '12hr' : r'\d{1,2}/\d{1,2}/\d{2,4}\s\d{1,2}:\d{2}\s[APap][mM]\s-\s',
        '24hr' : r'\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}\s-\s',
        'custom' : ''
    }
    datetime_formats = {
        '12hr' : '%d/%m/%y %I:%M %p - ',
        '24hr' : '%d/%m/%Y, %H:%M - ',
        'custom': ''
    }
    
    try:
        raw_data = file.decode("utf-8")
        raw_string = ' '.join(raw_data.split('\n')) # converting the list split by newline char. as one whole string as there can be multi-line messages
        user_msg = re.split(split_formats[key], raw_string) [1:] # splits at all the date-time pattern, resulting in list of all the messages with user names
        date_time = re.findall(split_formats[key], raw_string) # finds all the date-time patterns

        df = pd.DataFrame({'date_time': date_time, 'user_msg': user_msg}) # exporting it to a df
    except IOError:
        print ('File not accessible')
        return
    except Exception as e:
        print(e)
        return
    # converting date-time pattern which is of type String to type datetime,
    # format is to be specified for the whole string where the placeholders are extracted by the method 
    df['date_time'] = pd.to_datetime(df['date_time'], format=datetime_formats[key])
    
    # split user and msg 
    usernames = []
    msgs = []
    for i in df['user_msg']:
        a = re.split(r'([\w\W]+?):\s', i) # lazy pattern match to first {user_name}: pattern and spliting it aka each msg from a user
        if(a[1:]): # user typed messages
            usernames.append(a[1])
            msgs.append(a[2])
        else: # other notifications in the group(eg: someone was added, some left ...)
            usernames.append("group_notification")
            msgs.append(a[0])

    # creating new columns         
    df['user'] = usernames
    df['message'] = msgs

    # dropping the old user_msg col.
    df.drop('user_msg', axis=1, inplace=True)
    
    return df

def parse_contents(contents, filename, date):
    content_type, content_string = contents.split(',')
    # print(type(contents))
    decoded = base64.b64decode(content_string)
    try:
        df = rawToDf(decoded, '12hr')

        df['day'] = df['date_time'].dt.strftime('%a')
        df['month'] = df['date_time'].dt.strftime('%b')
        df['year'] = df['date_time'].dt.year
        df['date'] = df['date_time'].apply(lambda x: x.date())

        df = df[df.year != 2015]
        df.reset_index(inplace=True)
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])

    try:
        df1 = df.copy()      # I will be using a copy of the original data frame everytime, to avoid loss of data!
        df1['message_count'] = [1] * df1.shape[0]      # adding extra helper column --> message_count.
        df1.drop(columns='year', inplace=True)         # dropping unnecessary columns, using `inplace=True`, since this is copy of the DF and won't affect the original DataFrame.
        df1 = df1.groupby('date').sum().reset_index()  # grouping by date; since plot is of frequency of messages --> no. of messages / day.
        df1.drop(0, inplace=True)
    except:
        print("Error I01: Overall-graph")
        print("Problem with processing count of messages")

    return html.Div([
        html.H5(filename),
        html.H6(datetime.datetime.fromtimestamp(date)),

        dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[{'name': i, 'id': i} for i in df.columns],
            style_cell={'textAlign': 'left', 'textOverflow': 'ellipsis', 'minWidth': '20px', 'maxWidth': '400px'},
            style_table={'overflowX': 'auto', 'overflowY': 'auto'},
            page_size=10
        ),

        html.Hr(),  # horizontal line

        dcc.Graph(
            id='overall-graph',
            figure={
                'data': [
                    go.Scatter(
                        x = df1.date,
                        y = df1.message_count,
                        mode = 'lines+markers',
                        marker = {
                            'size': 12,
                            'color': 'rgb(51,204,153)',
                            'symbol': 'pentagon',
                            'line': {'width': 1}
                        }
                    )
                ],
                'layout': go.Layout(
                    title = 'Overall Messages Count',
                    xaxis = {'title': 'Date'},
                    yaxis = {'title': 'Message Count'},
                    hovermode='closest'
                )
            }
        ),

        html.Hr(),


    ])

@app.callback(Output('output-data-upload', 'children'),
              Input('upload-data', 'contents'),
              State('upload-data', 'filename'),
              State('upload-data', 'last_modified'))
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [
            parse_contents(c, n, d) for c, n, d in
            zip(list_of_contents, list_of_names, list_of_dates)]
        return children

if __name__ == '__main__':
    app.run_server(debug=True)