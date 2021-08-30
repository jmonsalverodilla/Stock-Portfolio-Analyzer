import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from functools import partial, reduce
import os
from itertools import cycle

#####################PORTFOLIO COMPANIES#########################
#Download data from yfinance api and save it in .csv file
@st.cache(show_spinner=False,allow_output_mutation=True)
def download_data(my_list,start,end,proxy_option):
    error_tickers = []
    dict_of_df = {}
    proxy_server = os.getenv('PROXY_SERVER')
    for symbol in my_list:
        try:
            if proxy_option == 'Yes':
                df = yf.Ticker(symbol).history(start=start, end=end, proxy=proxy_server).reset_index()[['Date','Close','Volume']]
            else:
                df = yf.Ticker(symbol).history(start=start, end=end).reset_index()[['Date','Close','Volume']]
            dict_of_df[symbol] = df
            print(df)
        except:
            error_tickers.append(symbol)
            pass
    min_dates = [company['Date'].min() for company in list(dict_of_df.values())]
    return dict_of_df, min_dates, error_tickers

@st.cache(show_spinner=False,allow_output_mutation=True)
def portfolio_return(company_list_df,
                     company_names,
                     initial_investment,
                     company_weighs,
                     start_date,
                     final_date
                     ):
    # Select the maximum min date from all dataframes
    min_dates = [company['Date'].min() for company in company_list_df]
    min_common_date = max(min_dates)
    company_list_df_filtered = [company[company['Date'] >= pd.to_datetime(min_common_date)] for company in company_list_df]

    # Let's create a dictionary where the keys are the symbols and the values are the dataframes
    company_dict_df = dict(zip(company_names, company_list_df_filtered))

    for i_weigh, (company_name, company) in enumerate(company_dict_df.items()):
        company.loc[:,'Price'] = company['Close']
        company.loc[:,'Return'] = company['Close'].pct_change()
        company = company.dropna()
        company = company[['Date', 'Price', 'Volume', 'Return']].rename(columns={'Return': 'Daily_return' + '_' + company_name,
                                                                                 'Price': 'Price' + '_' + company_name,
                                                                                 'Volume': 'Volume' + '_' + company_name})

        company = company[(company['Date'] >= pd.to_datetime(start_date)) & (company['Date'] <= pd.to_datetime(final_date))]
        company = company.reset_index().drop(columns=['index'])

        # Investment acumulado y drawdawns
        company['Investment_acumulado_{0}'.format(company_name)] = initial_investment * company_weighs[i_weigh]
        for i in range(1, company.shape[0]):
            company['Investment_acumulado_{0}'.format(company_name)][i] = company['Investment_acumulado_{0}'.format(company_name)][i - 1] * (1 + company['Daily_return_{0}'.format(company_name)][i - 1])
            company['Return_acumulado_{0}'.format(company_name)] = ((company['Investment_acumulado_{0}'.format(company_name)] / company['Investment_acumulado_{0}'.format(company_name)][0]) - 1) * 100
            company['Previous_peak_{0}'.format(company_name)] = company['Investment_acumulado_{0}'.format(company_name)].cummax()
            company['Drawdawn_{0}'.format(company_name)] = (company['Investment_acumulado_{0}'.format(company_name)] - company[
                'Previous_peak_{0}'.format(company_name)]) / company['Previous_peak_{0}'.format(company_name)]
        company = company.loc[:, company.columns.str.contains('peak') == False]
        company_dict_df[company_name] = company

    # Merge all the dataframes contained in the dictionary
    my_reduce = partial(pd.merge, on='Date', how='inner')
    company_return_all = reduce(my_reduce, company_dict_df.values())

    # Investment acumulado total
    company_return_all['Investment_acumulado_total'] = 0
    for company_name in company_dict_df.keys():
        company_return_all['Investment_acumulado_total'] = company_return_all['Investment_acumulado_total'] + company_return_all['Investment_acumulado_{0}'.format(company_name)]

    # Return acumulado total
    company_return_all['Return_acumulado_total'] = ((company_return_all['Investment_acumulado_total'] / company_return_all['Investment_acumulado_total'][0]) - 1) * 100

    # Percentage of allocation
    for company_name in company_dict_df.keys():
        company_return_all['Percentage_allocation_{0}'.format(company_name)] = company_return_all['Investment_acumulado_{0}'.format(company_name)] / \
                                                                               company_return_all['Investment_acumulado_total']

    # Drawdawn total
    company_return_all['Previous_peak_total'] = company_return_all['Investment_acumulado_total'].cummax()
    company_return_all['Drawdawn_total'] = (company_return_all['Investment_acumulado_total'] - company_return_all['Previous_peak_total']) / company_return_all[
        'Previous_peak_total']
    company_return_all = company_return_all.loc[:, company_return_all.columns.str.contains('peak') == False]

    # Day return total
    suma = 0
    for i, company_name in enumerate(company_names):
        company_return_all['Daily_return_total'] = suma + company_return_all['Daily_return_{0}'.format(company_name)] * company_return_all[
            'Percentage_allocation_{0}'.format(company_name)]
        suma = company_return_all['Daily_return_total']
    return company_return_all

