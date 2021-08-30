#Libraries
from functools import partial, reduce
from itertools import cycle
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import yfinance as yf

############################### MARKET CAP ##############################
@st.cache(show_spinner=False,allow_output_mutation=True)
def market_cap(dict_tickers, proxy_option):
    dict_annual_price = {}
    proxy_server = os.getenv('PROXY_SERVER')
    for ticker, df in dict_tickers.items():
        if proxy_option == 'Yes':
            price = yf.Ticker(ticker).history(start="2017-01-01", proxy=proxy_server).reset_index().sort_values(by='Date', ascending=True)[['Date', 'Close']]
            info = df.get_info(proxy=proxy_server)
        else:
            price = yf.Ticker(ticker).history(start="2017-01-01").reset_index().sort_values(by='Date', ascending=True)[['Date', 'Close']]
            info = df.get_info()
        price['Year'] = pd.DatetimeIndex(price['Date']).year
        price['Date'] = price['Date'].dt.strftime('%Y-%m-%d')
        price = price.groupby('Year').agg({'Date':'last','Close': 'last'}).sort_values(by="Date", ascending=False).reset_index(drop=['Year']).rename(columns={'Close': f'Price_{ticker}'})
        dict_annual_price[ticker] = price
        market_cap = info['marketCap']
        actual_price = info['regularMarketPrice']
        outstanding_shares = market_cap / actual_price
        dict_annual_price[ticker][f'Outstanding_shares_{ticker}'] = outstanding_shares
        dict_annual_price[ticker][f'Market_cap_{ticker}'] = dict_annual_price[ticker][f'Outstanding_shares_{ticker}'] * dict_annual_price[ticker][f'Price_{ticker}']
    my_reduce = partial(pd.merge, on='Date', how='outer')
    df_price = reduce(my_reduce, dict_annual_price.values()).sort_values(by="Date", ascending=False)
    return df_price


################## ANNUAL DATAFRAME ###################
@st.cache(show_spinner=False,allow_output_mutation=True)
def annual_financials(dict_tickers):
    #INCOME STATEMENT#
    dict_annual_income_statement = {}
    columns = ['Total Revenue', 'Gross Profit', 'Ebit', 'Net Income', 'Research Development']
    for ticker, df in dict_tickers.items():
        df = df.get_financials()
        df = df.T[columns].rename(columns={'Total Revenue':f'Revenue_{ticker}',
                                            'Gross Profit':f'Gross_profit_{ticker}',
                                            'Ebit': f'Ebit_{ticker}',
                                            'Net Income': f'Net_income_{ticker}',
                                            'Research Development':f'Research_development_{ticker}'}).reset_index(drop=[''])
        dict_annual_income_statement[ticker] = df
    #my_reduce = partial(pd.merge, on='Date', how='outer')
    #df_annual_income_statement = reduce(my_reduce, dict_annual_income_statement.values()).sort_values(by="Date",ascending=False)
    df_annual_income_statement = pd.concat(dict_annual_income_statement.values(),axis=1)

    #BALANCE SHEET#
    dict_annual_balance_sheet = {}
    columns = ['Total Current Assets','Total Current Liabilities','Long Term Debt','Total Stockholder Equity']
    for ticker, df in dict_tickers.items():
        df = df.get_balance_sheet()
        columns = [col for col in columns if col in df.T.columns]
        df = df.T[columns].rename(columns={'Total Current Assets':f'Total_current_assets_{ticker}',
                                                        'Total Current Liabilities':f'Total_current_liabilities_{ticker}',
                                                        'Long Term Debt': f'Long_term_debt_{ticker}',
                                                        'Total Stockholder Equity':f'Equity_{ticker}'}).reset_index(drop=[''])
        dict_annual_balance_sheet[ticker] = df
    #my_reduce = partial(pd.merge, on='Date', how='outer')
    #df_annual_balance_sheet = reduce(my_reduce, dict_annual_balance_sheet.values()).sort_values(by="Date",ascending=False)
    df_annual_balance_sheet = pd.concat(dict_annual_balance_sheet.values(), axis=1)

    #MERGE OF INCOME STATEMENT AND BALANCE SHEET#
    df_annual_financials = pd.concat([df_annual_income_statement, df_annual_balance_sheet], axis=1)
    annual_dates = ['2020-01-01','2019-01-01','2018-01-01','2017-01-01']
    df_annual_financials['Date'] = pd.to_datetime(annual_dates).strftime('%Y-%m-%d')
    df_annual_financials = df_annual_financials.set_index('Date').reset_index()
    return df_annual_financials

