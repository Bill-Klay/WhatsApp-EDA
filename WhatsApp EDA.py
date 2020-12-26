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

# List of global variables
df = pd.DataFrame()
messageCount = pd.DataFrame()
messagePerUser = pd.DataFrame()
linksCount = pd.DataFrame()
fileCheck = False

#  App basic layout
app.layout = html.Div([
    # Upload data div
    html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select Files')
            ]),
            style={
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            # Allow multiple files to be uploaded
            multiple = False
        )],
        style = {'display' : 'inline-block', 'width' : '79%'}
    ),
    html.Div([
        dcc.Dropdown(
            id = 'time-format',
            options = [{'label': '12 Hours', 'value': '12hr'}, {'label': '24 Hours', 'value': '24hr'}],
            multi = False,
            placeholder = 'Enter date format'
        )
    ],
        style = {'display': 'inline-block', 'width': '20%'}
    ),

    # File details div
    html.Div(id = 'file-details')
])

# File upload text change
@app.callback(Output('upload-data', 'children'),
              Input('upload-data', 'filename'))
def fileUpload (filename):
    if filename is None:
        return html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ])
    else:
        return html.Div([
            filename,
            html.A(' Update file')
        ])

# First layout template
def template (filename, date, timeKey):
    filename = "Filename: " + filename
    date = "Last modified: " + str(datetime.datetime.fromtimestamp(date))
    timeKey = "Time format: " + timeKey

    return html.Div([
        html.H5(filename),
        html.H6(date),
        html.H6(timeKey),

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
                        x = messageCount.date,
                        y = messageCount.message_count,
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

        dcc.Graph(
            id='user-graph',
            figure={
                'data': [
                    go.Bar(
                        x = messagePerUser.user,
                        y = messagePerUser.message,
                        marker = {
                            'color': 'rgb(51,204,153)',
                        }
                    )
                ],
                'layout': go.Layout(
                    title = 'Message Sent by Users',
                    xaxis = {'title': 'User'},
                    yaxis = {'title': 'Message Count'},
                    hovermode = 'closest'
                )
            }
        ),

        html.Hr(),

        dcc.Graph(
            id='links-graph',
            figure={
                'data': [
                    go.Scatter(
                        x = linksCount.user,
                        y = linksCount.no_links,
                        mode = 'lines+markers',
                        marker = {
                            'size': 12,
                            'color': 'rgb(252, 107, 3)',
                            'symbol': 'pentagon',
                            'line': {'width': 1}
                        },
                        name = "Line plot"
                    ),
                ],
                'layout': go.Layout(
                    title = 'Links Shared',
                    xaxis = {'title': 'User'},
                    yaxis = {'title': 'Links Shared'},
                    hovermode='closest'
                )
            }
        ),

        html.Hr(),
    ])

# Processor function to turn raw data file into a dataframe
def rawToDf (file, timeKey):
    global fileCheck, df, messageCount, messagePerUser, linksCount

    df = df.iloc[0:0]

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
        user_msg = re.split(split_formats[timeKey], raw_string) [1:] # splits at all the date-time pattern, resulting in list of all the messages with user names
        date_time = re.findall(split_formats[timeKey], raw_string) # finds all the date-time patterns

        df = pd.DataFrame({'date_time': date_time, 'user_msg': user_msg}) # exporting it to a df
    except IOError:
        print ('File not accessible')
        return
    except Exception as e:
        print("Computer Generated Error: ", e)
        print("Dev Error: Please enter the correct date format")
        return

    # converting date-time pattern which is of type String to type datetime,
    # format is to be specified for the whole string where the placeholders are extracted by the method 
    df['date_time'] = pd.to_datetime(df['date_time'], format=datetime_formats[timeKey])
    
    # split user and msg 
    usernames = []
    msgs = []
    try:
        for i in df['user_msg']:
            a = re.split(r'([\w\W]+?):\s', i) # lazy pattern match to first {user_name}: pattern and spliting it aka each msg from a user
            if(a[1:]): # user typed messages
                usernames.append(a[1])
                msgs.append(a[2])
            else: # other notifications in the group(eg: someone was added, some left ...)
                usernames.append("group_notification")
                msgs.append(a[0])
    except Exception as e:
        print("Computer Generated Error: ", e)
        print("Dev Error: Could not parse users and notifications")
        return

    try:
        # creating new columns         
        df['user'] = usernames
        df['message'] = msgs

        # dropping the old user_msg col.
        df.drop('user_msg', axis=1, inplace=True)

        df['day'] = df['date_time'].dt.strftime('%a')
        df['month'] = df['date_time'].dt.strftime('%b')
        df['year'] = df['date_time'].dt.year
        df['date'] = df['date_time'].apply(lambda x: x.date())

        df = df[df.year != 2015]
        df.reset_index(inplace=True)
    except Exception as e:
        print("Computer Generated Error: ", e)
        print("Dev Error: Could not parse date time")

    # Overall messages data frame
    try:
        messageCount = df.copy()      # I will be using a copy of the original data frame everytime, to avoid loss of data!
        messageCount['message_count'] = [1] * messageCount.shape[0]      # adding extra helper column --> message_count.
        messageCount.drop(columns='year', inplace=True)         # dropping unnecessary columns, using `inplace=True`, since this is copy of the DF and won't affect the original DataFrame.
        messageCount = messageCount.groupby('date').sum().reset_index()  # grouping by date; since plot is of frequency of messages --> no. of messages / day.
        messageCount.drop(0, inplace=True)
    except:
        print("Error I01: Overall-graph; could not process count of messages")

    # Messages per user data frame
    try:
        messagePerUser = df.copy()    
        messagePerUser = messagePerUser[messagePerUser.user != "group_notification"]
        messagePerUser = messagePerUser.groupby("user")["message"].count().sort_values(ascending=False)
        messagePerUser = messagePerUser.reset_index()
    except:
        print("Error I02: Per user graph; could not process user graph")

    # Links data frame
    try:
        links = 0
        linksCount = pd.DataFrame()
        for index, row in df.iterrows():
            urls = re.findall(r'(https?://[^\s]+)', row.message)
            if urls:
                links = links + len(urls)
                linksCount = linksCount.append(row, ignore_index=True)

        linksCount = linksCount.groupby("user")["message"].count().sort_values(ascending=False)
        linksCount = pd.DataFrame({'user':linksCount.index, 'no_links':linksCount.values})
    except:
        print("Error I03: Links-graph; could not process links graph")

    fileCheck = True
    
    return fileCheck

@app.callback(Output('file-details', 'children'),
              Input('time-format', 'value'),
              Input('upload-data', 'contents'),
              State('upload-data', 'filename'),
              State('upload-data', 'last_modified'))
def uploadData (timeKey, content, filename, date):
    global df, fileCheck

    if content is not None:
        content_type, content_string = content.split(',')
        print(content_type)
        file = base64.b64decode(content_string)
        fileCheck = rawToDf(file, timeKey)
        if fileCheck:
            children = template(filename, date, timeKey)
            fileCheck = False
            return children
        else:
            return html.Div("There was a problem parsing the file, have you entered the correct date format?")

if __name__ == '__main__':
    app.run_server(debug=True)