@st.cache(show_spinner=False,allow_output_mutation=True)
def benchmark_return(benchmark_list_df,
                     benchmark_names,
                     initial_investment):

    # Let's create a dictionary where the keys are the symbols and the values are the dataframes
    benchmark_dict_df = dict(zip(benchmark_names, benchmark_list_df))
    for i_weigh, (benchmark_name, benchmark) in enumerate(benchmark_dict_df.items()):
        benchmark.loc[:,'Price'] = benchmark['Close']
        benchmark.loc[:,'Return'] = benchmark['Close'].pct_change()
        benchmark = benchmark.dropna()
        benchmark = benchmark[['Date', 'Price', 'Volume', 'Return']].rename(columns={'Return': 'Daily_return' + '_' + benchmark_name,
                                                                                 'Price': 'Price' + '_' + benchmark_name,
                                                                                 'Volume': 'Volume' + '_' + benchmark_name})

        # Investment acumulado y drawdawns
        benchmark = benchmark.reset_index().drop(columns=['index'])
        benchmark['Investment_acumulado_{0}'.format(benchmark_name)] = initial_investment
        for i in range(1, benchmark.shape[0]):
            benchmark['Investment_acumulado_{0}'.format(benchmark_name)][i] = benchmark['Investment_acumulado_{0}'.format(benchmark_name)][i - 1] * (1 + benchmark['Daily_return_{0}'.format(benchmark_name)][i - 1])
            benchmark['Return_acumulado_{0}'.format(benchmark_name)] = ((benchmark['Investment_acumulado_{0}'.format(benchmark_name)] / benchmark['Investment_acumulado_{0}'.format(benchmark_name)][0]) - 1) * 100
            benchmark['Previous_peak_{0}'.format(benchmark_name)] = benchmark['Investment_acumulado_{0}'.format(benchmark_name)].cummax()
            benchmark['Drawdawn_{0}'.format(benchmark_name)] = (benchmark['Investment_acumulado_{0}'.format(benchmark_name)] - benchmark[
                'Previous_peak_{0}'.format(benchmark_name)]) / benchmark['Previous_peak_{0}'.format(benchmark_name)]
        benchmark = benchmark.loc[:, benchmark.columns.str.contains('peak') == False]
        benchmark_dict_df[benchmark_name] = benchmark

    # Merge all the dataframes contained in the dictionary
    my_reduce = partial(pd.merge, on='Date', how='inner')
    benchmark_return_all = reduce(my_reduce, benchmark_dict_df.values())
    return benchmark_return_all

####################################PLOTS#####################################
@st.cache(show_spinner=False,allow_output_mutation=True)
def wealth_plot(df_portfolio,df_benchmark):
    df = df_portfolio.merge(df_benchmark, how="inner",on="Date")
    figure = go.Figure()
    investment_acumulado_columns = df.loc[:, df.columns.str.contains('Inv')].columns
    investment_acumulado_columns_replaced = [col.replace("Investment_acumulado_","") for col in investment_acumulado_columns]
    dict_cols = dict(zip(investment_acumulado_columns,investment_acumulado_columns_replaced))
    df = df.rename(columns=dict_cols)
    palette = cycle(px.colors.qualitative.Dark24)
    for stock in investment_acumulado_columns_replaced:
        if stock == '^GSPC':
            alpha = 1
            lw = 3
            dash = "dot"
        elif stock == '^IXIC':
            alpha = 1
            lw = 3
            dash = "dashdot"
        elif stock == 'total':
            alpha = 1
            lw = 4
            dash = 'solid'
        else:
            alpha = 1
            lw = 1
            dash = 'solid'
        figure.add_trace(go.Scatter(
            x=df['Date'],
            y=df[stock],
            name=stock,
            marker_color=next(palette),
            mode='lines',
            opacity=alpha,
            line={'width': lw,
                  'dash': dash}
        ))

    figure.update_layout(title_text="<b>Accumulated investment over time</b>",
                         updatemenus=[dict(buttons=[
                             dict(label="Linear", method="relayout", args=[{"yaxis.type": "linear"}]),
                             dict(label="Log", method="relayout", args=[{"yaxis.type": "log"}])])])
    figure.update_xaxes(
        title = "Date",
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        ))
    figure.update_yaxes(title = "Investment ($)")
    figure.update_layout(width = 1500, height=600)
    return figure