################ QUARTER INCOME STATEMENT ###########################
@st.cache(show_spinner=False,allow_output_mutation=True)
def quarter_income_statement(dict_tickers):
    dict_quarter_income_statement = {}
    columns = ['Total Revenue', 'Gross Profit', 'Ebit', 'Net Income', 'Research Development']
    for ticker, df in dict_tickers.items():
        df = df.quarterly_financials
        df = df.T[columns].rename(columns={'Total Revenue':f'Revenue_{ticker}',
                                                        'Gross Profit':f'Gross_profit_{ticker}',
                                                        'Ebit': f'Ebit_{ticker}',
                                                        'Net Income': f'Net_income_{ticker}',
                                                        'Research Development':f'Research_development_{ticker}'}).reset_index(drop=[''])
        dict_quarter_income_statement[ticker] = df
    #my_reduce = partial(pd.merge, on='Date', how='outer')
    #df_quarter_income_statement = reduce(my_reduce, dict_quarter_income_statement.values()).sort_values(by="Date",ascending=False)
    df_quarter_income_statement = pd.concat(dict_quarter_income_statement.values(), axis=1)
    quarter_dates = ['2021-06-01', '2021-03-01', '2020-12-01', '2020-09-01']
    df_quarter_income_statement['Date'] = pd.to_datetime(quarter_dates).strftime('%Y-%m-%d')
    df_quarter_income_statement = df_quarter_income_statement.set_index('Date').reset_index()

    #Forecast next annual income statement
    df_annual_income_statement_forecasted = df_quarter_income_statement.head(1).drop(columns=['Date'])*4
    annual_dates = ['2021-01-01']
    df_annual_income_statement_forecasted['Date'] = pd.to_datetime(annual_dates).strftime('%Y-%m-%d')
    df_annual_income_statement_forecasted = df_annual_income_statement_forecasted.set_index('Date').reset_index()
    return df_quarter_income_statement, df_annual_income_statement_forecasted


#################### RATIOS ##############################################
@st.cache(show_spinner=False,allow_output_mutation=True)
def calculate_ratios(df_annual_financials,dict_tickers):
    ###########GROWTH: REVENUE AND INCOME#############
    for ticker in dict_tickers.keys():
        #GROWTH METRICS#
        df_annual_financials[f'Growth_revenue_{ticker}']= df_annual_financials[f'Revenue_{ticker}'].pct_change(-1)
        df_annual_financials[f'Growth_net_income_{ticker}']= df_annual_financials[f'Net_income_{ticker}'].pct_change(-1)
        df_annual_financials[f'Growth_gross_profit_{ticker}']= df_annual_financials[f'Gross_profit_{ticker}'].pct_change(-1)

        # NORMALIZED METRICS#
        df_annual_financials[f'Normalized_revenue_{ticker}'] = df_annual_financials[f'Revenue_{ticker}'] / df_annual_financials[f'Revenue_{ticker}'].tail(1).values[0]
        df_annual_financials[f'Normalized_net_income_{ticker}'] = df_annual_financials[f'Net_income_{ticker}'] / df_annual_financials[f'Net_income_{ticker}'].tail(1).values[0]
        df_annual_financials[f'Normalized_gross_profit_{ticker}'] = df_annual_financials[f'Gross_profit_{ticker}'] / df_annual_financials[f'Gross_profit_{ticker}'].tail(1).values[0]

        #VALUATION RATIOS#
        df_annual_financials[f'P/S_{ticker}'] = df_annual_financials[f'Market_cap_{ticker}'] / df_annual_financials[f'Revenue_{ticker}']
        df_annual_financials[f'P/E_{ticker}'] = df_annual_financials[f'Market_cap_{ticker}']/df_annual_financials[f'Net_income_{ticker}']
        df_annual_financials[f'P/G_{ticker}'] = df_annual_financials[f'Market_cap_{ticker}'] / df_annual_financials[f'Gross_profit_{ticker}']

        #RESEARCH RATIO#
        df_annual_financials[f'R&D/revenue_{ticker}'] = df_annual_financials[f'Research_development_{ticker}']/df_annual_financials[f'Revenue_{ticker}']

        #DEBT RATIOS#
        df_annual_financials[f'Current_ratio_{ticker}'] = df_annual_financials[f'Total_current_assets_{ticker}']/df_annual_financials[f'Total_current_liabilities_{ticker}']
        if f'Long_term_debt_{ticker}' in df_annual_financials.columns:
            df_annual_financials[f'Debt/equity_{ticker}'] = df_annual_financials[f'Long_term_debt_{ticker}']/df_annual_financials[f'Equity_{ticker}']
            df_annual_financials[f'Debt/ebit_{ticker}'] = df_annual_financials[f'Long_term_debt_{ticker}'] / df_annual_financials[f'Equity_{ticker}']
    return df_annual_financials

