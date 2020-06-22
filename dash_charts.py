import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
import dash_html_components as html
from datetime import datetime
from dateutil.relativedelta import relativedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as tls
import yfinance as yf

app = dash.Dash(
    external_stylesheets = [dbc.themes.BOOTSTRAP]
)

app.title = "Stock Analyser"

app.layout = html.Div(
    [
        dbc.Container(
            [
                dbc.Container(
                    dbc.Label(
                        "Enter symbol here:",
                        className = "mt-5"
                        ),
                ),

                

                dbc.Input(
                    id = "stockInput",
                    value = "MU",
                    type = "text"
                    ),

                dbc.Button(
                    "Submit",
                    id = "submitStock",
                    className = "mt-3"
                    ),

                html.Hr(

                ),
            ]
        ),

        dbc.Container(
            [
                dbc.Container(
                    dbc.Label(
                    """
                    Enter timeframe here:
                    """,
                    ),
                ),
                
                html.Span(
                    dcc.DatePickerRange(
                        id = 'stockRange',
                        start_date = datetime(
                            int((datetime.today() - relativedelta(months = 12)).strftime("%Y")),
                            int((datetime.today() - relativedelta(months = 12)).strftime("%m")),
                            int((datetime.today() - relativedelta(months = 12)).strftime("%d"))
                            ).date(),
                        end_date = datetime(
                            int(datetime.today().strftime('%Y')),
                            int(datetime.today().strftime('%m')),
                            int(datetime.today().strftime('%d'))
                            ).date(),
                        display_format = 'YYYY-MM-DD',
                        number_of_months_shown = 3
                        ),
                ),
                
                html.Hr(

                ),
            ]
        ),
    
        
        dcc.Graph(
            id = "priceGraph",
            figure = {
                "layout" : {
                    "height": 1100
                    }    
                }
            ),

        html.Div(
            id = "volumeGraph"
            ),

        dcc.Store(
            id = 'intermediateStockDf',
            storage_type = 'session'
            )
    ]
)

@app.callback(
    Output(
        component_id = 'intermediateStockDf',
        component_property = 'data'
    ),

    [
        Input(
            component_id = 'submitStock',
            component_property = 'n_clicks'
        ),
    ],

    state = [
        State(
            component_id = 'stockInput',
            component_property = 'value'
        )
    ]
)
def store_stock_df(n_clicks, input_stock):
    symbol_selected = yf.Ticker(str(input_stock).upper())

    df_symbol = symbol_selected.history(period = "5y", interval = "1d")
    df_symbol.reset_index(inplace = True)
    
    df_symbol = df_symbol.to_json()

    return df_symbol, str(symbol_selected.info.get('longName')), str(input_stock).upper()


@app.callback(
    Output(
        component_id = 'priceGraph', 
        component_property = 'figure'
        ),
    
    [
        Input(
            component_id = 'intermediateStockDf',
            component_property = 'data'
        ),

        Input(
            component_id = 'stockRange',
            component_property = 'start_date'
        ),

        Input(
            component_id = 'stockRange',
            component_property = 'end_date'
        )
    ]
)
def update_graph(input_stock, start_date, end_date):
    df, selected_ticker, ticker_symbol = input_stock

    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')

    if selected_ticker == '':
        selected_ticker = 'NIL'

    df = pd.read_json(df)

    rsi_period = 14

    def rolling_moving_ave(x, period, y):
        a = (period - 1) / period

        ak = a**np.arange(len(x) - 1, -1, -1)

        return np.append(y, np.cumsum(ak * x) / ak / period + y * a**np.arange(1, len(x) + 1))

    df['Change'] = df.Close.diff()

    df['Gain'] = df.Change.mask(df.Change < 0, 0.0)
    df['Loss'] = -df.Change.mask(df.Change > 0, -0.0)

    df.loc[rsi_period:, 'ave_gain'] = rolling_moving_ave(df.Gain[rsi_period + 1:].values, rsi_period, df.loc[:rsi_period, 'Gain'].mean())
    df.loc[rsi_period:, 'ave_loss'] = rolling_moving_ave(df.Loss[rsi_period + 1:].values, rsi_period, df.loc[:rsi_period, 'Loss'].mean())

    df['RS'] = df.ave_gain / df.ave_loss

    df['RSI_14'] = 100 - (100 / (1 + df.RS))

    df['180_SMA'] = df.Close.rolling(180).mean()

    df['9_SMA'] = df.Close.rolling(9).mean()

    df['ema_fast'] = df.Close.ewm(span = 12, adjust = False).mean()

    df['ema_slow'] = df.Close.ewm(span = 26, adjust = False).mean()

    df['MACD'] = df.ema_fast - df.ema_slow

    df['Signal'] = df.MACD.ewm(span = 9, adjust = False).mean()
   
    df_range = df.loc[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

    fig = tls.make_subplots(
        rows = 4,
        cols = 1,
        shared_xaxes = True,
        vertical_spacing = 0.009, 
        horizontal_spacing = 0.009 
    )

    fig.append_trace(
        {
            'x': df_range.Date,
            'open': df_range.Open,
            'high': df_range.High,
            'low': df_range.Low,
            'close': df_range.Close,
            'type': 'candlestick',
            'name': 'Price'
        },
        1, 1
    )

    fig.append_trace(
        {
            'x': df_range.Date,
            'y': df_range['9_SMA'],
            'type': 'scatter',
            'name': '9-day SMA'
        },
        1, 1
    )

    fig.append_trace(
        {
            'x': df_range.Date,
            'y': df_range['180_SMA'],
            'type': 'scatter',
            'name': '180-day SMA'
        },
        1, 1
    )

    fig.append_trace(
        {
            'x': df_range.Date,
            'y': df_range.Volume,
            'type': 'bar',
            'name': 'Volume',
            'marker_color': 'rgba(0, 0, 0, 255)'
        },
        2, 1
    )

    fig.append_trace(
        {
            'x': df_range.Date,
            'y': df_range.RSI_14,
            'type': 'scatter',
            'name': 'RSI'
        },
        3, 1
    )

    fig.add_shape(
        x0 = df_range.Date.iloc[0],
        x1 = df_range.Date.iloc[-1],
        y0 = 70,
        y1 = 70,
        line = dict(
            color = 'yellowgreen',
            width = 0.8
        ),
        row = 3,
        col = 1
    )

    fig.add_shape(
        x0 = df_range.Date.iloc[0],
        x1 = df_range.Date.iloc[-1],
        y0 = 30,
        y1 = 30,
        line = dict(
            color = 'yellowgreen',
            width = 0.8
        ),
        row = 3,
        col = 1
    )

    fig.append_trace(
        {
            'x': df_range.Date,
            'y': df_range.MACD,
            'type': 'scatter',
            'name': 'MACD'
        },
        4, 1
    )

    fig.append_trace(
        {
            'x': df_range.Date,
            'y': df_range.Signal,
            'type': 'scatter',
            'name': 'Signal'
        },
        4, 1
    )


    fig['layout'].update(
        title = {
            'text': f'Daily plot of {selected_ticker} ({ticker_symbol})',
            'xanchor': 'center',
            'yanchor': 'top',
            'x': 0.5,
            'y': 0.9,
            },
        hovermode = 'x unified',
        plot_bgcolor = 'rgba(255, 255, 255, 0.4)'
    )

    return fig

"""
@app.callback(
    Output(
        component_id = 'volumeGraph',
        component_property = 'children'
    ),

    Input(
        component_id = 'submitStock'
    )
)
"""

if __name__ == "__main__":
    app.run_server(host="127.0.0.1", port="1234")