@st.cache(show_spinner=False,allow_output_mutation=True)
def accumulated_return_plot(df_portfolio,df_benchmark):
    df = df_portfolio.merge(df_benchmark, how="inner", on="Date")
    figure = go.Figure()
    return_acumulado_columns = df.loc[:, df.columns.str.contains('Return_acumulado')].columns
    return_acumulado_columns_replaced = [col.replace("Return_acumulado_", "") for col in return_acumulado_columns]
    dict_cols = dict(zip(return_acumulado_columns, return_acumulado_columns_replaced))
    df = df.rename(columns=dict_cols)
    for stock in return_acumulado_columns_replaced:
        if stock == '^GSPC':
            alpha = 1
            lw = 3
            dash = "dot"
        elif stock == '^IXIC':
            alpha = 1
            lw = 3
            dash = "dashdot"
        elif stock == 'total':
            alpha = 1
            lw = 4
            dash = 'solid'
        else:
            alpha = 1
            lw = 1
            dash = 'solid'
        figure.add_trace(go.Scatter(
            x=df['Date'],
            y=df[stock],
            name=stock,
            mode='lines',
            opacity=alpha,
            line={'width': lw,
                  'dash': dash}
        ))
    figure.update_layout(title_text="<b>Accumulated return over time</b>",
                         updatemenus=[dict(buttons=[
                             dict(label="Linear", method="relayout", args=[{"yaxis.type": "linear"}]),
                             dict(label="Log", method="relayout", args=[{"yaxis.type": "log"}])])])
    figure.update_xaxes(
        title = "Date",
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        ))
    figure.update_yaxes(title = "Return (%)")
    figure.update_layout(width = 1500, height=600)
    return figure


@st.cache(show_spinner=False,allow_output_mutation=True)
def drawdawn_plot(df_portfolio, df_benchmark):
    df = df_portfolio.merge(df_benchmark, how="inner", on="Date")
    figure = go.Figure()
    drawdawn_columns = df.loc[:, df.columns.str.contains('Drawdawn')].columns
    drawdawn_columns_replaced = [col.replace("Drawdawn_", "") for col in drawdawn_columns]
    dict_cols = dict(zip(drawdawn_columns, drawdawn_columns_replaced))
    df = df.rename(columns=dict_cols)
    for stock in drawdawn_columns_replaced:
        if stock == '^GSPC':
            alpha = 1
            lw = 3
            dash = "dot"
        elif stock == '^IXIC':
            alpha = 1
            lw = 3
            dash = "dashdot"
        elif stock == 'total':
            alpha = 1
            lw = 4
            dash = 'solid'
        else:
            alpha = 1
            lw = 1
            dash = 'solid'
        figure.add_trace(go.Scatter(
            x=df['Date'],
            y=df[stock],
            name=stock,
            mode='lines',
            opacity=alpha,
            line={'width': lw,
                  'dash': dash}
        ))
    figure.update_xaxes(
        title = "Date",
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        ))
    figure.update_yaxes(title = "Percentage (%)")
    figure.update_layout(title_text="<b>Drawdawn over time</b>",width = 1500, height=600)
    return figure

@st.cache(show_spinner=False,allow_output_mutation=True)
def day_returns_plot(df_portfolio, df_benchmark):
    df = df_portfolio.merge(df_benchmark, how="inner", on="Date")
    figure = go.Figure()
    return_columns = df.loc[:, df.columns.str.contains('Daily_return')].columns
    return_columns_replaced = [col.replace("Daily_return_", "") for col in return_columns]
    dict_cols = dict(zip(return_columns, return_columns_replaced))
    df = df.rename(columns=dict_cols)
    for stock in return_columns_replaced:
        if stock == '^GSPC':
            alpha = 1
            lw = 3
            dash = "dot"
        elif stock == '^IXIC':
            alpha = 1
            lw = 3
            dash = "dashdot"
        elif stock == 'total':
            alpha = 1
            lw = 4
            dash = 'solid'
        else:
            alpha = 1
            lw = 1
            dash = 'solid'
        figure.add_trace(go.Scatter(
            x=df['Date'],
            y=df[stock],
            name=stock,
            mode='lines',
            opacity=alpha,
            line={'width': lw,
                  'dash': dash}
        ))
    figure.update_xaxes(
        title = "Date",
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        ))
    figure.update_yaxes(title="Percentage (%)")
    figure.update_layout(title_text="<b>Daily return</b>",width = 1500, height=600)
    return figure

@st.cache(show_spinner=False,allow_output_mutation=True)
def allocation_plot(df):
    figure = go.Figure()
    allocation_drift_columns = df.loc[:, df.columns.str.contains('Percentage_allocation')].columns
    allocation_drift_columns_replaced = [col.replace("Percentage_allocation_", "") for col in allocation_drift_columns]
    dict_cols = dict(zip(allocation_drift_columns, allocation_drift_columns_replaced))
    df = df.rename(columns=dict_cols)
    for stock in allocation_drift_columns_replaced:
        if stock == 'total':
            alpha = 1
            lw = 3
        else:
            alpha = 1
            lw = 1
        figure.add_trace(go.Scatter(
            x=df['Date'],
            y=df[stock],
            name=stock,
            mode='lines',
            opacity=alpha,
            line={'width': lw}
        ))
    figure.update_xaxes(
        title = "Date",
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        ))
    figure.update_yaxes(title="Percentage (%)")
    figure.update_layout(title_text="<b>Portfolio allocation over time (without rebalancing)</b>",width = 1500, height=600)
    return figure