##########################################################################################################PLOTS###############################################################################
@st.cache(show_spinner=False,allow_output_mutation=True)
def market_cap_plot(df,period,substring, y_title, general_title):
    figure = go.Figure()
    revenue_columns = [col for col in df.columns if substring in col]
    revenue_columns_replaced = [col.replace(f"{substring}_", "") for col in revenue_columns]
    dict_cols = dict(zip(revenue_columns, revenue_columns_replaced))
    df = df.rename(columns=dict_cols)
    revenue_columns_replaced = df.head(1)[revenue_columns_replaced].sort_values(by=df.index[0], ascending=True, axis=1).columns
    palette = cycle(px.colors.qualitative.Dark24)
    dict_stock_color = {}
    for stock in revenue_columns_replaced:
        dict_stock_color[stock] = next(palette)
    for stock in revenue_columns_replaced:
        figure.add_trace(go.Scatter(
            x=df['Date'],
            y=df[stock],
            name=stock,
            marker_color=dict_stock_color[stock]
        ))
    #################X AXIS#############################
    if period == 'Annually':
        figure.update_xaxes(title="Date",dtick="M12")
    else:
        figure.update_xaxes(title="Date", dtick="M3",tick0 = "2020-09-01",tickformat='%b %Y')

    ##############Y AXIS###############################
    figure.update_yaxes(title=f"{y_title}")

    #############TITLE################################
    figure.update_layout(title_text=f"<b>{general_title}</b>", title_font_color='#3E477F', width=1500, height=400)
    return figure,dict_stock_color

@st.cache(show_spinner=False,allow_output_mutation=True)
def bar_plot(df,period,dict_stock_color,substring, y_title, general_title):
    figure = go.Figure()
    revenue_columns = [col for col in df.columns if substring in col]
    revenue_columns_replaced = [col.replace(f"{substring}_", "") for col in revenue_columns]
    dict_cols = dict(zip(revenue_columns, revenue_columns_replaced))
    df = df.rename(columns=dict_cols)
    revenue_columns_replaced = df.head(1)[revenue_columns_replaced].sort_values(by=df.index[0], ascending=True, axis=1).columns
    for stock in revenue_columns_replaced:
        figure.add_trace(go.Bar(
            x=df['Date'],
            y=df[stock],
            name=stock,
            marker_color=dict_stock_color[stock]
        ))
    #################X AXIS#############################
    if period == 'Annually':
        figure.update_xaxes(title="Date",dtick="M12")
        figure.add_vrect(x0="2020-08-01", x1="2021-08-01",
                         annotation_text="Forecasted period", annotation_position="top left",
                         fillcolor="grey", opacity=0.25, line_width=0)
    else:
        figure.update_xaxes(title="Date", dtick="M3",tick0 = "2020-09-01",tickformat='%b %Y')

    ##############Y AXIS###############################
    figure.update_yaxes(title=f"{y_title}")

    #############TITLE################################
    figure.update_layout(title_text=f"<b>{general_title}</b>",title_font_color = '#3E477F',width = 1500, height=400)
    return figure

@st.cache(show_spinner=False,allow_output_mutation=True)
def line_plot(df,dict_stock_color,period,substring,y_title, general_title):
    figure = go.Figure()
    revenue_columns = [col for col in df.columns if substring in col]
    revenue_columns_replaced = [col.replace(f"{substring}_", "") for col in revenue_columns]
    dict_cols = dict(zip(revenue_columns, revenue_columns_replaced))
    df = df.rename(columns=dict_cols)
    revenue_columns_replaced = df.head(1)[revenue_columns_replaced].sort_values(by=df.index[0], ascending=True, axis=1).columns
    for stock in revenue_columns_replaced:
        figure.add_trace(go.Scatter(
            x=df['Date'],
            y=df[stock],
            name=stock,
            marker_color=dict_stock_color[stock]
        ))
    ##################X AXIS###################
    if period == 'Annually':
        figure.add_vrect(x0="2020-08-01", x1="2021-08-01",
                         annotation_text="Forecasted period", annotation_position="top left",
                         fillcolor="grey", opacity=0.25, line_width=0)
        figure.update_xaxes(title="Date", dtick="M12")
    else:
        figure.update_xaxes(title="Date", dtick="M3", tick0="2020-09-01", tickformat='%b %Y')

    #################Y AXIS####################
    figure.update_yaxes(title=f"{y_title}")

    ################TITLE#######################
    figure.update_layout(title_text=f"<b>{general_title}</b>",title_font_color = '#3E477F' ,width = 1500, height=400)
    return figure


